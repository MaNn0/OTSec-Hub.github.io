from pydantic import BaseModel, Field
from typing import Optional
import datetime


class PaperCreate(BaseModel):
    title: str = Field(...)
    journal: str = Field(...)
    authors: str = Field(...)
    date: datetime.date = Field(...)
    url: str = Field(...)
    abstract: str = Field(...)

    conference_place: Optional[str] = None
    doi: Optional[str] = None
    paper_type: Optional[str] = None
    keywords: Optional[str] = None


class PaperOut(BaseModel):
    id: int
    title: str
    journal: str
    authors: str
    date: datetime.date
    url: str
    abstract: str

    conference_place: Optional[str] = None
    doi: Optional[str] = None
    paper_type: Optional[str] = None
    keywords: Optional[str] = None

    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    status: Optional[str] = "approved"
    message: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    journal: Optional[str] = None
    authors: Optional[str] = None
    date: Optional[datetime.date] = None
    url: Optional[str] = None
    abstract: Optional[str] = None

    conference_place: Optional[str] = None
    doi: Optional[str] = None
    paper_type: Optional[str] = None
    keywords: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True
