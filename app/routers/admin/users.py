from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db, require_admin
from models.user import User, Role

router = APIRouter(tags=["admin-users"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def users_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        request, "admin/users/list.html",
        {"users": users, "current_user": current_user, "Role": Role}
    )


@router.post("/{user_id}/role")
def set_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.id != current_user.id:
        try:
            user.role = Role(role)
            db.commit()
        except ValueError:
            pass
    return RedirectResponse("/admin/users/", status_code=303)


@router.post("/{user_id}/ban")
def toggle_ban(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.id != current_user.id:
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse("/admin/users/", status_code=303)
