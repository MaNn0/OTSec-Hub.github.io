from datetime import timedelta
from jose import jwt,JWTError
from fastapi import HTTPException
from .auth import create_access_token, SECRET_KEY, ALGORITHM
from dotenv import load_dotenv
import os

#create temp token for educator
def create_verification_token(email: str):
    return create_access_token(
        data={"email": email, "purpose": "verify_educator"},
        expires_delta=timedelta(hours=24)
    )

def verify_educator_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "verify_educator":
            raise HTTPException(status_code=400, detail="Invalid token purpose")
        return payload.get("email")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")


def create_email_change_token(user_id: int, email: str):
    return create_access_token(
        data={"email": email, "user_id": user_id, "purpose": "change_email"},
        expires_delta=timedelta(hours=24),
    )


def create_educator_invite_token(email: str):
    return create_access_token(
        data={"email": email, "purpose": "invite_educator"},
        expires_delta=timedelta(hours=48),
    )


def decode_verification_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")