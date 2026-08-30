from pydantic import BaseModel, Field
from typing import Optional, List
from .quiz import QuizCreate, QuizOut, QuizUpdate

class LabCreate(BaseModel):
    content: str
    title: str
    lab_img : str
    quizzes: List[QuizCreate]
    
class LabOut(BaseModel):
    id: int
    content: str
    title: str
    lab_img : str
    quizzes: List[QuizOut]
    
    views_count: int = 0
    likes_count: int = 0
    is_liked_by_user: bool = False
    
    class Config:
        from_attributes=True
    
class LabUpdate(BaseModel):
    content: Optional[str] = None
    title: str
    lab_img : str
    quizzes: Optional[List[QuizUpdate]] = None
    
    class Config:
        from_attributes = True