import re
import bleach
from datetime import date
from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, Dict, Any, List

#Password regex pattern
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")

def validate_password_complexity(v: Optional[str]) -> Optional[str]:
    if v is not None and not PASSWORD_REGEX.match(v):
        raise ValueError(
            "Password must be at least 8 characters long and contain at least "
            "one uppercase letter, one lowercase letter, one number, and one special character (@$!%*?&)."
        )
    return v

def clean_string(v: Optional[str], max_len: int = 255) -> Optional[str]:
    if v is None:
        return v
    v = v.strip()
    # Strip all HTML/script tags from user names or general text
    v = bleach.clean(v, tags=[], strip=True)
    if len(v) > max_len:
        raise ValueError(f"Input exceeds maximum allowed length of {max_len} characters.")
    return v

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str
    captcha_token: str

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        cleaned = clean_string(v, max_len=100)
        if not cleaned or len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long.")
        return cleaned

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_complexity(v)

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    is_banned: bool = False
    is_verified: bool = True
    streak_count: int = 0
    streak_freezes: int = 0
    last_active_date: Optional[date] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        return clean_string(v, max_len=100)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: Optional[str]) -> Optional[str]:
        return validate_password_complexity(v)

    class Config:
        from_attributes = True
        
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[Dict[str, Any]] = None  # Allows the streak dictionary to pass through

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class CompletionResponse(BaseModel):
    is_completed: bool
    streak_count: int
    streak_freezes: int
    last_active_date: Optional[date] = None
    new_badges: Optional[List[Dict[str, Any]]] = []