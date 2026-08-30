import bleach
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

def clean_text(v: Optional[str], max_len: int) -> Optional[str]:
    if v is None:
        return v
    v = bleach.clean(v.strip(), tags=[], strip=True)
    if len(v) > max_len:
        raise ValueError(f"Field exceeds maximum allowed length of {max_len} characters.")
    return v

class VideoCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    subtitle: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5, max_length=5000)
    url: str
    status: str
    message: Optional[str] = None

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        cleaned = clean_text(v, 150)
        if not cleaned:
            raise ValueError("Title cannot be empty.")
        return cleaned

    @field_validator("subtitle")
    @classmethod
    def sanitize_subtitle(cls, v: str) -> str:
        cleaned = clean_text(v, 255)
        if not cleaned:
            raise ValueError("Subtitle cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        cleaned = clean_text(v, 5000)
        if not cleaned:
            raise ValueError("Description cannot be empty.")
        return cleaned

    @field_validator("url")
    @classmethod
    def sanitize_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Invalid URL protocol. Must start with http:// or https://")
        return v

class VideoOut(BaseModel):
    id: int
    title: str
    subtitle: str
    description: str
    url: str
    status: str
    user_id: int
    user_name: Optional[str]
    message: Optional[str]
    created_at: Optional[datetime] = None

    views_count: int = 0
    likes_count: int = 0
    
    is_completed: Optional[bool] = False
    new_badges: Optional[List[Dict[str, Any]]] = []

    class Config:
        from_attributes = True

class VideoUpdate(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True