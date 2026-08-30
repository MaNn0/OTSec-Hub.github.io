import os
import secrets
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, Body, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from ..models.user import User
from ..schemas.user import UserOut
from ..auth.email import send_educator_invite_email
from ..auth.verification import create_educator_invite_token
from ..auth.auth import admin_only
from ..database import get_db
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()


@router.post("/add_educator", response_model=UserOut)
async def add_educator(
    background_tasks: BackgroundTasks,
    email: str = Body(...),
    name: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    token = create_educator_invite_token(email)
    placeholder_password = pwd_context.hash(secrets.token_urlsafe(32))
    db_user = User(
        name=name.strip(),
        email=email.strip(),
        password=placeholder_password,
        role="educator",
        is_verified=False,
        verification_token=token,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    redirect_url = f"{os.getenv('REACT_DOT_SERVER')}/complete-invite"
    await send_educator_invite_email(
        email=email,
        name=name,
        token=token,
        redirect_url=redirect_url,
        background_tasks=background_tasks,
    )

    return db_user
