from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db, require_user, get_current_user
from models.user import User
from models.favorite import UserFavorite
from models.page import Page
from models.system import System

router = APIRouter(prefix="/user", tags=["user"])
templates = Jinja2Templates(directory="templates")

HISTORY_COOKIE = "reading_history"
HISTORY_MAX = 20


def _get_history_ids(request: Request) -> list[int]:
    raw = request.cookies.get(HISTORY_COOKIE, "")
    ids = []
    for part in raw.split(","):
        try:
            ids.append(int(part.strip()))
        except ValueError:
            pass
    return ids


def _set_history_cookie(response: Response, ids: list[int]):
    value = ",".join(str(i) for i in ids[:HISTORY_MAX])
    response.set_cookie(
        HISTORY_COOKIE, value,
        max_age=60 * 60 * 24 * 30,
        httponly=False,
        samesite="lax"
    )


@router.get("/profile", response_class=HTMLResponse)
def profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    # Favorites
    favs = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id
    ).order_by(UserFavorite.created_at.desc()).all()

    fav_pages = []
    for f in favs:
        page = db.query(Page).filter(Page.id == f.page_id).first()
        if page:
            system = db.query(System).filter(System.id == page.system_id).first()
            fav_pages.append({"page": page, "system": system})

    # Reading history
    history_ids = _get_history_ids(request)
    history = []
    for pid in history_ids:
        page = db.query(Page).filter(Page.id == pid).first()
        if page:
            system = db.query(System).filter(System.id == page.system_id).first()
            history.append({"page": page, "system": system})

    return templates.TemplateResponse(
        request, "user/profile.html",
        {
            "current_user": current_user,
            "fav_pages": fav_pages,
            "history": history,
        }
    )


@router.get("/favorites", response_class=HTMLResponse)
def favorites(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    favs = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id
    ).order_by(UserFavorite.created_at.desc()).all()

    # Group by system
    grouped: dict = {}
    for f in favs:
        page = db.query(Page).filter(Page.id == f.page_id).first()
        if not page:
            continue
        system = db.query(System).filter(System.id == page.system_id).first()
        if not system:
            continue
        key = system.id
        if key not in grouped:
            grouped[key] = {"system": system, "pages": []}
        grouped[key]["pages"].append(page)

    return templates.TemplateResponse(
        request, "user/favorites.html",
        {
            "current_user": current_user,
            "groups": list(grouped.values()),
        }
    )
