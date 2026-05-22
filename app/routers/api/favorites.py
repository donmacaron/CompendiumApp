from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from dependencies import get_db, require_user
from models.user import User
from models.favorite import UserFavorite
from models.page import Page
from models.system import System

router = APIRouter(prefix="/api/favorites", tags=["favorites"])
templates = Jinja2Templates(directory="templates")


def _is_fav(db: Session, user_id: int, page_id: int) -> bool:
    return db.query(UserFavorite).filter(
        UserFavorite.user_id == user_id,
        UserFavorite.page_id == page_id
    ).first() is not None


@router.post("/toggle/{page_id}", response_class=HTMLResponse)
def toggle_favorite(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user)
):
    """HTMX endpoint — returns just the button HTML."""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        return HTMLResponse("", status_code=404)

    existing = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.page_id == page_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        is_fav = False
    else:
        try:
            db.add(UserFavorite(user_id=current_user.id, page_id=page_id))
            db.commit()
            is_fav = True
        except IntegrityError:
            db.rollback()
            is_fav = True

    # Return updated button HTML for HTMX swap
    return HTMLResponse(_fav_button_html(page_id, is_fav))


def _fav_button_html(page_id: int, is_fav: bool) -> str:
    star = "★" if is_fav else "☆"
    label = "Saved" if is_fav else "Save"
    active_style = "color:#8b2e2e;font-weight:600;" if is_fav else "color:#7a5c3a;"
    return f'''<button
  hx-post="/api/favorites/toggle/{page_id}"
  hx-target="this"
  hx-swap="outerHTML"
  class="fav-btn"
  style="border:1px solid var(--border,#c4a96b);background:var(--bg-alt,#ede0b0);
         padding:5px 14px;cursor:pointer;font-size:0.9em;{active_style}
         border-radius:3px;font-family:inherit;transition:all 0.15s">
  {star} {label}
</button>'''
