from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from typing import List
from app.models.communityVideo import CommunityVideo
from app.models.user import User
from app.models.community_interaction import CommunityInteraction  
from app.schemas.communityVideo import VideoCreate, VideoOut, VideoUpdate
from app.auth.auth import get_current_user, admin_or_educator
from sqlalchemy import text
from app.models.user import User

from app.schemas.user import CompletionResponse
from app.utils.streak import update_user_streak
from app.utils.badge_engine import evaluate_user_badges
from app.routes.announcements import create_automatic_announcement

# Import Limiter instance
from app.routes.auth import limiter

router = APIRouter()


def _interaction_metrics_by_id(db: Session, videos) -> dict:
    """Fetch the interaction row for every video in a single query, keyed by video id."""
    ids = [v.id for v in videos]
    if not ids:
        return {}
    rows = db.query(CommunityInteraction).filter(
        CommunityInteraction.resource_type == "video",
        CommunityInteraction.resource_id.in_(ids),
    ).all()
    return {row.resource_id: row for row in rows}


@router.post("/create_communityVideo", response_model=VideoOut)
@limiter.limit("5/minute")
async def create_video(
    request: Request,
    video_data: VideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> VideoOut:
    
    new_video = CommunityVideo(
        title=video_data.title,
        subtitle=video_data.subtitle,
        description=video_data.description,
        url=video_data.url,
        status=video_data.status,
        user_id=current_user.id,
        message=video_data.message
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    
    new_badges = evaluate_user_badges(current_user.id, db)
    new_video.new_badges = new_badges
    return new_video

@router.post("/community/video/{id}/complete", response_model=CompletionResponse)
def toggle_video_completion(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    video = db.query(CommunityVideo).filter(CommunityVideo.id == id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video in current_user.completed_videos:
        current_user.completed_videos.remove(video)
        is_completed = False
    else:
        current_user.completed_videos.append(video)
        is_completed = True
        update_user_streak(current_user)

    db.commit()
    db.refresh(current_user)
    
    new_badges = evaluate_user_badges(current_user.id, db)

    return {
        "is_completed": is_completed,
        "streak_count": current_user.streak_count,
        "streak_freezes": current_user.streak_freezes,
        "last_active_date": current_user.last_active_date.isoformat() if current_user.last_active_date else None,
        "new_badges": new_badges
    }
    

@router.get("/get_communityVideo/{id}", response_model=VideoOut)
def get_video(
    id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    video = db.query(CommunityVideo).filter(CommunityVideo.id == id).first()
    if not video:
        raise HTTPException(status_code=404, detail="CommunityVideo not found")

    user = db.query(User).filter(User.id == video.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interaction = db.query(CommunityInteraction).filter_by(resource_type="video", resource_id=id).first()

    is_completed = False
    if current_user and video in current_user.completed_videos:
        is_completed = True
        
    #FIX: Construct the dictionary override for videos[cite: 13]
    video_data = {
        "id": video.id,
        "title": video.title,
        "subtitle": video.subtitle,
        "description": video.description,
        "url": video.url,
        "status": video.status,
        "user_id": video.user_id,
        "user_name": user.name,
        "message": video.message,
        "created_at": video.created_at,
        "views_count": interaction.views_count if interaction else 0,
        "likes_count": interaction.likes_count if interaction else 0,
        "is_completed": is_completed
    }

    return video_data

@router.get("/get_communityVideos", response_model=List[VideoOut])
def get_videos(db: Session = Depends(get_db)) -> List[VideoOut]:
    videos = db.query(CommunityVideo).options(selectinload(CommunityVideo.user)).all()
    if not videos:
        raise HTTPException(status_code=404, detail="No CommunityVideos found")

    metrics = _interaction_metrics_by_id(db, videos)
    for video in videos:
        interaction = metrics.get(video.id)
        video.views_count = interaction.views_count if interaction else 0
        video.likes_count = interaction.likes_count if interaction else 0

    return videos


@router.get('/get_userCommunityVideos', response_model=List[VideoOut])
def get_labs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[VideoOut]:
    """
    Get all community videos submitted by the current user.
    """
    videos = db.query(CommunityVideo).options(selectinload(CommunityVideo.user)).filter(CommunityVideo.user_id == current_user.id).all()

    if not videos:
        return []

    metrics = _interaction_metrics_by_id(db, videos)
    for video in videos:
        interaction = metrics.get(video.id)
        video.views_count = interaction.views_count if interaction else 0
        video.likes_count = interaction.likes_count if interaction else 0

    return videos


@router.put("/update_communityVideo/{video_id}", response_model=VideoOut)
@limiter.limit("5/minute")
async def update_video(
    request: Request,
    video_id: int,
    video: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> VideoOut:
    
    db_video = db.query(CommunityVideo).filter(CommunityVideo.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="CommunityVideo not found")

    prev_status = (db_video.status or "").strip().lower()

    if video.status is not None:
        db_video.status = video.status
    if video.message is not None:
        db_video.message = video.message

    now_status = (db_video.status or "").strip().lower()
    if now_status != prev_status and now_status in ("approved", "rejected"):
        create_automatic_announcement(
            content_type="community_video",
            content_id=db_video.id,
            title=now_status,
            image_url=None,
            db=db,
            user_id=db_video.user_id,
        )

    db.commit()
    db.refresh(db_video)
    return db_video

@router.delete("/delete_communityVideo/{video_id}", status_code=200)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    
    db_video = db.query(CommunityVideo).filter(CommunityVideo.id == video_id).first()
    if not db_video:
        raise HTTPException(status_code=404, detail="CommunityVideo not found")

    db.delete(db_video)
    db.commit()
    return JSONResponse(content={"message": "CommunityVideo deleted successfully"})