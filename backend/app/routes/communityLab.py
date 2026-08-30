from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from app.database import get_db
from app.models.communityLab import CommunityLab
from app.schemas.communityLab import LabOut, LabCreate, LabUpdate
from app.auth.auth import get_current_user, admin_or_educator, admin_only
from app.models.community_interaction import CommunityInteraction  
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.models.user import User, community_lab_completions

from app.schemas.user import CompletionResponse
from app.utils.streak import update_user_streak
from app.utils.badge_engine import evaluate_user_badges
from app.routes.announcements import create_automatic_announcement

# Import Limiter instance
from app.routes.auth import limiter

router = APIRouter()


def _interaction_metrics_by_id(db: Session, labs) -> dict:
    """Fetch the interaction row for every lab in a single query, keyed by lab id."""
    ids = [lab.id for lab in labs]
    if not ids:
        return {}
    rows = db.query(CommunityInteraction).filter(
        CommunityInteraction.resource_type == "lab",
        CommunityInteraction.resource_id.in_(ids),
    ).all()
    return {row.resource_id: row for row in rows}


@router.post('/create_communityLab', response_model=LabOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_lab(
    request: Request,
    lab_data: LabCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LabOut:
    """
    Create a new community lab.
    """
    new_lab = CommunityLab(
        title=lab_data.title,
        lab_img=lab_data.lab_img,
        status=lab_data.status,
        topics=lab_data.topics,
        user_id=current_user.id,
        description=lab_data.description,
        content=lab_data.content  
    )
    db.add(new_lab)
    db.commit()
    db.refresh(new_lab)
    
    new_badges = evaluate_user_badges(current_user.id, db)
    new_lab.new_badges = new_badges
    return new_lab

@router.post("/community/lab/{id}/complete", response_model=CompletionResponse)
def toggle_lab_completion(
    id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    lab = db.query(CommunityLab).filter(CommunityLab.id == id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Match video toggle logic EXACTLY[cite: 12]
    if lab in current_user.completed_labs:
        current_user.completed_labs.remove(lab)
        is_completed = False
    else:
        current_user.completed_labs.append(lab)
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


@router.get('/get_communityLab/{id}', response_model=LabOut)
def get_lab(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LabOut:
    lab = db.query(CommunityLab).filter(CommunityLab.id == id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="CommunityLab not found")
    
    user = db.query(User).filter(User.id == lab.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interaction = db.query(CommunityInteraction).filter_by(resource_type="lab", resource_id=id).first()
    
    is_completed = False
    if current_user and lab in current_user.completed_labs:
        is_completed = True

    # FIX: Construct a dictionary so Pydantic cannot strip our dynamic fields[cite: 12]
    lab_data = {
        "id": lab.id,
        "title": lab.title,
        "lab_img": lab.lab_img,
        "status": lab.status,
        "user_id": lab.user_id,
        "user_name": user.name,
        "content": lab.content,
        "description": lab.description,
        "topics": lab.topics,
        "created_at": lab.created_at,
        "views_count": interaction.views_count if interaction else 0,
        "likes_count": interaction.likes_count if interaction else 0,
        "is_completed": is_completed
    }

    return lab_data


@router.get('/get_communityLabs', response_model=List[LabOut])
def get_labs(db: Session = Depends(get_db)) -> List[LabOut]:
    """
    Get all community labs.
    """
    labs = db.query(CommunityLab).options(selectinload(CommunityLab.user)).all()
    if not labs:
        raise HTTPException(status_code=404, detail="No CommunityLabs found")

    metrics = _interaction_metrics_by_id(db, labs)
    for lab in labs:
        interaction = metrics.get(lab.id)
        lab.views_count = interaction.views_count if interaction else 0
        lab.likes_count = interaction.likes_count if interaction else 0

    return labs

@router.get('/get_userCommunityLabs', response_model=List[LabOut])
def get_labs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> List[LabOut]:
    """
    Get all community labs submitted by the current user.
    """
    labs = db.query(CommunityLab).options(selectinload(CommunityLab.user)).filter(CommunityLab.user_id == current_user.id).all()

    if not labs:
        return []

    metrics = _interaction_metrics_by_id(db, labs)
    for lab in labs:
        interaction = metrics.get(lab.id)
        lab.views_count = interaction.views_count if interaction else 0
        lab.likes_count = interaction.likes_count if interaction else 0

    return labs


@router.put("/update_communityLab/{lab_id}", response_model=LabOut)
@limiter.limit("5/minute")
async def update_lab(
    request: Request,
    lab_id: int,
    lab: LabUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LabOut:
    """
    Update a community lab by ID.
    """
    db_lab = db.query(CommunityLab).filter(CommunityLab.id == lab_id).first()
    if not db_lab:
        raise HTTPException(status_code=404, detail="CommunityLab not found")

    prev_status = (db_lab.status or "").strip().lower()

    if lab.status is not None:
        db_lab.status = lab.status
    if lab.description is not None:
        db_lab.description = lab.description
    if lab.topics is not None:
        db_lab.topics = lab.topics
    if lab.content is not None:
        db_lab.content = lab.content

    now_status = (db_lab.status or "").strip().lower()
    if now_status != prev_status and now_status in ("approved", "rejected"):
        create_automatic_announcement(
            content_type="community_lab",
            content_id=db_lab.id,
            title=now_status,
            image_url=None,
            db=db,
            user_id=db_lab.user_id,
        )

    db.commit()
    db.refresh(db_lab)
    return db_lab


@router.delete("/delete_communityLab/{lab_id}", status_code=200)
def delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Delete a community lab by ID.
    """
    db_lab = db.query(CommunityLab).filter(CommunityLab.id == lab_id).first()
    
    if not db_lab:
        raise HTTPException(status_code=404, detail="CommunityLab not found")

    db.delete(db_lab)
    db.commit()
    return JSONResponse(content={"message": "CommunityLab deleted successfully"})