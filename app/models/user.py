import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base


class Role(str, enum.Enum):
    user = "user"
    editor = "editor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_path = Column(String(500), nullable=True)
    role = Column(Enum(Role), default=Role.user, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete")
