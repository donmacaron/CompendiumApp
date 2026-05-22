from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models.user import User
from models.system import System
from services.search import search_pages

router = APIRouter(tags=["search"])
templates = Jinja2Templates(directory="templates")


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    q: str = Query(default=""),
    system: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user)
):
    results = []
    if q.strip():
        results = search_pages(q.strip(), db, system_slug=system, limit=30)

    systems = db.query(System).filter(
        System.is_published == True,
        System.is_archived == False
    ).order_by(System.name).all()

    return templates.TemplateResponse(
        request, "public/search.html",
        {
            "q": q,
            "system": system,
            "results": results,
            "systems": systems,
            "current_user": current_user,
            "count": len(results),
        }
    )
