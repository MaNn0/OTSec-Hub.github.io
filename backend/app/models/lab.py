from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Lab(Base):
    __tablename__ = "labs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    lab_img = Column(String, nullable=False)
    content = Column(String, nullable=False)
    
    views_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    
    quizzes = relationship("Quiz", back_populates="lab", cascade="all, delete-orphan")