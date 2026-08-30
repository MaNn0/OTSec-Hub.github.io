from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.ExerciseSubmission import ExerciseSubmission
from app.schemas.exerciseSubmission import ExerciseSubmissionCreate, ExerciseSubmissionOut, ExerciseSubmissionUpdate
from app.auth.auth import get_current_user
from app.models.user import User
from typing import List

from app.utils.streak import update_user_streak
from app.models.exercise import Exercise
from app.utils.badge_engine import evaluate_user_badges

# IMPORT THE AUTOMATIC ANNOUNCEMENT TRIGGER
from app.routes.announcements import create_automatic_announcement

router = APIRouter()

@router.post("/submit_exercise/{exercise_id}", status_code=status.HTTP_201_CREATED)
def submit_exercise(
    exercise_id: int,
    submission: ExerciseSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    submission_record = ExerciseSubmission(
        exercise_id=exercise_id,
        user_id=current_user.id,
        answers=submission.answers,
        status=submission.status if submission.status else "pending"
    )
    db.add(submission_record)

    # Mark as completed if it's the first time
    if exercise not in current_user.completed_owner_exercises:
        current_user.completed_owner_exercises.append(exercise)
        
    # ALWAYS check/update streak for an action
    update_user_streak(current_user)

    db.commit()
    db.refresh(current_user)
    db.refresh(submission_record)

    new_badges = evaluate_user_badges(current_user.id, db)
    return {
        "message": "Submission successful",
        "streak_count": current_user.streak_count,
        "streak_freezes": current_user.streak_freezes,
        "last_active_date": current_user.last_active_date.isoformat() if current_user.last_active_date else None,
        "new_badges": new_badges
    }
    
    
@router.get("/submission", response_model=List[ExerciseSubmissionOut])
def get_submission(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(ExerciseSubmission).options(joinedload(ExerciseSubmission.exercise)).all()
    return submission

@router.patch("/submission/{submission_id}", response_model=ExerciseSubmissionOut)
def update_submission_status(
    submission_id: int,
    update_data: ExerciseSubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(ExerciseSubmission).options(joinedload(ExerciseSubmission.exercise)).filter(ExerciseSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission.status = update_data.status
    if update_data.admin_note is not None:
        submission.admin_note = update_data.admin_note
    if update_data.answers is not None:
        submission.answers = update_data.answers 
    
    db.flush()

    create_automatic_announcement(
        content_type="exercise_submission",
        content_id=submission.id,
        title=submission.status, 
        image_url=None, 
        db=db,
        user_id=submission.user_id,
    )
    
    db.commit()
    db.refresh(submission)
    return submission