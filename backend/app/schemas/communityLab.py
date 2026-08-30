import bleach
from pydantic import BaseModel, field_validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Safe HTML tags allowed inside Markdown content renderings
SAFE_MARKDOWN_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'b', 'i', 'strong', 'em', 'p', 'br',
    'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'img', 'hr', 'table',
    'thead', 'tbody', 'tr', 'th', 'td'
]
SAFE_MARKDOWN_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height']
}

class LabCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    lab_img: str
    status: str
    content: str  
    description: Optional[str] = None
    topics: Optional[str] = None

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        cleaned = bleach.clean(v.strip(), tags=[], strip=True)
        if not cleaned:
            raise ValueError("Title cannot be empty.")
        return cleaned

    @field_validator("description", "topics")
    @classmethod
    def sanitize_plain_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return bleach.clean(v.strip(), tags=[], strip=True)

    @field_validator("content")
    @classmethod
    def sanitize_markdown_content(cls, v: str) -> str:
        # Strip dangerous tags like <script> or <iframe> while preserving safe Markdown HTML elements :)
        cleaned = bleach.clean(
            v.strip(),
            tags=SAFE_MARKDOWN_TAGS,
            attributes=SAFE_MARKDOWN_ATTRIBUTES,
            strip=True
        )
        if not cleaned or len(cleaned) == 0:
            raise ValueError("Lab content cannot be empty.")
        return cleaned

class LabOut(BaseModel):
    id: int
    title: str
    lab_img: str
    status: str
    user_id: int
    user_name: Optional[str]
    content: str
    description: Optional[str] = None
    topics: Optional[str] = None
    created_at: Optional[datetime] = None
    
    views_count: int = 0
    likes_count: int = 0
    
    is_completed: Optional[bool] = False
    new_badges: Optional[List[Dict[str, Any]]] = []
    
    class Config:
        from_attributes = True

class LabUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    topics: Optional[str] = None
    content: Optional[str] = None

    @field_validator("content")
    @classmethod
    def sanitize_markdown_content(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return bleach.clean(
            v.strip(),
            tags=SAFE_MARKDOWN_TAGS,
            attributes=SAFE_MARKDOWN_ATTRIBUTES,
            strip=True
        )

    class Config:
        from_attributes = True