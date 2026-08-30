from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base

class Exercise(Base):
    __tablename__ = "exercise"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=False)
    content = Column(String, nullable=False)
    questions = Column(JSON, nullable=True)
    
    # Atomic Metric Nodes for Free Tier Preservation
    views_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    
    submissions = relationship("ExerciseSubmission", back_populates="exercise", cascade="all, delete-orphan")