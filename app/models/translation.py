from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class PageTranslation(Base):
    __tablename__ = "page_translations"

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    language = Column(String(10), nullable=False)
    title = Column(String(255), nullable=False, default="")
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    page = relationship("Page", back_populates="translations")

    __table_args__ = (UniqueConstraint("page_id", "language"),)
