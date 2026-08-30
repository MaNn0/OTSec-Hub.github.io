from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    journal = Column(String, nullable=False)
    authors = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    url = Column(String, nullable=False)
    abstract = Column(Text, nullable=False)

    conference_place = Column(String, nullable=True)
    doi = Column(String, nullable=True)
    paper_type = Column(String, nullable=True)
    keywords = Column(String, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False, default="approved")
    message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    user = relationship("User")

    @property
    def user_name(self):
        return self.user.name if self.user else None

    @property
    def user_role(self):
        return self.user.role if self.user else None
