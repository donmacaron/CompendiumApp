from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class UserFavorite(Base):
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    page = relationship("Page", back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "page_id"),)
