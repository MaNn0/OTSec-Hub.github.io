from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class CommunityInteraction(Base):
    """Tracks raw metrics directly inside a unified, optimized table row."""
    __tablename__ = "community_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String, nullable=False)  # "lab" or "video"
    resource_id = Column(Integer, nullable=False)
    views_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('resource_type', 'resource_id', name='uq_resource_type_id'),
    )

class CommunityLike(Base):
    """Tracks distinct user likes to prevent double voting."""
    __tablename__ = "community_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String, nullable=False)  # "lab" or "video"
    resource_id = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'resource_type', 'resource_id', name='uq_user_community_like'),
    )

class CommunityView(Base):
    """Tracks distinct user views to enforce a strict single-view lock per profile."""
    __tablename__ = "community_views"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String, nullable=False)  # "lab" or "video"
    resource_id = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'resource_type', 'resource_id', name='uq_user_community_view'),
    )
    
class CommentReport(Base):
    """Tracks unique user submissions on reported comments to block double reporting."""
    __tablename__ = "comment_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_id = Column(Integer, ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=False)
    reported_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'comment_id', name='uq_user_comment_report'),
    )

class CommunityComment(Base):
    """Handles 2-Level Nested Comments with an explicit self-referencing relationship."""
    __tablename__ = "community_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String, nullable=False)  # "lab" or "video"
    resource_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    parent_id = Column(Integer, ForeignKey("community_comments.id", ondelete="CASCADE"), nullable=True)
    
    report_count = Column(Integer, default=0, nullable=False)
    is_under_review = Column(Boolean, default=False, nullable=False)
    
    user = relationship("User")
    parent = relationship("CommunityComment", remote_side=[id], back_populates="replies")
    replies = relationship("CommunityComment", back_populates="parent", cascade="all, delete-orphan")

class ModeratedCommentLog(Base):
    """Stores a history of all comments deleted via reports or admin review."""
    __tablename__ = "moderated_comment_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    original_comment_id = Column(Integer, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    reason_for_deletion = Column(String, nullable=False)
    deleted_at = Column(DateTime, server_default=func.now())
    
    author = relationship("User")