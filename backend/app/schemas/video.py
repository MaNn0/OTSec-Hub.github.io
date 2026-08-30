from pydantic import BaseModel, Field
from typing import Optional, List
from .quiz import QuizCreate, QuizOut, QuizUpdate

class VideoCreate(BaseModel):
    title: str = Field(...)
    subtitle: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    url: str = Field(...)
    quizzes: List[QuizCreate]
    
class VideoOut(BaseModel):
    id: int
    title: Optional[str] = ""
    subtitle: Optional[str] = ""
    description: Optional[str] = ""
    url: str
    quizzes: List[QuizOut]
    
    views_count: int = 0
    likes_count: int = 0
    is_liked_by_user: bool = False
    
    class Config:
        from_attributes = True

class VideoUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    quizzes: Optional[List[QuizUpdate]] = None
    
    class Config:
        from_attributes = True