from pydantic import BaseModel, Field
from typing import Optional, List

class ExerciseCreate(BaseModel):
    title: str
    subtitle: str
    content: str
    questions: Optional[List[str]] = Field(default_factory=list)

class ExerciseOut(BaseModel):
    id: int
    title: str
    subtitle: str
    content: str
    questions: List[str] = Field(default_factory=list)
    
    views_count: int = 0
    likes_count: int = 0
    is_liked_by_user: bool = False

    class Config:
        from_attributes = True

class ExerciseUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    content: Optional[str] = None
    questions: Optional[List[str]] = None

    class Config:
        from_attributes = True