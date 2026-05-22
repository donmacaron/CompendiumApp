from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("pages.id"), nullable=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    language = Column(String(10), nullable=True, default="en")
    content = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    system = relationship("System", back_populates="pages")
    parent = relationship("Page", remote_side=[id], back_populates="children")
    children = relationship(
        "Page", back_populates="parent",
        order_by="Page.sort_order", cascade="all, delete"
    )
    revisions = relationship("PageRevision", back_populates="page", cascade="all, delete")
    favorites = relationship("UserFavorite", back_populates="page", cascade="all, delete")
    translations = relationship("PageTranslation", back_populates="page", cascade="all, delete")
