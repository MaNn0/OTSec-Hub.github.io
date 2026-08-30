from pydantic import BaseModel
from datetime import datetime
from .user import UserOut
from .quiz import QuizOut
from typing import List, Optional, Dict, Any
from datetime import date


class UserProgressCreate(BaseModel):
    content_type: str
    content_id: int
    quiz_completed: Optional[bool] = None 

class UserProgressOut(BaseModel):
    user_id: int
    content_type: str
    content_id: int
    quiz_completed: Optional[bool] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    content_title: Optional[str] = None
    
    # Newly added streak fields to pass through to the frontend
    streak_count: Optional[int] = None
    streak_freezes: Optional[int] = None
    last_active_date: Optional[date] = None
    
    new_badges: Optional[List[Dict[str, Any]]] = []
    
    class Config:
        from_attributes = True