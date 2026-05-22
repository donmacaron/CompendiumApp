from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from database import Base


class System(Base):
    __tablename__ = "systems"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    abbreviation = Column(String(20), nullable=True)
    banner_path = Column(String(500), nullable=True)
    logo_path = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    translatable = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    theme = Column(JSON, nullable=True, default=dict)

    pages = relationship("Page", back_populates="system", cascade="all, delete")
