from sqlalchemy import Column, Integer, Boolean, String, ForeignKey, DateTime, func, UniqueConstraint
from app.database import Base
from sqlalchemy.orm import relationship

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    subtitle = Column(String, nullable=True)
    description = Column(String, nullable=True)
    url = Column(String, index=True, nullable=False)
    
    # Atomic Metrics Columns for Free-Tier Preservation
    views_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    quizzes = relationship("Quiz", back_populates="video", cascade="all, delete-orphan")


class OwnerLike(Base):
    __tablename__ = 'owner_likes'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    resource_type = Column(String(50), index=True, nullable=False) # 'video', 'lab', or 'exercise'
    resource_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Hard database-level guard against duplicate like data entry expansion
    __table_args__ = (
        UniqueConstraint('user_id', 'resource_type', 'resource_id', name='unique_user_owner_like'),
    )


class OwnerView(Base):
    __tablename__ = 'owner_views'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    resource_type = Column(String(50), index=True, nullable=False) # 'video', 'lab', or 'exercise'
    resource_id = Column(Integer, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Unique constraint prevents users from logging infinite views on reload
    __table_args__ = (
        UniqueConstraint('user_id', 'resource_type', 'resource_id', name='unique_user_owner_view'),
    )