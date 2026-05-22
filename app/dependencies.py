from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User, Role
from services.auth import decode_token


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        return None  # banned users treated as logged out
    return user


def require_user(user: User | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=303,
            headers={"Location": "/auth/login"}
        )
    return user


def require_admin(user: User = Depends(require_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
