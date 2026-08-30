from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.models.user import (
    User,
    Badge,
    UserBadge,
    owner_lab_completions,
    owner_video_completions,
    owner_exercise_completions,
    community_lab_completions,
    community_video_completions
)
# --- NEW: Import the models we need to count creations & comments ---
from app.models.communityLab import CommunityLab
from app.models.communityVideo import CommunityVideo
from app.models.community_interaction import CommunityComment

def evaluate_user_badges(user_id: int, db: Session):
    """
    Evaluates all badge milestones for a user.
    Runs synchronously to inject instant payloads.
    """
    try:
        # 1. Fetch IDs of badges the user already has
        earned_badge_ids = {
            row[0] for row in db.query(UserBadge.badge_id).filter(UserBadge.user_id == user_id).all()
        }

        # 2. Fetch all available badges
        all_badges = db.query(Badge).all()
        unearned_badges = [b for b in all_badges if b.id not in earned_badge_ids]

        if not unearned_badges:
            return []

        # 3. Fetch user record for streak
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Count completed official content via pivot tables
        labs_count = db.execute(
            select(func.count()).select_from(owner_lab_completions).where(owner_lab_completions.c.user_id == user_id)
        ).scalar() or 0

        videos_count = db.execute(
            select(func.count()).select_from(owner_video_completions).where(owner_video_completions.c.user_id == user_id)
        ).scalar() or 0

        exercises_count = db.execute(
            select(func.count()).select_from(owner_exercise_completions).where(owner_exercise_completions.c.user_id == user_id)
        ).scalar() or 0

        # --- UPDATED: Count community CREATIONS (Uploads), not completions ---
        comm_labs_count = db.query(CommunityLab).filter(CommunityLab.user_id == user_id).count()
        comm_videos_count = db.query(CommunityVideo).filter(CommunityVideo.user_id == user_id).count()

        community_resources_count = comm_labs_count + comm_videos_count

        # Streaks from the user model
        streak_count = getattr(user, "streak_count", 0) or 0

        # --- UPDATED: Dynamically count user comments ---
        comments_count = db.query(CommunityComment).filter(CommunityComment.user_id == user_id).count()
        
        papers_count = 0

        # Metric mapping lookup
        metrics = {
            "labs": labs_count,
            "videos": videos_count,
            "exercises": exercises_count,
            "community_resources": community_resources_count,
            "comments": comments_count,
            "papers": papers_count,
            "streaks": streak_count,
        }

        # 4. Check thresholds and award qualified badges
        new_user_badges = []
        unlocked_badge_details = []

        for badge in unearned_badges:
            current_val = metrics.get(badge.track, 0)
            if current_val >= badge.threshold:
                new_user_badges.append(UserBadge(user_id=user_id, badge_id=badge.id))
                
                # Capture the details for the React toast
                unlocked_badge_details.append({
                    "name": badge.name,
                    "realm": badge.realm,
                    "image_url": badge.image_url
                })

        if new_user_badges:
            db.add_all(new_user_badges)
            db.commit()

        return unlocked_badge_details

    except Exception as e:
        db.rollback()
        print(f"[BadgeEngine Error] user_id {user_id}: {e}")
        return []