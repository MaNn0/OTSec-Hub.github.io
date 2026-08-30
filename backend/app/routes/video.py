from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from app.schemas.video import VideoCreate, VideoOut, VideoUpdate
from app.models.video import Video, OwnerLike, OwnerView  
from app.models.quiz import Quiz
from app.database import get_db
from typing import List, Optional
from dotenv import load_dotenv
from sqlalchemy import asc, text
from app.schemas.pagination import PaginatedResponse
from app.routes.announcements import create_automatic_announcement
from app.auth.auth import get_current_user, get_optional_user
from app.models.user import User
from app.utils.streak import update_user_streak

load_dotenv()
router = APIRouter()

@router.post("/add_video", response_model=VideoOut)
def add_video(video: VideoCreate, db: Session = Depends(get_db)):
    try:
        quiz_objects = []
        for q in video.quizzes:
            if not q.question or q.question.strip() == "" or q.question.strip().upper() == "EMPTY":
                continue
                
            quiz_objects.append(
                Quiz(
                    question=q.question,
                    option1=q.options[0] if len(q.options) > 0 else None,
                    option2=q.options[1] if len(q.options) > 1 else None,
                    option3=q.options[2] if len(q.options) > 2 else None,
                    option4=q.options[3] if len(q.options) > 3 else None,
                    correct_answer=q.correct_answer
                )
            )

        db_video = Video(
            title=video.title,
            subtitle=video.subtitle,
            description=video.description,
            url=video.url,
            quizzes=quiz_objects,
            views_count=0,
            likes_count=0
        )
        
        db.add(db_video)
        db.flush() 
        
        create_automatic_announcement(
            content_type="video",
            content_id=db_video.id,
            title=db_video.title,
            image_url=db_video.url,
            db=db
        )
        
        db.commit()
        db.refresh(db_video) 
        return db_video

    except IntegrityError as e:
        db.rollback()
        if 'ix_videos_url' in str(e.orig):
            raise HTTPException(status_code=400, detail="Video URL already exists.")
        raise HTTPException(status_code=400, detail="Database integrity error.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
@router.get("/get_videos", response_model=PaginatedResponse[VideoOut])
def get_videos(
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(lambda: None) 
):
    videos_query = db.query(Video).order_by(asc(Video.id))
    total = videos_query.count()
    videos = (
        videos_query
        .options(selectinload(Video.quizzes))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    liked_video_ids = set()
    if current_user and hasattr(current_user, 'id'):
        liked_records = db.query(OwnerLike.resource_id).filter(
            OwnerLike.user_id == current_user.id,
            OwnerLike.resource_type == "video"
        ).all()
        liked_video_ids = {r[0] for r in liked_records}

    video_items = []
    for v in videos:
        vo = VideoOut.from_orm(v)
        vo.is_liked_by_user = v.id in liked_video_ids
        video_items.append(vo)

    if not video_items and total > 0 and page > 1:
        raise HTTPException(status_code=404, detail="Page not found")

    return PaginatedResponse(
        total=total,
        page=page,
        limit=limit,
        items=video_items
    )

@router.get("/get_video/{video_id}", response_model=VideoOut)
def get_video(
    video_id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(lambda: None) 
):
    db_video = db.query(Video).filter(Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    is_liked = False
    if current_user and hasattr(current_user, 'id'):
        is_liked = db.query(OwnerLike).filter(
            OwnerLike.user_id == current_user.id,
            OwnerLike.resource_type == "video",
            OwnerLike.resource_id == video_id
        ).first() is not None

    video_out = VideoOut.from_orm(db_video)
    video_out.is_liked_by_user = is_liked
    return video_out

@router.put("/update_video/{video_id}", response_model=VideoOut)
def update_video(video_id: int, video: VideoUpdate, db: Session = Depends(get_db)):
    db_video = db.query(Video).filter(Video.id == video_id).first()

    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.title:
        db_video.title = video.title
    if video.subtitle:
        db_video.subtitle = video.subtitle
    if video.description:
        db_video.description = video.description
    if video.url:
        db_video.url = video.url

    if video.quizzes:
        for updated_quiz in video.quizzes:
            db_quiz = db.query(Quiz).filter(Quiz.id == updated_quiz.id).first()
            if db_quiz:
                if updated_quiz.question:
                    db_quiz.question = updated_quiz.question
                if updated_quiz.correct_answer:
                    db_quiz.correct_answer = updated_quiz.correct_answer
                if updated_quiz.options:
                    db_quiz.option1 = updated_quiz.options[0]
                    db_quiz.option2 = updated_quiz.options[1]
                    db_quiz.option3 = updated_quiz.options[2]
                    db_quiz.option4 = updated_quiz.options[3]

    db.commit()
    db.refresh(db_video)
    return db_video

@router.delete("/delete_video/{video_id}", response_model=VideoOut)
def delete_video(video_id: int, db: Session = Depends(get_db)):
    db_video = db.query(Video).filter(Video.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    db.query(OwnerLike).filter(
        OwnerLike.resource_type == "video",
        OwnerLike.resource_id == video_id
    ).delete(synchronize_session=False)

    db.query(OwnerView).filter(
        OwnerView.resource_type == "video",
        OwnerView.resource_id == video_id
    ).delete(synchronize_session=False)

    db.delete(db_video)
    db.commit()
    return JSONResponse(content={"message": "Video deleted successfully"})



@router.get("/interactions/metrics/video/{resource_id}")
def get_video_metrics(
    resource_id: int, 
    db: Session = Depends(get_db), 
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Safely handles syncing exact unique multi-user state payload to interaction bar components."""
    video = db.query(Video).filter(Video.id == resource_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    is_liked = False
    is_viewed = False
    if current_user:
        is_liked = db.query(OwnerLike).filter_by(
            user_id=current_user.id, 
            resource_type="video", 
            resource_id=resource_id
        ).first() is not None

        is_viewed = db.query(OwnerView).filter_by(
            user_id=current_user.id,
            resource_type="video",
            resource_id=resource_id
        ).first() is not None

    return {
        "views_count": video.views_count or 0,
        "likes_count": video.likes_count or 0,
        "is_liked_by_user": is_liked,
        "is_viewed_by_user": is_viewed
    }

@router.post("/interactions/view/{video_id}")
def record_video_view(
    video_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers unique views per user profile securely."""
    existing_view = db.query(OwnerView).filter_by(
        user_id=current_user.id, 
        resource_type="video", 
        resource_id=video_id
    ).first()

    if not existing_view:
        try:
            new_view = OwnerView(user_id=current_user.id, resource_type="video", resource_id=video_id)
            db.add(new_view)
            
            # ORM Safe Update Engine
            db.query(Video).filter(Video.id == video_id).update(
                {Video.views_count: Video.views_count + 1},
                synchronize_session=False
            )
            db.commit()
        except Exception:
            db.rollback()
            
    return {"message": "View validation handled cleanly."}


@router.post("/interactions/video/like/{video_id}")
def toggle_video_like(
    video_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    if not current_user or not hasattr(current_user, 'id'):
        raise HTTPException(status_code=401, detail="Authentication identity context required to vote.")
        
    user_id = current_user.id
    
    existing_like = db.query(OwnerLike).filter(
        OwnerLike.user_id == user_id,
        OwnerLike.resource_type == "video",
        OwnerLike.resource_id == video_id
    ).first()
    
    if existing_like:
        db.delete(existing_like)
        db.execute(text("UPDATE videos SET likes_count = GREATEST(0, likes_count - 1) WHERE id = :id"), {"id": video_id})
        db.commit()
        
        video = db.query(Video).filter(Video.id == video_id).first()
        return {
            "views_count": video.views_count if video else 0,
            "likes_count": video.likes_count if video else 0,
            "is_liked_by_user": False,
            "is_viewed_by_user": True
        }
    else:
        try:
            new_like = OwnerLike(user_id=user_id, resource_type="video", resource_id=video_id)
            db.add(new_like)
            db.execute(text("UPDATE videos SET likes_count = likes_count + 1 WHERE id = :id"), {"id": video_id})
            db.commit()
        except IntegrityError:
            db.rollback()

        video = db.query(Video).filter(Video.id == video_id).first()
        return {
            "views_count": video.views_count if video else 0,
            "likes_count": video.likes_count if video else 0,
            "is_liked_by_user": True,
            "is_viewed_by_user": True
        }