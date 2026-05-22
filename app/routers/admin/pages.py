from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from dependencies import get_db, require_admin
from models.user import User
from models.system import System
from models.page import Page
from models.revision import PageRevision
from models.translation import PageTranslation
from services.slugify import unique_page_slug
from services.page_tree import build_tree, flatten_tree
from services.md_import import parse_md_file

router = APIRouter(tags=["admin-pages"])
templates = Jinja2Templates(directory="templates")

LANGUAGES = [
    ("en", "English"), ("ru", "Russian"), ("de", "German"),
    ("fr", "French"),  ("es", "Spanish"), ("it", "Italian"),
    ("pl", "Polish"),  ("pt", "Portuguese"), ("zh", "Chinese"), ("ja", "Japanese"),
]

MAX_MD_SIZE = 2 * 1024 * 1024  # 2 MB


def _get_system(system_id: int, db: Session):
    return db.query(System).filter(
        System.id == system_id, System.is_archived == False
    ).first()


def _parse_parent(val) -> Optional[int]:
    try:
        v = int(val)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _save_revision(db: Session, page: Page, user_id: int):
    db.add(PageRevision(
        page_id=page.id, user_id=user_id,
        title=page.title, content=page.content or "",
    ))


def _upsert_translation(db, page_id, language, title, content):
    db.query(PageTranslation).filter(
        PageTranslation.page_id == page_id
    ).delete(synchronize_session=False)
    db.add(PageTranslation(
        page_id=page_id, language=language,
        title=title, content=content,
    ))


# ── LIST ──────────────────────────────────────────────────────────────────────

@router.get("/{system_id}/", response_class=HTMLResponse)
def pages_list(
    request: Request, system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = _get_system(system_id, db)
    if not system:
        return RedirectResponse("/admin/systems/", status_code=303)
    pages = db.query(Page).filter(Page.system_id == system_id).all()
    flat  = flatten_tree(build_tree(pages))
    return templates.TemplateResponse(
        request, "admin/pages/list.html",
        {"system": system, "flat_pages": flat, "current_user": current_user}
    )


# ── IMPORT MD ─────────────────────────────────────────────────────────────────

@router.post("/{system_id}/import-md")
async def import_md(
    request: Request, system_id: int,
    file: UploadFile = File(...),
    parent_id: str = Form(""),
    language: str = Form("en"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = _get_system(system_id, db)
    if not system:
        return RedirectResponse("/admin/systems/", status_code=303)

    # Validate file type
    filename = file.filename or "import.md"
    if not filename.lower().endswith(".md"):
        pages = db.query(Page).filter(Page.system_id == system_id).all()
        flat  = flatten_tree(build_tree(pages))
        return templates.TemplateResponse(
            request, "admin/pages/list.html",
            {
                "system": system, "flat_pages": flat,
                "current_user": current_user,
                "import_error": "Only .md files are supported."
            }
        )

    content_bytes = await file.read()

    # Size check
    if len(content_bytes) > MAX_MD_SIZE:
        pages = db.query(Page).filter(Page.system_id == system_id).all()
        flat  = flatten_tree(build_tree(pages))
        return templates.TemplateResponse(
            request, "admin/pages/list.html",
            {
                "system": system, "flat_pages": flat,
                "current_user": current_user,
                "import_error": "File too large (max 2 MB)."
            }
        )

    # Parse markdown
    parsed = parse_md_file(content_bytes, filename)
    title  = parsed["title"]
    html   = parsed["html"]

    # Create draft page
    pid  = _parse_parent(parent_id)
    slug = unique_page_slug(title, db, system_id=system_id, parent_id=pid)

    page = Page(
        system_id=system_id, parent_id=pid,
        title=title, slug=slug,
        language=language,
        content=html,
        is_published=False,  # always draft — admin reviews before publishing
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    _save_revision(db, page, current_user.id)
    db.commit()

    # Redirect to editor so admin can review/adjust
    return RedirectResponse(
        f"/admin/pages/{system_id}/{page.id}?imported=1",
        status_code=303
    )


# ── NEW ───────────────────────────────────────────────────────────────────────

@router.get("/{system_id}/new", response_class=HTMLResponse)
def page_new_form(
    request: Request, system_id: int,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = _get_system(system_id, db)
    if not system:
        return RedirectResponse("/admin/systems/", status_code=303)
    all_pages = db.query(Page).filter(Page.system_id == system_id).order_by(Page.title).all()
    parent    = db.query(Page).filter(Page.id == parent_id).first() if parent_id else None
    return templates.TemplateResponse(
        request, "admin/pages/edit.html",
        {
            "system": system, "page": None, "translation": None,
            "all_pages": all_pages, "parent": parent,
            "languages": LANGUAGES, "current_user": current_user,
            "is_new": True, "revisions": [],
        }
    )


@router.post("/{system_id}/new")
def page_new(
    request: Request, system_id: int,
    title: str = Form(...),
    content: str = Form(""),
    language: str = Form("en"),
    parent_id: str = Form(""),
    tags: str = Form(""),
    published: Optional[str] = Form(None),
    translation_language: str = Form(""),
    translation_title: str = Form(""),
    translation_content: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = _get_system(system_id, db)
    if not system:
        return RedirectResponse("/admin/systems/", status_code=303)
    pid  = _parse_parent(parent_id)
    slug = unique_page_slug(title, db, system_id=system_id, parent_id=pid)
    page = Page(
        system_id=system_id, parent_id=pid,
        title=title.strip(), slug=slug, language=language,
        content=content, tags=tags.strip() or None,
        is_published=(published == "on"),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    _save_revision(db, page, current_user.id)
    if translation_language and (translation_title or translation_content):
        _upsert_translation(db, page.id, translation_language,
                            translation_title.strip() or title, translation_content)
    db.commit()
    return RedirectResponse(f"/admin/pages/{system_id}/{page.id}?saved=1", status_code=303)


# ── EDIT ──────────────────────────────────────────────────────────────────────

@router.get("/{system_id}/{page_id}", response_class=HTMLResponse)
def page_edit_form(
    request: Request, system_id: int, page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = _get_system(system_id, db)
    page   = db.query(Page).filter(Page.id == page_id, Page.system_id == system_id).first()
    if not system or not page:
        return RedirectResponse(f"/admin/pages/{system_id}/", status_code=303)
    translation = db.query(PageTranslation).filter(
        PageTranslation.page_id == page_id
    ).first()
    all_pages = db.query(Page).filter(
        Page.system_id == system_id, Page.id != page_id
    ).order_by(Page.title).all()
    revisions = db.query(PageRevision).filter(
        PageRevision.page_id == page_id
    ).order_by(PageRevision.created_at.desc()).limit(20).all()
    return templates.TemplateResponse(
        request, "admin/pages/edit.html",
        {
            "system": system, "page": page, "translation": translation,
            "all_pages": all_pages, "parent": None,
            "languages": LANGUAGES, "current_user": current_user,
            "is_new": False, "revisions": revisions,
        }
    )


@router.post("/{system_id}/{page_id}")
def page_edit(
    request: Request, system_id: int, page_id: int,
    title: str = Form(...),
    content: str = Form(""),
    language: str = Form("en"),
    parent_id: str = Form(""),
    tags: str = Form(""),
    published: Optional[str] = Form(None),
    translation_language: str = Form(""),
    translation_title: str = Form(""),
    translation_content: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    page = db.query(Page).filter(Page.id == page_id, Page.system_id == system_id).first()
    if not page:
        return RedirectResponse(f"/admin/pages/{system_id}/", status_code=303)
    _save_revision(db, page, current_user.id)
    page.title        = title.strip()
    page.content      = content
    page.language     = language
    page.parent_id    = _parse_parent(parent_id)
    page.tags         = tags.strip() or None
    page.is_published = (published == "on")
    db.commit()
    if translation_language and (translation_title or translation_content):
        _upsert_translation(db, page_id, translation_language,
                            translation_title.strip() or title, translation_content)
        db.commit()
    elif not translation_language:
        db.query(PageTranslation).filter(
            PageTranslation.page_id == page_id
        ).delete(synchronize_session=False)
        db.commit()
    return RedirectResponse(f"/admin/pages/{system_id}/{page_id}?saved=1", status_code=303)


@router.post("/{system_id}/{page_id}/restore/{rev_id}")
def page_restore(
    system_id: int, page_id: int, rev_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    page = db.query(Page).filter(Page.id == page_id, Page.system_id == system_id).first()
    rev  = db.query(PageRevision).filter(
        PageRevision.id == rev_id, PageRevision.page_id == page_id
    ).first()
    if page and rev:
        _save_revision(db, page, current_user.id)
        page.title   = rev.title
        page.content = rev.content
        db.commit()
    return RedirectResponse(f"/admin/pages/{system_id}/{page_id}?saved=1", status_code=303)


@router.post("/{system_id}/{page_id}/delete")
def page_delete(
    system_id: int, page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    page = db.query(Page).filter(Page.id == page_id, Page.system_id == system_id).first()
    if page:
        db.delete(page)
        db.commit()
    return RedirectResponse(f"/admin/pages/{system_id}/", status_code=303)


@router.post("/{system_id}/{page_id}/publish")
def page_toggle_publish(
    system_id: int, page_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    page = db.query(Page).filter(Page.id == page_id, Page.system_id == system_id).first()
    if page:
        page.is_published = not page.is_published
        db.commit()
    return RedirectResponse(f"/admin/pages/{system_id}/", status_code=303)
