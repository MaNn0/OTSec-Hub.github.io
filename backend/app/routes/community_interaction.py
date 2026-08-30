from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models.community_interaction import CommunityInteraction, CommunityLike, CommunityView, CommunityComment, ModeratedCommentLog, CommentReport
from app.schemas.community_interaction import CommentCreate, CommentOut, MetricSummaryOut
from app.auth.auth import get_current_user, get_optional_user, admin_only
from app.models.user import User
from typing import List, Optional
from app.utils.streak import update_user_streak
from app.routes.auth import limiter
from app.utils.badge_engine import evaluate_user_badges

router = APIRouter(prefix="/community", tags=["Community Interactions"])


@router.get("/metrics/{resource_type}/{resource_id}", response_model=MetricSummaryOut)
def get_community_resource_metrics(
    resource_type: str, resource_id: int, 
    db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_user)
):
    """Safely handles tracking isolated metric status states relative to the calling profile user."""
    if resource_type not in ["lab", "video"]:
        raise HTTPException(status_code=400, detail="Invalid resource type query vector.")

    metric = db.query(CommunityInteraction).filter_by(resource_type=resource_type, resource_id=resource_id).first()
    if not metric:
        metric = CommunityInteraction(resource_type=resource_type, resource_id=resource_id, views_count=0, likes_count=0)
        db.add(metric)
        db.flush()

    is_liked = False
    is_viewed = False
    if current_user:
        is_liked = db.query(CommunityLike).filter_by(user_id=current_user.id, resource_type=resource_type, resource_id=resource_id).first() is not None
        is_viewed = db.query(CommunityView).filter_by(user_id=current_user.id, resource_type=resource_type, resource_id=resource_id).first() is not None

    return {
        "views_count": metric.views_count or 0,
        "likes_count": metric.likes_count or 0,
        "is_liked_by_user": is_liked,
        "is_viewed_by_user": is_viewed
    }

@router.post("/view/{resource_type}/{resource_id}", response_model=MetricSummaryOut)
def record_community_view(
    resource_type: str, resource_id: int, 
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if resource_type not in ["lab", "video"]:
        raise HTTPException(status_code=400, detail="Invalid resource type execution vector.")

    existing_view = db.query(CommunityView).filter(
        CommunityView.user_id == current_user.id,
        CommunityView.resource_type == resource_type,
        CommunityView.resource_id == resource_id
    ).first()

    metric = db.query(CommunityInteraction).filter_by(resource_type=resource_type, resource_id=resource_id).first()
    if not metric:
        metric = CommunityInteraction(resource_type=resource_type, resource_id=resource_id, views_count=0, likes_count=0)
        db.add(metric)
        db.flush()

    if not existing_view:
        try:
            new_view = CommunityView(
                user_id=current_user.id,
                resource_type=resource_type,
                resource_id=resource_id
            )
            db.add(new_view)
            metric.views_count += 1
            db.commit()
        except Exception:
            db.rollback()

    is_liked = db.query(CommunityLike).filter_by(user_id=current_user.id, resource_type=resource_type, resource_id=resource_id).first() is not None
    
    db.commit()
    
    return {
        "views_count": metric.views_count, 
        "likes_count": metric.likes_count, 
        "is_liked_by_user": is_liked,
        "is_viewed_by_user": True,
        "streak_count": current_user.streak_count,
        "streak_freezes": current_user.streak_freezes
    }

@router.post("/like/{resource_type}/{resource_id}", response_model=MetricSummaryOut)
def toggle_community_like(
    resource_type: str, resource_id: int, 
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if resource_type not in ["lab", "video"]:
        raise HTTPException(status_code=400, detail="Invalid resource type transaction vector.")

    existing_like = db.query(CommunityLike).filter(
        CommunityLike.user_id == current_user.id,
        CommunityLike.resource_type == resource_type,
        CommunityLike.resource_id == resource_id
    ).first()

    metric = db.query(CommunityInteraction).filter_by(resource_type=resource_type, resource_id=resource_id).first()
    if not metric:
        metric = CommunityInteraction(resource_type=resource_type, resource_id=resource_id, views_count=0, likes_count=0)
        db.add(metric)
        db.flush()

    if existing_like:
        db.delete(existing_like)
        metric.likes_count = max(0, metric.likes_count - 1)
        is_liked = False
        db.commit()
    else:
        try:
            new_like = CommunityLike(
                user_id=current_user.id, 
                resource_type=resource_type, 
                resource_id=resource_id
            )
            db.add(new_like)
            db.flush()
            
            metric.likes_count += 1
            is_liked = True
            db.commit()
        except Exception:
            db.rollback()
            duplicate = db.query(CommunityLike).filter_by(
                user_id=current_user.id, resource_type=resource_type, resource_id=resource_id
            ).first()
            if duplicate:
                db.delete(duplicate)
                metric.likes_count = max(0, metric.likes_count - 1)
                is_liked = False
                db.commit()
            else:
                is_liked = False

    is_viewed = db.query(CommunityView).filter_by(user_id=current_user.id, resource_type=resource_type, resource_id=resource_id).first() is not None

    return {
        "views_count": metric.views_count, 
        "likes_count": metric.likes_count, 
        "is_liked_by_user": is_liked,
        "is_viewed_by_user": is_viewed
    }


@router.post("/comment/report/{comment_id}")
@limiter.limit("10/minute")
def report_community_comment(request: Request, comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comment = db.query(CommunityComment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Target comment not found.")

    already_reported = db.query(CommentReport).filter_by(user_id=current_user.id, comment_id=comment_id).first()
    if already_reported:
        raise HTTPException(status_code=400, detail="ALREADY_REPORTED")

    try:
        new_report = CommentReport(user_id=current_user.id, comment_id=comment_id)
        db.add(new_report)
        db.flush()  
        
        comment.report_count += 1
        db.flush()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Report submission failed or duplicate detected.")

    if comment.report_count >= 3:
        log_entry = ModeratedCommentLog(
            original_comment_id=comment.id, 
            author_id=comment.user_id,
            resource_type=comment.resource_type, 
            resource_id=comment.resource_id,
            content=comment.content, 
            reason_for_deletion="Flagged by 3 Users"
        )
        db.add(log_entry)
        db.delete(comment) 
        db.commit()
        return {"status": "AUTOMATICALLY_PURGED", "message": "Comment auto-deleted due to high report density."}

    if comment.report_count == 1:
        comment.is_under_review = True

    db.commit()
    return {"status": "FLAGGED_FOR_REVIEW", "message": "Comment queued for Admin inspection dashboard."}


@router.post("/comment/{resource_type}/{resource_id}", response_model=CommentOut)
@limiter.limit("10/minute")
def add_comment(
    request: Request, 
    resource_type: str, 
    resource_id: int, 
    comment_data: CommentCreate, 
    db: Session = Depends(get_db), # <-- This was missing
    current_user: User = Depends(get_current_user)
):
    if comment_data.parent_id:
        parent = db.query(CommunityComment).filter_by(id=comment_data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent thread not found.")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Deep nesting blocked. Max recursion limit of 2 layers reached.")

    new_comment = CommunityComment(
        user_id=current_user.id, resource_type=resource_type, resource_id=resource_id,
        content=comment_data.content, parent_id=comment_data.parent_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    new_comment.user = db.query(User).filter(User.id == current_user.id).first()
    new_comment.replies = []
    
    new_badges = evaluate_user_badges(current_user.id, db)
    new_comment.new_badges = new_badges
    return new_comment


@router.get("/comments/{resource_type}/{resource_id}", response_model=List[CommentOut])
def get_resource_comments(resource_type: str, resource_id: int, db: Session = Depends(get_db)):
    comments = (
        db.query(CommunityComment)
        .options(
            selectinload(CommunityComment.user),
            selectinload(CommunityComment.replies).selectinload(CommunityComment.user),
        )
        .filter_by(resource_type=resource_type, resource_id=resource_id, parent_id=None)
        .order_by(CommunityComment.created_at.desc())
        .all()
    )
    for comment in comments:
        if not comment.user:
            comment.user = db.query(User).filter(User.id == comment.user_id).first()
        for reply in comment.replies:
            if not reply.user:
                reply.user = db.query(User).filter(User.id == reply.user_id).first()
    return comments

# ADMIN DASHBOARD & BAN

@router.get("/admin/reported-comments", response_model=List[CommentOut])
def get_reported_comments_dashboard(db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    comments = (
        db.query(CommunityComment)
        .options(
            selectinload(CommunityComment.user),
            selectinload(CommunityComment.replies).selectinload(CommunityComment.user),
        )
        .filter(CommunityComment.is_under_review == True)
        .all()
    )
    for comment in comments:
        if not comment.user:
            comment.user = db.query(User).filter(User.id == comment.user_id).first()
        for reply in comment.replies:
            if not reply.user:
                reply.user = db.query(User).filter(User.id == reply.user_id).first()
    return comments

@router.get("/admin/deleted-logs")
def get_all_deleted_comment_logs(db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    return db.query(ModeratedCommentLog).order_by(ModeratedCommentLog.deleted_at.desc()).all()

@router.post("/admin/comment-resolve/{comment_id}/{action}")
def resolve_admin_review(comment_id: int, action: str, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    comment = db.query(CommunityComment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment no longer exists.")

    if action == "keep":
        comment.is_under_review = False
        comment.report_count = 0  
        db.query(CommentReport).filter_by(comment_id=comment_id).delete()
    elif action == "delete":
        log_entry = ModeratedCommentLog(
            original_comment_id=comment.id, author_id=comment.user_id,
            resource_type=comment.resource_type, resource_id=comment.resource_id,
            content=comment.content, reason_for_deletion="Flagged by Admin"
        )
        db.add(log_entry)
        db.delete(comment)
    else:
        raise HTTPException(status_code=400, detail="Invalid action statement.")

    db.commit()
    return {"message": f"Comment successfully resolved with action: {action}."}

@router.post("/admin/ban-user/{user_id}")
def ban_malicious_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User target profile structure not found.")
    if target_user.role == "admin":
        raise HTTPException(status_code=400, detail="Administrative profiles cannot be banned via automation handles.")

    target_user.is_banned = True
    db.commit()
    return {"status": "USER_SUCCESSFULLY_BANNED", "message": f"User {target_user.name} has been restricted."}