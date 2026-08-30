from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String, nullable=False, server_default="general")
    content_id = Column(Integer, nullable=False, server_default="0")
    image = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
