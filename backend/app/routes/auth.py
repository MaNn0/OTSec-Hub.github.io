from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth.email import send_verification_email, send_email_change_verification
from ..auth.verification import create_verification_token, create_email_change_token, decode_verification_token
from ..models.user import User
from ..schemas.user import UserCreate, UserOut, Token, UserLogin, validate_password_complexity
from ..auth.auth import verify_password, create_access_token, get_current_user
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import os
from ..utils.captcha import verify_turnstile_token

#Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

load_dotenv()

router = APIRouter()

#camelCase to match frontend

@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
async def register(request: Request, user: UserCreate, background_tasks: BackgroundTasks
, db: Session = Depends(get_db)):
    
    # Verify CAPTCHA token
    client_ip = request.client.host if request.client else None
    await verify_turnstile_token(user.captcha_token, remote_ip=client_ip)
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password and create user
    hashed = bcrypt.hash(user.password)
    token = create_verification_token(user.email)
    db_user = User(name=user.name, email=user.email, password=hashed,is_verified=False, verification_token=token)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    await send_verification_email(
        email=user.email,
        name=user.name,
        token=token,
        redirect_url=f"{os.getenv('REACT_DOT_SERVER')}/verify-email",
        background_tasks=background_tasks,

    )
    return db_user;


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not db_user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not verified")
    
    if db_user.is_banned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="USER_BANNED")  #Banned user check
    
    access_token = create_access_token(data={"user_id": db_user.id})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "streak_count": db_user.streak_count,
            "streak_freezes": db_user.streak_freezes
        }
    }


class EmailChangeRequest(BaseModel):
    email: EmailStr


class CompleteInviteRequest(BaseModel):
    token: str
    password: str


@router.post("/request-email-change")
@limiter.limit("3/minute")
async def request_email_change(
    request: Request,
    payload: EmailChangeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_email = str(payload.email).strip().lower()
    current_email = (current_user.email or "").strip().lower()
    if new_email == current_email:
        raise HTTPException(status_code=400, detail="That is already your email.")

    taken = db.query(User).filter(User.email == new_email, User.id != current_user.id).first()
    if taken:
        raise HTTPException(status_code=400, detail="Email already registered")

    token = create_email_change_token(current_user.id, new_email)
    current_user.verification_token = token
    db.commit()

    await send_email_change_verification(
        email=new_email,
        name=current_user.name,
        token=token,
        redirect_url=f"{os.getenv('REACT_DOT_SERVER')}/verify-email",
        background_tasks=background_tasks,
    )
    return {"message": "Verification email sent. Confirm the new address to finish the change."}


@router.post("/complete-invite")
@limiter.limit("5/minute")
async def complete_educator_invite(
    request: Request,
    payload: CompleteInviteRequest,
    db: Session = Depends(get_db),
):
    token_payload = decode_verification_token(payload.token)
    if token_payload.get("purpose") != "invite_educator":
        raise HTTPException(status_code=400, detail="Invalid invitation token")

    email = token_payload.get("email")
    user = db.query(User).filter(User.email == email).first()
    if not user or user.role != "educator":
        raise HTTPException(status_code=404, detail="Invitation not found")
    if user.verification_token != payload.token:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="This invitation has already been used")

    try:
        password = validate_password_complexity(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user.password = bcrypt.hash(password)
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Account ready. You can log in with your email and password."}


@router.get("/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    payload = decode_verification_token(token)
    purpose = payload.get("purpose")

    if purpose == "change_email":
        user_id = payload.get("user_id")
        new_email = payload.get("email")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.verification_token != token:
            raise HTTPException(status_code=400, detail="Invalid token")
        taken = db.query(User).filter(User.email == new_email, User.id != user.id).first()
        if taken:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = new_email
        user.is_verified = True
        user.verification_token = None
        db.commit()
        return {"message": "Email updated successfully", "kind": "email_change"}

    if purpose != "verify_educator":
        raise HTTPException(status_code=400, detail="Invalid token purpose")

    email = payload.get("email")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    if user.verification_token != token:
        raise HTTPException(status_code=400, detail="Invalid token")

    user.is_verified = True
    user.verification_token = None
    db.commit()

    return {"message": "Email verified successfully", "kind": "signup"}