from pydantic import BaseModel
from app.schemas.exercise import ExerciseOut
from typing import List, Optional

class ExerciseSubmissionCreate(BaseModel):
    answers: List[str]  
    status: Optional[str] = "pending"

class ExerciseSubmissionOut(BaseModel):
    id: int
    user_id: int
    exercise_id: int
    answers: List[str]
    exercise: ExerciseOut
    status: str
    admin_note: Optional[str] = None

    class Config:
        from_attributes = True
        
class ExerciseSubmissionUpdate(BaseModel):
    status: str
    admin_note: Optional[str] = None
    answers: Optional[List[str]] = None  # Allows users to overwrite answers arrays