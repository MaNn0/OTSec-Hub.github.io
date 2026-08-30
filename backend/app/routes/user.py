from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut, Token, UserLogin, UserUpdate
from app.models.user import User, Badge, UserBadge
from app.auth.auth import get_current_user, admin_only  # Added admin_only constraint guard
from app.database import get_db
from passlib.hash import bcrypt

from typing import List
import uuid
from dotenv import load_dotenv
import os

load_dotenv()
router = APIRouter()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/users/me/badges")
def get_my_badges(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Fetches all badges earned by the currently logged-in user, sorted by most recent."""
    rows = (
        db.query(Badge, UserBadge.earned_at)
        .join(UserBadge, Badge.id == UserBadge.badge_id)
        .filter(UserBadge.user_id == current_user.id)
        .order_by(UserBadge.earned_at.desc())
        .all()
    )

    return [
        {
            "id": badge.id,
            "name": badge.name,
            "realm": badge.realm,
            "track": badge.track,
            "tier": badge.tier,
            "threshold": badge.threshold,
            "description": badge.description,
            "image_url": badge.image_url,
            "earned_at": earned_at.isoformat() if earned_at else None,
        }
        for badge, earned_at in rows
    ]


@router.get("/badges")
def get_all_badges(db: Session = Depends(get_db)):
    """Fetches the master list of all available badges to build the locked grid."""
    all_badges = db.query(Badge).all()
    return all_badges


@router.get("/users/", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    users = db.query(User).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found")
    return users

@router.put("/update_user/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile.")

    if user.name:
        db_user.name = user.name
    if user.password:
        db_user.password = bcrypt.hash(user.password)

    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/users/{user_id}/toggle-ban", response_model=UserOut)
def toggle_user_ban(
    user_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_only)  # Locked down strictly to administrative credentials
):
    """Safely toggles administrative account bans without throwing away user records."""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Administrative restriction prevents self-suspensions.")
        
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Target account record absent.")
    if (db_user.role or "").lower() == "admin":
        raise HTTPException(status_code=400, detail="Admin accounts cannot be banned.")

    db_user.is_banned = not db_user.is_banned
    db.commit()
    db.refresh(db_user)
    return db_user