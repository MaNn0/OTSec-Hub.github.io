from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base

class ExerciseSubmission(Base):
    __tablename__ = "exercise_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercise.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    status = Column(String, default="pending")
    admin_note = Column(String, nullable=True)  
    
    exercise = relationship("Exercise", back_populates="submissions")