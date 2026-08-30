from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.quiz import Quiz
from app.models.video import Video
from app.models.lab import Lab
from app.models.exercise import Exercise
from app.models.userProgress import UserProgress
from app.models.user import (
    User,
    owner_lab_completions,
    owner_exercise_completions,
)
from typing import List
from app.schemas.stats import ProgressPieChartOut

router = APIRouter()


def _counts_by_user(db: Session, table, user_col):
    rows = db.query(user_col, func.count()).group_by(user_col).all()
    return {uid: int(n) for uid, n in rows}


@router.get("/stats", response_model=List[ProgressPieChartOut])
def get_all_users_progress_stats(db: Session = Depends(get_db)):
    """Official (owner) videos, labs, and exercises only — not community uploads."""
    try:
        total_videos = db.query(func.count(Video.id)).scalar() or 0
        total_quizzes = db.query(func.count(Quiz.video_id.distinct())).scalar() or 0
        total_labs = db.query(func.count(Lab.id)).scalar() or 0
        total_exercises = db.query(func.count(Exercise.id)).scalar() or 0
        catalog_total = total_videos + total_labs + total_exercises

        official_video_ids = {row[0] for row in db.query(Video.id).all()}

        watched_rows = (
            db.query(UserProgress.user_id, UserProgress.content_id)
            .filter(UserProgress.content_type == "video")
            .all()
        )
        watched_by_user = {}
        for uid, cid in watched_rows:
            if cid in official_video_ids:
                watched_by_user.setdefault(uid, set()).add(cid)

        official_lab_ids = {row[0] for row in db.query(Lab.id).all()}
        lab_progress_rows = (
            db.query(UserProgress.user_id, UserProgress.content_id)
            .filter(UserProgress.content_type == "lab", UserProgress.quiz_completed.is_(True))
            .all()
        )
        labs_by_user = {}
        for uid, cid in lab_progress_rows:
            if cid in official_lab_ids:
                labs_by_user.setdefault(uid, set()).add(cid)

        lab_done = _counts_by_user(db, owner_lab_completions, owner_lab_completions.c.user_id)
        exercise_done = _counts_by_user(db, owner_exercise_completions, owner_exercise_completions.c.user_id)

        quiz_rows = (
            db.query(UserProgress.user_id, func.count(UserProgress.content_id.distinct()))
            .filter(UserProgress.content_type == "video", UserProgress.quiz_completed.is_(True))
            .group_by(UserProgress.user_id)
            .all()
        )
        quiz_done = {uid: int(n) for uid, n in quiz_rows}

        users = (
            db.query(User)
            .filter(User.is_banned.is_(False), User.role.in_(["member", "educator"]))
            .order_by(User.name)
            .all()
        )

        results = []
        for user in users:
            completed_videos = min(len(watched_by_user.get(user.id, ())), total_videos)
            completed_labs = min(max(lab_done.get(user.id, 0), len(labs_by_user.get(user.id, ()))), total_labs)
            completed_exercises = min(exercise_done.get(user.id, 0), total_exercises)
            completed_quizzes = min(quiz_done.get(user.id, 0), total_quizzes)

            finished = completed_videos + completed_labs + completed_exercises
            overall = round((finished / catalog_total) * 100) if catalog_total > 0 else 0
            certificate_ready = catalog_total > 0 and finished >= catalog_total

            results.append(
                ProgressPieChartOut(
                    user_id=user.id,
                    name=user.name,
                    completed_videos=completed_videos,
                    remaining_videos=max(0, total_videos - completed_videos),
                    completed_quizzes=completed_quizzes,
                    remaining_quizzes=max(0, total_quizzes - completed_quizzes),
                    completed_labs=completed_labs,
                    remaining_labs=max(0, total_labs - completed_labs),
                    completed_exercises=completed_exercises,
                    remaining_exercises=max(0, total_exercises - completed_exercises),
                    overall_percent=overall,
                    certificate_ready=certificate_ready,
                )
            )

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
