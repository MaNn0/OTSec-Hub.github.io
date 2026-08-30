from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import relationship
from app.database import Base

class CommunityLab(Base):
    __tablename__ = "community_labs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    lab_img = Column(String, nullable=False)
    topics = Column(String, nullable=True)
    status = Column(String, nullable=False)
    description = Column(String, nullable=True)
    content = Column(Text, nullable=False)  
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user = relationship("User", back_populates="community_labs")
    
    @property
    def user_name(self):
        return self.user.name if self.user else None