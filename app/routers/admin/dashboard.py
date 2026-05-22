from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db, require_admin
from models.user import User
from models.system import System
from models.page import Page
from models.revision import PageRevision

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    stats = {
        "systems_total":     db.query(System).filter(System.is_archived == False).count(),
        "systems_published": db.query(System).filter(System.is_published == True, System.is_archived == False).count(),
        "pages_total":       db.query(Page).count(),
        "pages_published":   db.query(Page).filter(Page.is_published == True).count(),
        "users_total":       db.query(User).count(),
    }

    recent_pages = db.query(Page).order_by(Page.updated_at.desc()).limit(8).all()

    # Enrich with system info
    recent = []
    for p in recent_pages:
        sys = db.query(System).filter(System.id == p.system_id).first()
        recent.append({"page": p, "system": sys})

    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"stats": stats, "recent": recent, "current_user": current_user}
    )
