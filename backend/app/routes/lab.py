from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import text
from app.database import get_db
from app.models.userProgress import UserProgress
from app.models.lab import Lab
from app.models.video import OwnerLike, OwnerView  
from app.models.quiz import Quiz
from fastapi.responses import JSONResponse
from app.schemas.userProgress import UserProgressCreate
from app.schemas.lab import LabOut, LabCreate, LabUpdate
from app.auth.auth import get_current_user, get_optional_user
from app.models.user import User
from typing import List, Optional
from app.schemas.pagination import PaginatedResponse
from app.routes.announcements import create_automatic_announcement
from app.utils.streak import update_user_streak


router = APIRouter()

@router.post('/create_lab', response_model=LabOut)
def create_lab(
    lab_data: LabCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_lab = Lab(
        title=lab_data.title,
        lab_img=lab_data.lab_img,
        content=lab_data.content,
        views_count=0,
        likes_count=0
    )
    db.add(new_lab)
    db.flush() 

    for quiz in lab_data.quizzes:
        if not quiz.question or quiz.question.strip() == "" or quiz.question.strip().upper() == "EMPTY":
            continue
            
        new_quiz = Quiz(
            question=quiz.question,
            correct_answer=quiz.correct_answer,
            option1=quiz.options[0] if len(quiz.options) > 0 else None,
            option2=quiz.options[1] if len(quiz.options) > 1 else None,
            option3=quiz.options[2] if len(quiz.options) > 2 else None,
            option4=quiz.options[3] if len(quiz.options) > 3 else None,
            lab_id=new_lab.id
        )
        db.add(new_quiz)

    create_automatic_announcement(
        content_type="lab",
        content_id=new_lab.id,
        title=new_lab.title,
        image_url=new_lab.lab_img,
        db=db
    )

    db.commit()
    db.refresh(new_lab)
    return new_lab

@router.get('/get_lab/{id}', response_model=LabOut)
def get_lab(
    id: int, 
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(lambda: None)  
):
    lab = db.query(Lab).filter(Lab.id == id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
        
    is_liked = False
    if current_user and hasattr(current_user, 'id'):
        is_liked = db.query(OwnerLike).filter(
            OwnerLike.user_id == current_user.id,
            OwnerLike.resource_type == "lab",
            OwnerLike.resource_id == id
        ).first() is not None

    lab_out = LabOut.from_orm(lab)
    lab_out.is_liked_by_user = is_liked
    return lab_out

@router.get("/get_labs", response_model=PaginatedResponse[LabOut])
def get_labs(
    page: int = Query(1, ge=1),
    limit: int = Query(9, ge=1),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(lambda: None)
):
    labs_query = db.query(Lab).order_by(Lab.id.asc())
    total = labs_query.count()
    labs = (
        labs_query
        .options(selectinload(Lab.quizzes))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    
    liked_lab_ids = set()
    if current_user and hasattr(current_user, 'id'):
        liked_records = db.query(OwnerLike.resource_id).filter(
            OwnerLike.user_id == current_user.id,
            OwnerLike.resource_type == "lab"
        ).all()
        liked_lab_ids = {r[0] for r in liked_records}

    lab_items = []
    for lab in labs:
        lo = LabOut.from_orm(lab)
        lo.is_liked_by_user = lab.id in liked_lab_ids
        lab_items.append(lo)

    if not lab_items:
        raise HTTPException(status_code=404, detail="No labs found")

    return PaginatedResponse(
        total=total,
        page=page,
        limit=limit,
        items=lab_items
    )

@router.put("/update_lab/{lab_id}", response_model=LabOut)
def update_lab(lab_id: int, lab: LabUpdate, db: Session = Depends(get_db)):
    db_lab = db.query(Lab).filter(Lab.id == lab_id).first()

    if not db_lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    if lab.title:
        db_lab.title = lab.title
    if lab.lab_img:
        db_lab.lab_img = lab.lab_img
    if lab.content:
        db_lab.content = lab.content

    if lab.quizzes:
        for updated_quiz in lab.quizzes:
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
    db.refresh(db_lab)
    return db_lab

@router.delete("/delete_lab/{lab_id}", status_code=200)
def delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_lab = db.query(Lab).filter(Lab.id == lab_id).first()

    if not db_lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    
    db.query(OwnerLike).filter(
        OwnerLike.resource_type == "lab",
        OwnerLike.resource_id == lab_id
    ).delete(synchronize_session=False)

    db.query(OwnerView).filter(
        OwnerView.resource_type == "lab",
        OwnerView.resource_id == lab_id
    ).delete(synchronize_session=False)

    db.delete(db_lab)
    db.commit()
    return JSONResponse(content={"message": "Lab deleted successfully"})

@router.post("/user_lab_progress", status_code=201)
def create_user_progress(
    progress_data: UserProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_progress = db.query(UserProgress).filter_by(
        user_id=current_user.id,
        content_type=progress_data.content_type,
        content_id=progress_data.content_id
    ).first()

    if existing_progress:
        raise HTTPException(status_code=409, detail="Progress already recorded for this content.")

    new_progress = UserProgress(
        user_id=current_user.id,
        content_type=progress_data.content_type,
        content_id=progress_data.content_id
    )
    db.add(new_progress)
    db.commit()

    return Response(status_code=201)



@router.get("/interactions/metrics/lab/{resource_id}")
def get_lab_metrics(
    resource_id: int, 
    db: Session = Depends(get_db), 
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Safely handles syncing exact unique multi-user state payload to interaction bar components."""
    lab = db.query(Lab).filter(Lab.id == resource_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    is_liked = False
    is_viewed = False
    if current_user:
        is_liked = db.query(OwnerLike).filter_by(
            user_id=current_user.id, 
            resource_type="lab", 
            resource_id=resource_id
        ).first() is not None

        is_viewed = db.query(OwnerView).filter_by(
            user_id=current_user.id,
            resource_type="lab",
            resource_id=resource_id
        ).first() is not None

    return {
        "views_count": lab.views_count or 0,
        "likes_count": lab.likes_count or 0,
        "is_liked_by_user": is_liked,
        "is_viewed_by_user": is_viewed
    }

@router.post("/interactions/lab/view/{lab_id}")
def record_lab_view(
    lab_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers unique views per user profile securely."""
    existing_view = db.query(OwnerView).filter_by(
        user_id=current_user.id, 
        resource_type="lab", 
        resource_id=lab_id
    ).first()

    if not existing_view:
        try:
            new_view = OwnerView(user_id=current_user.id, resource_type="lab", resource_id=lab_id)
            db.add(new_view)
            
            # ORM Safe Update Engine
            db.query(Lab).filter(Lab.id == lab_id).update(
                {Lab.views_count: Lab.views_count + 1},
                synchronize_session=False
            )
            db.commit()
        except Exception:
            db.rollback()
            
    return {"message": "View validation handled cleanly."}


@router.post("/interactions/lab/like/{lab_id}")
def toggle_lab_like(
    lab_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    user_id = current_user.id
    
    existing_like = db.query(OwnerLike).filter(
        OwnerLike.user_id == user_id,
        OwnerLike.resource_type == "lab",
        OwnerLike.resource_id == lab_id
    ).first()
    
    if existing_like:
        db.delete(existing_like)
        db.execute(text("UPDATE labs SET likes_count = GREATEST(0, likes_count - 1) WHERE id = :id"), {"id": lab_id})
        db.commit()
        
        lab = db.query(Lab).filter(Lab.id == lab_id).first()
        return {
            "views_count": lab.views_count if lab else 0,
            "likes_count": lab.likes_count if lab else 0,
            "is_liked_by_user": False,
            "is_viewed_by_user": True
        }
    else:
        try:
            new_like = OwnerLike(user_id=user_id, resource_type="lab", resource_id=lab_id)
            db.add(new_like)
            db.execute(text("UPDATE labs SET likes_count = likes_count + 1 WHERE id = :id"), {"id": lab_id})
            db.commit()
        except Exception:
            db.rollback()

        lab = db.query(Lab).filter(Lab.id == lab_id).first()
        return {
            "views_count": lab.views_count if lab else 0,
            "likes_count": lab.likes_count if lab else 0,
            "is_liked_by_user": True,
            "is_viewed_by_user": True
        }