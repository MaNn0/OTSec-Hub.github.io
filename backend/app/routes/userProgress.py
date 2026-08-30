from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.schemas.userProgress import UserProgressCreate, UserProgressOut
from app.models.video import Video
from app.models.userProgress import UserProgress
from app.database import get_db
from app.auth.auth import get_current_user
from app.models.user import User
from app.models.lab import Lab
from dotenv import load_dotenv
from app.utils.streak import update_user_streak
from app.utils.badge_engine import evaluate_user_badges

load_dotenv()
router = APIRouter()

@router.post("/track_progress", response_model=UserProgressOut)
def track_progress(
    progress: UserProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check existing
    existing = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.content_type == progress.content_type,
        UserProgress.content_id == progress.content_id
    ).first()

    if existing:
        if progress.content_type == "lab" and progress.quiz_completed:
            # Allow repeatable lab quiz submissions to boost streak
            update_user_streak(current_user)
            db.commit()
            db.refresh(current_user)
            
            new_badges = evaluate_user_badges(current_user.id, db)
            return UserProgressOut(
                user_id=existing.user_id,
                content_type=existing.content_type,
                content_id=existing.content_id,
                quiz_completed=True,
                user_name=current_user.name,
                user_email=current_user.email,
                streak_count=current_user.streak_count,
                streak_freezes=current_user.streak_freezes,
                last_active_date=current_user.last_active_date,
                new_badges=new_badges
            )
        elif progress.content_type == "lab":  
            raise HTTPException(status_code=409, detail="Progress already recorded")
        return existing  

    # Create new
    new_progress = UserProgress(
        user_id=current_user.id,
        content_type=progress.content_type,
        content_id=progress.content_id,
        quiz_completed=progress.quiz_completed if progress.quiz_completed is not None else False
    )
    db.add(new_progress)
    
    # --- LAB COMPLETION & STREAK LOGIC ---
    if progress.content_type == "lab" and new_progress.quiz_completed:
        lab = db.query(Lab).filter(Lab.id == progress.content_id).first()
        if lab and lab not in current_user.completed_owner_labs:
            current_user.completed_owner_labs.append(lab)
        # ALWAYS check/update streak
        update_user_streak(current_user)

    db.commit()
    db.refresh(new_progress)
    db.refresh(current_user)

    content_title = None
    if progress.content_type == "video":
        video = db.query(Video).filter(Video.id == progress.content_id).first()
        content_title = video.title if video else None
    elif progress.content_type == "lab":
        lab = db.query(Lab).filter(Lab.id == progress.content_id).first()
        content_title = lab.title if lab else None

    new_badges = evaluate_user_badges(current_user.id, db)
    return UserProgressOut(
        user_id=new_progress.user_id,
        content_type=new_progress.content_type,
        content_id=new_progress.content_id,
        quiz_completed=new_progress.quiz_completed,
        user_name=current_user.name,
        user_email=current_user.email,
        content_title=content_title,
        streak_count=current_user.streak_count,
        streak_freezes=current_user.streak_freezes,
        last_active_date=current_user.last_active_date,
        new_badges=new_badges
    )

@router.get("/track_progress", response_model=List[UserProgressOut])
def get_user_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = db.query(UserProgress).filter(UserProgress.user_id == current_user.id).all()

    video_ids = [r.content_id for r in rows if r.content_type == "video"]
    lab_ids = [r.content_id for r in rows if r.content_type == "lab"]

    video_titles = {}
    if video_ids:
        video_titles = {
            v.id: v.title
            for v in db.query(Video).filter(Video.id.in_(video_ids)).all()
        }

    lab_titles = {}
    if lab_ids:
        lab_titles = {
            lab.id: lab.title
            for lab in db.query(Lab).filter(Lab.id.in_(lab_ids)).all()
        }

    results = []
    for row in rows:
        content_title = None
        if row.content_type == "video":
            content_title = video_titles.get(row.content_id)
        elif row.content_type == "lab":
            content_title = lab_titles.get(row.content_id)

        results.append(
            UserProgressOut(
                user_id=row.user_id,
                content_type=row.content_type,
                content_id=row.content_id,
                quiz_completed=row.quiz_completed,
                user_name=current_user.name,
                user_email=current_user.email,
                content_title=content_title,
                streak_count=current_user.streak_count,
                streak_freezes=current_user.streak_freezes,
                last_active_date=current_user.last_active_date,
            )
        )
    return results

@router.patch("/track_progress/fullmark/{video_id}") 
def mark_fullmark(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        view = db.query(UserProgress).filter_by(
            user_id=current_user.id,
            content_type="video",
            content_id=video_id
        ).first()

        if not view:
            raise HTTPException(status_code=404, detail="View not found")

        view.quiz_completed = True
        
        # --- VIDEO COMPLETION & STREAK LOGIC ---
        video = db.query(Video).filter(Video.id == video_id).first()
        if video and video not in current_user.completed_owner_videos:
            current_user.completed_owner_videos.append(video)
            
        update_user_streak(current_user)
            
        db.commit()
        db.refresh(current_user)
        
        new_badges = evaluate_user_badges(current_user.id, db)
        return {
            "message": "Marked as full score",
            "streak_count": current_user.streak_count,
            "streak_freezes": current_user.streak_freezes,
            "last_active_date": current_user.last_active_date.isoformat() if current_user.last_active_date else None,
            "new_badges": new_badges
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/track_progress/single_view", response_model=UserProgressOut) 
def single_view(
    content_type: str,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if content_type not in ["video", "lab", "exercise"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type structure")
    
    try:
        content_title = None
        if content_type == 'video':
            content = db.query(Video).filter(Video.id == content_id).first()
            content_title = content.title if content else None
        elif content_type == 'lab':
            content = db.query(Lab).filter(Lab.id == content_id).first()
            content_title = content.title if content else None
        elif content_type == 'exercise':
            content_title = f"Exercise Workspace ID #{content_id}"

        view = db.query(UserProgress).filter_by(
            user_id=current_user.id,
            content_type=content_type,
            content_id=content_id
        ).first()

        if not view:
            return UserProgressOut(
                user_id=current_user.id,
                content_type=content_type,
                content_id=content_id,
                quiz_completed=False, 
                user_name=current_user.name,
                user_email=current_user.email,
                content_title=content_title,
                streak_count=current_user.streak_count,
                streak_freezes=current_user.streak_freezes
            )
            
        return UserProgressOut(
            user_id=view.user_id,
            content_type=view.content_type,
            content_id=view.content_id,
            quiz_completed=view.quiz_completed,
            user_name=current_user.name,
            user_email=current_user.email,
            content_title=content_title,
            streak_count=current_user.streak_count,
            streak_freezes=current_user.streak_freezes
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Background tracking core failure: {str(e)}"
        )