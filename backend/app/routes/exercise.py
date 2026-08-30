from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models.exercise import Exercise
from app.models.video import OwnerLike, OwnerView  
from fastapi.responses import JSONResponse
from app.schemas.exercise import ExerciseCreate, ExerciseOut, ExerciseUpdate
from app.auth.auth import get_current_user, get_optional_user
from app.models.user import User
from typing import List, Optional
from app.routes.announcements import create_automatic_announcement

router = APIRouter()

@router.post('/create_exercise', response_model=ExerciseOut)
def create_exercise(
    exercise_data: ExerciseCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    clean_questions = [
        q.strip() for q in exercise_data.questions 
        if q and q.strip() != "" and q.strip().upper() != "EMPTY"
    ]

    new_exercise = Exercise(
        title=exercise_data.title,
        subtitle=exercise_data.subtitle,
        content=exercise_data.content,
        questions=clean_questions,
        views_count=0,
        likes_count=0
    )
    db.add(new_exercise)
    db.flush()  
    
    create_automatic_announcement(
        content_type="exercise",
        content_id=new_exercise.id,
        title=new_exercise.title,
        image_url="",  
        db=db
    )

    db.commit()
    db.refresh(new_exercise)
    return new_exercise

@router.get('/get_exercises', response_model=List[ExerciseOut])
def get_exercises(
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(lambda: None)  
):
    exercises = db.query(Exercise).all()
    if not exercises:
        raise HTTPException(status_code=404, detail="Exercise not found")
        
    liked_exercise_ids = set()
    if current_user and hasattr(current_user, 'id'):
        liked_records = db.query(OwnerLike.resource_id).filter(
            OwnerLike.user_id == current_user.id,
            OwnerLike.resource_type == "exercise"
        ).all()
        liked_exercise_ids = {r[0] for r in liked_records}

    exercise_items = []
    for ex in exercises:
        eo = ExerciseOut.from_orm(ex)
        eo.is_liked_by_user = ex.id in liked_exercise_ids
        exercise_items.append(eo)
        
    return exercise_items

@router.get('/get_exercise/{id}', response_model=ExerciseOut)
def get_exercise(
    id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(lambda: None)  
):
    exercise = db.query(Exercise).filter(Exercise.id == id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
        
    is_liked = False
    if current_user and hasattr(current_user, 'id'):
        is_liked = db.query(OwnerLike).filter(
            OwnerLike.user_id == current_user.id,
            OwnerLike.resource_type == "exercise",
            OwnerLike.resource_id == id
        ).first() is not None

    exercise_out = ExerciseOut.from_orm(exercise)
    exercise_out.is_liked_by_user = is_liked
    return exercise_out

@router.put("/update_exercise/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, exercise: ExerciseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()

    if not db_exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    if exercise.title:
        db_exercise.title = exercise.title
    if exercise.subtitle:
        db_exercise.subtitle = exercise.subtitle
    if exercise.content:
        db_exercise.content = exercise.content

    if exercise.questions:
        db_exercise.questions = [
            q.strip() for q in exercise.questions 
            if q and q.strip() != "" and q.strip().upper() != "EMPTY"
        ]

    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@router.delete("/delete_exercise/{exercise_id}", status_code=200)
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()

    if not db_exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    db.query(OwnerLike).filter(
        OwnerLike.resource_type == "exercise",
        OwnerLike.resource_id == exercise_id
    ).delete(synchronize_session=False)

    db.query(OwnerView).filter(
        OwnerView.resource_type == "exercise",
        OwnerView.resource_id == exercise_id
    ).delete(synchronize_session=False)

    db.delete(db_exercise)
    db.commit()
    return JSONResponse(content={"message": "Exercise deleted successfully"})



@router.get("/interactions/metrics/exercise/{resource_id}")
def get_exercise_metrics(
    resource_id: int, 
    db: Session = Depends(get_db), 
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Safely handles syncing exact unique multi-user state payload to interaction bar components."""
    exercise = db.query(Exercise).filter(Exercise.id == resource_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    is_liked = False
    is_viewed = False
    if current_user:
        is_liked = db.query(OwnerLike).filter_by(
            user_id=current_user.id, 
            resource_type="exercise", 
            resource_id=resource_id
        ).first() is not None

        is_viewed = db.query(OwnerView).filter_by(
            user_id=current_user.id,
            resource_type="exercise",
            resource_id=resource_id
        ).first() is not None

    return {
        "views_count": exercise.views_count or 0,
        "likes_count": exercise.likes_count or 0,
        "is_liked_by_user": is_liked,
        "is_viewed_by_user": is_viewed
    }

@router.post("/interactions/exercise/view/{exercise_id}")
def record_exercise_view(
    exercise_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers unique views per user profile securely."""
    existing_view = db.query(OwnerView).filter_by(
        user_id=current_user.id, 
        resource_type="exercise", 
        resource_id=exercise_id
    ).first()

    if not existing_view:
        try:
            new_view = OwnerView(user_id=current_user.id, resource_type="exercise", resource_id=exercise_id)
            db.add(new_view)
            
            db.query(Exercise).filter(Exercise.id == exercise_id).update(
                {Exercise.views_count: Exercise.views_count + 1},
                synchronize_session=False
            )
            db.commit()
        except Exception:
            db.rollback()
            
    return {"message": "View validation handled cleanly."}


@router.post("/interactions/exercise/like/{exercise_id}")
def toggle_exercise_like(
    exercise_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    user_id = current_user.id
    
    existing_like = db.query(OwnerLike).filter(
        OwnerLike.user_id == user_id,
        OwnerLike.resource_type == "exercise",
        OwnerLike.resource_id == exercise_id
    ).first()
    
    if existing_like:
        db.delete(existing_like)
        db.execute(text("UPDATE exercise SET likes_count = GREATEST(0, likes_count - 1) WHERE id = :id"), {"id": exercise_id})
        db.commit()
        
        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        return {
            "views_count": exercise.views_count if exercise else 0,
            "likes_count": exercise.likes_count if exercise else 0,
            "is_liked_by_user": False,
            "is_viewed_by_user": True
        }
    else:
        try:
            new_like = OwnerLike(user_id=user_id, resource_type="exercise", resource_id=exercise_id)
            db.add(new_like)
            db.execute(text("UPDATE exercise SET likes_count = likes_count + 1 WHERE id = :id"), {"id": exercise_id})
            db.commit()
        except Exception:
            db.rollback()

        exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
        return {
            "views_count": exercise.views_count if exercise else 0,
            "likes_count": exercise.likes_count if exercise else 0,
            "is_liked_by_user": True,
            "is_viewed_by_user": True
        }

# @router.post("/user_lab_progress", status_code=201) #check exercise quiz complete 
# async def create_user_progress(
#     progress_data: UserProgressCreate,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     # Check if the record already exists (based on PK constraint)
#     existing_progress = db.query(UserProgress).filter_by(
#         user_id=current_user.id,
#         content_type=progress_data.content_type,
#         content_id=progress_data.content_id
#     ).first()

#     if existing_progress:
#         raise HTTPException(status_code=409, detail="Progress already recorded for this content.")

#     new_progress = UserProgress(
#         user_id=current_user.id,
#         content_type=progress_data.content_type,
#         content_id=progress_data.content_id
#     )
#     db.add(new_progress)
#     db.commit()

#     return Response(status_code=201)

# @router.get('/lab_quiz',)
