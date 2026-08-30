from sqlalchemy import Column, Integer, Boolean, String, ForeignKey, Date, Table, Text, TIMESTAMP, UniqueConstraint, func
from app.database import Base
from sqlalchemy.orm import relationship



# Pivot tables for community completion tracking
community_lab_completions = Table(
    'community_lab_completions', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('lab_id', Integer, ForeignKey('community_labs.id'), primary_key=True)
)

community_video_completions = Table(
    'community_video_completions', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('video_id', Integer, ForeignKey('community_videos.id'), primary_key=True)
)

# Pivot tables for owner resource completion tracking
owner_video_completions = Table(
    'owner_video_completions', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('video_id', Integer, ForeignKey('videos.id'), primary_key=True)
)

owner_lab_completions = Table(
    'owner_lab_completions', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('lab_id', Integer, ForeignKey('labs.id'), primary_key=True)
)

owner_exercise_completions = Table(
    'owner_exercise_completions', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('exercise_id', Integer, ForeignKey('exercise.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default='member')
    is_verified = Column(Boolean, default=False)  
    verification_token = Column(String, nullable=True)
    is_banned = Column(Boolean, default=False, nullable=False)
    
    # GAMIFICATION TRACKING COLUMNS
    streak_count = Column(Integer, default=0, nullable=False)
    last_active_date = Column(Date, nullable=True)
    streak_freezes = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user_progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    community_labs = relationship("CommunityLab", back_populates="user")
    community_videos = relationship("CommunityVideo", back_populates="user")
    
    # COMMUNITY COMPLETION TRACKING RELATIONSHIPS
    completed_labs = relationship("CommunityLab", secondary=community_lab_completions)
    completed_videos = relationship("CommunityVideo", secondary=community_video_completions)

    # OWNER RESOURCE COMPLETION TRACKING RELATIONSHIPS
    completed_owner_videos = relationship("Video", secondary=owner_video_completions)
    completed_owner_labs = relationship("Lab", secondary=owner_lab_completions)
    completed_owner_exercises = relationship("Exercise", secondary=owner_exercise_completions)
    
    
#Badges Section
class Badge(Base):
    __tablename__ = 'badges'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    realm = Column(String(100), nullable=False)
    track = Column(String(100), nullable=False)
    tier = Column(String(50), nullable=False)
    threshold = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=False)


class UserBadge(Base):
    __tablename__ = 'user_badges'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    badge_id = Column(Integer, ForeignKey('badges.id', ondelete='CASCADE'), nullable=False)
    earned_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'badge_id', name='unique_user_badge'),
    )
    