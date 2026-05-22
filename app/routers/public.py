from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user
from models.user import User
from models.system import System
from models.page import Page
from models.favorite import UserFavorite
from models.translation import PageTranslation
from services.page_tree import build_tree

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="templates")

HISTORY_COOKIE = "reading_history"
HISTORY_MAX = 20

LANG_FLAGS = {
    "en": "\U0001f1ec\U0001f1e7",
    "ru": "\U0001f1f7\U0001f1fa",
    "de": "\U0001f1e9\U0001f1ea",
    "fr": "\U0001f1eb\U0001f1f7",
    "es": "\U0001f1ea\U0001f1f8",
    "it": "\U0001f1ee\U0001f1f9",
    "pl": "\U0001f1f5\U0001f1f1",
    "pt": "\U0001f1f5\U0001f1f9",
    "zh": "\U0001f1e8\U0001f1f3",
    "ja": "\U0001f1ef\U0001f1f5",
}


def _is_admin(user) -> bool:
    if not user:
        return False
    return getattr(user.role, "value", user.role) == "admin"


def _is_fav(db: Session, user, page_id: int) -> bool:
    if not user:
        return False
    return db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id,
        UserFavorite.page_id == page_id
    ).first() is not None


def _get_history_ids(request: Request) -> list[int]:
    raw = request.cookies.get(HISTORY_COOKIE, "")
    ids = []
    for part in raw.split(","):
        try:
            ids.append(int(part.strip()))
        except ValueError:
            pass
    return ids


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user)
):
    systems = db.query(System).filter(
        System.is_published == True,
        System.is_archived == False
    ).all()
    return templates.TemplateResponse(
        request, "public/home.html",
        {"systems": systems, "current_user": current_user}
    )


@router.get("/s/{system_slug}", response_class=HTMLResponse)
def system_home(
    request: Request, system_slug: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user)
):
    system = db.query(System).filter(
        System.slug == system_slug, System.is_archived == False
    ).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if not system.is_published and not _is_admin(current_user):
        raise HTTPException(status_code=404, detail="System not found")

    top_pages = db.query(Page).filter(
        Page.system_id == system.id,
        Page.parent_id == None,
        Page.is_published == True
    ).order_by(Page.sort_order, Page.title).all()

    return templates.TemplateResponse(
        request, "public/system_home.html",
        {"system": system, "top_pages": top_pages, "current_user": current_user}
    )


@router.get("/s/{system_slug}/{page_slug}", response_class=HTMLResponse)
def page_view(
    request: Request, system_slug: str, page_slug: str,
    lang: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user)
):
    system = db.query(System).filter(
        System.slug == system_slug, System.is_archived == False
    ).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    if not system.is_published and not _is_admin(current_user):
        raise HTTPException(status_code=404, detail="System not found")

    page = db.query(Page).filter(
        Page.system_id == system.id, Page.slug == page_slug
    ).first()
    if not page or (not page.is_published and not _is_admin(current_user)):
        raise HTTPException(status_code=404, detail="Page not found")

    # View count
    page.view_count += 1
    db.commit()

    # Load all translations for this page
    translations = db.query(PageTranslation).filter(
        PageTranslation.page_id == page.id
    ).all()

    # Build available languages list: original + translations
    available_langs = []
    if system.translatable:
        original_lang = page.language or "en"
        available_langs.append({
            "code": original_lang,
            "label": original_lang.upper(),
            "flag": LANG_FLAGS.get(original_lang, "\U0001f310"),
            "is_original": True,
        })
        for t in translations:
            available_langs.append({
                "code": t.language,
                "label": t.language.upper(),
                "flag": LANG_FLAGS.get(t.language, "\U0001f310"),
                "is_original": False,
            })

    # Determine active language and content
    original_lang = page.language or "en"
    active_lang = lang if lang else original_lang

    active_title   = page.title
    active_content = page.content

    if active_lang != original_lang:
        translation = next(
            (t for t in translations if t.language == active_lang), None
        )
        if translation:
            active_title   = translation.title or page.title
            active_content = translation.content or page.content
        else:
            # Requested lang not found — fall back to original
            active_lang = original_lang

    # Tree for sidebar
    all_pages = db.query(Page).filter(
        Page.system_id == system.id, Page.is_published == True
    ).order_by(Page.sort_order, Page.title).all()
    tree = build_tree(all_pages)

    # Breadcrumb
    breadcrumb = []
    cur = page
    while cur:
        breadcrumb.insert(0, cur)
        cur = db.query(Page).filter(Page.id == cur.parent_id).first() if cur.parent_id else None

    is_fav = _is_fav(db, current_user, page.id)

    # Reading history cookie
    history_ids = _get_history_ids(request)
    history_ids = [page.id] + [i for i in history_ids if i != page.id]
    history_ids = history_ids[:HISTORY_MAX]

    response = templates.TemplateResponse(
        request, "public/page.html",
        {
            "system": system,
            "page": page,
            "active_title": active_title,
            "active_content": active_content,
            "active_lang": active_lang,
            "available_langs": available_langs,
            "tree": tree,
            "breadcrumb": breadcrumb,
            "current_user": current_user,
            "is_fav": is_fav,
        }
    )
    response.set_cookie(
        HISTORY_COOKIE,
        ",".join(str(i) for i in history_ids),
        max_age=60 * 60 * 24 * 30,
        httponly=False, samesite="lax"
    )
    return response
