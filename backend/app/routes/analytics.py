from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, func
from app.models.user import User
from app.models.video import Video
from app.models.lab import Lab
from app.models.exercise import Exercise
from app.database import get_db

# Core community models
from app.models.communityLab import CommunityLab 
from app.models.communityVideo import CommunityVideo
from app.models.paper import Paper

router = APIRouter()


def _safe_count(db: Session, statement: str) -> int:
    try:
        return int(db.execute(text(statement)).scalar() or 0)
    except Exception:
        db.rollback()
        return 0

@router.get("/analytics")
def get_overview(db: Session = Depends(get_db)):
    # 1. Base counters
    total_users = db.query(User).count()
    total_videos = db.query(Video).count()
    total_labs = db.query(Lab).count()
    total_exercises = db.query(Exercise).count()

    # Calculate Total Submissions dynamically by summing all community labs & videos
    total_community_labs = db.query(CommunityLab).count()
    total_community_videos = db.query(CommunityVideo).count()
    aggregated_submissions = total_community_labs + total_community_videos

    admins_count = db.query(User).filter(User.role == "admin").count()
    educators_count = db.query(User).filter(User.role == "educator").count()
    members_count = db.query(User).filter(User.role == "member").count()
    banned_count = db.query(User).filter(User.is_banned == True).count()

    pending_labs = db.query(CommunityLab).filter(CommunityLab.status == "pending").count()
    pending_videos = db.query(CommunityVideo).filter(CommunityVideo.status == "pending").count()
    pending_papers = db.query(Paper).filter(func.lower(Paper.status) == "pending").count()

    total_reported_items = db.execute(text("SELECT COUNT(*) FROM comment_reports;")).scalar() or 0

    # Live Database Capacity
    db_size_bytes = db.execute(text("SELECT pg_database_size(current_database());")).scalar() or 0
    FREE_TIER_LIMIT_BYTES = 500 * 1024 * 1024 
    db_usage_percent = round((db_size_bytes / FREE_TIER_LIMIT_BYTES) * 100, 2)

    return {
        "users": total_users,
        "videos": total_videos,
        "labs": total_labs,
        "exercises": total_exercises,
        "submissions": aggregated_submissions,  # Represents total community video & lab submissions
        "roles": {
            "admins": admins_count,
            "educators": educators_count,
            "members": members_count,
            "banned": banned_count
        },
        "moderation_queue": {
            "pending_labs": pending_labs,
            "pending_videos": pending_videos,
            "pending_papers": pending_papers,
            "reported_comments": total_reported_items
        },
        "system_health": {
            "db_usage_percent": min(db_usage_percent, 100.0)
        }
    }


@router.get("/public-stats")
def get_public_statistics(db: Session = Depends(get_db)):
    visits_count = db.execute(
        text(
            """
            INSERT INTO site_stats (id, homepage_visits)
            VALUES (1, 1)
            ON CONFLICT (id) DO UPDATE
            SET homepage_visits = site_stats.homepage_visits + 1
            RETURNING homepage_visits;
            """
        )
    ).scalar() or 1
    db.commit()

    owner_labs = db.query(Lab).count()
    owner_videos = db.query(Video).count()
    exercises = db.query(Exercise).count()
    
    total_papers = db.query(Paper).filter(
        or_(func.lower(Paper.status) == "approved", Paper.status.is_(None))
    ).count()
    total_benchmarks = _safe_count(db, "SELECT COUNT(*) FROM benchmarks;")
    
    community_labs = db.query(CommunityLab).filter(CommunityLab.status == "approved").count()
    community_videos = db.query(CommunityVideo).filter(CommunityVideo.status == "approved").count()

    aggregated_resources = (
        owner_labs + owner_videos + exercises + 
        total_papers + total_benchmarks + 
        community_labs + community_videos
    )

    total_comments = _safe_count(db, "SELECT COUNT(*) FROM community_comments;")
    total_likes = (
        _safe_count(db, "SELECT COUNT(*) FROM community_likes;")
        + _safe_count(db, "SELECT COUNT(*) FROM owner_likes;")
    )
    total_views = (
        _safe_count(db, "SELECT COUNT(*) FROM community_views;")
        + _safe_count(db, "SELECT COUNT(*) FROM owner_views;")
    )

    total_activity_score = total_comments + total_likes + total_views
    total_registered_members = db.query(User).count()

    return {
        "total_activity": total_activity_score,
        "total_resources": aggregated_resources,
        "total_members": total_registered_members,
        "site_visits": visits_count
    }