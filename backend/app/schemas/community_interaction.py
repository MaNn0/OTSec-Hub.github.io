import bleach
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserMinOut(BaseModel):
    id: int
    user_name: str = Field(default="Anonymous", validation_alias="name")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class CommentReplyOut(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime
    parent_id: int
    report_count: int
    is_under_review: bool
    user: UserMinOut

    model_config = ConfigDict(from_attributes=True)

class CommentOut(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime
    parent_id: Optional[int] = None
    report_count: int
    is_under_review: bool
    user: UserMinOut
    replies: List[CommentReplyOut] = []
    
    new_badges: Optional[List[Dict[str, Any]]] = []

    model_config = ConfigDict(from_attributes=True)

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def sanitize_comment_content(cls, v: str) -> str:
        # Strip all HTML/JavaScript tags
        cleaned = bleach.clean(v.strip(), tags=[], strip=True)
        if not cleaned or len(cleaned) == 0:
            raise ValueError("Comment content cannot be empty or contain only invalid HTML tags.")
        if len(cleaned) > 2000:
            raise ValueError("Comment exceeds maximum allowed length of 2000 characters.")
        return cleaned

class MetricSummaryOut(BaseModel):
    views_count: int
    likes_count: int
    is_liked_by_user: bool
    is_viewed_by_user: bool
    streak_count: Optional[int] = None
    streak_freezes: Optional[int] = None