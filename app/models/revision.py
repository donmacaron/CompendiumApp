from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from database import Base


class PageRevision(Base):
    __tablename__ = "page_revisions"

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    page = relationship("Page", back_populates="revisions")
    user = relationship("User")
