from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from database import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    url = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
