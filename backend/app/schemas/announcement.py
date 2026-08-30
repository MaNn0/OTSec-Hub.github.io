from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    image: Optional[str] = None

    class Config:
        from_attributes = True


class AnnouncementOut(BaseModel):
    id: int
    content_type: str
    content_id: int
    title: Optional[str] = None
    message: Optional[str] = None
    image: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnnouncementUpdate(BaseModel):
    content_type: str = Field(..., min_length=1)
    content_id: int = Field(0, ge=0)
    title: str = Field(..., min_length=1)
    message: Optional[str] = None
    image: Optional[str] = None

    class Config:
        from_attributes = True
