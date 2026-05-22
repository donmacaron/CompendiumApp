from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import re

from dependencies import get_db, require_admin
from models.user import User
from models.system import System
from models.page import Page
from services.page_tree import build_tree
from services.slugify import unique_system_slug

router = APIRouter(tags=["admin-systems"])
templates = Jinja2Templates(directory="templates")

THEME_PRESETS = [
    "low-fantasy", "eldritch-tome", "tech-manual",
    "old-web-forum", "sci-fi-terminal", "fantasy-wiki",
]

FONT_OPTIONS = [
    "IM Fell English", "Cinzel", "Crimson Text", "Lora",
    "Georgia", "Times New Roman", "Courier New",
    "VT323", "Share Tech Mono", "Arial",
]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")


@router.get("/", response_class=HTMLResponse)
def systems_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    systems = db.query(System).filter(
        System.is_archived == False
    ).order_by(System.name).all()
    return templates.TemplateResponse(
        request, "admin/systems/list.html",
        {"systems": systems, "current_user": current_user}
    )


@router.get("/create", response_class=HTMLResponse)
def systems_create_form(
    request: Request,
    current_user: User = Depends(require_admin)
):
    return templates.TemplateResponse(
        request, "admin/systems/create.html",
        {"current_user": current_user, "presets": THEME_PRESETS}
    )


@router.post("/create")
def systems_create(
    name: str = Form(...),
    description: str = Form(""),
    abbreviation: str = Form(""),
    theme_preset: str = Form("low-fantasy"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    slug = unique_system_slug(name, db)
    system = System(
        name=name.strip(), slug=slug,
        description=description.strip() or None,
        abbreviation=abbreviation.strip() or None,
        theme={"preset": theme_preset, "custom_css": ""},
        translatable=False,
    )
    db.add(system)
    db.commit()
    db.refresh(system)
    return RedirectResponse(f"/admin/systems/{system.id}/edit", status_code=303)


@router.get("/{system_id}/edit", response_class=HTMLResponse)
def systems_edit_form(
    request: Request, system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        return RedirectResponse("/admin/systems/", status_code=303)

    # Load full page tree for Structure tab
    all_pages = db.query(Page).filter(
        Page.system_id == system_id
    ).order_by(Page.sort_order, Page.title).all()
    pages_tree = build_tree(all_pages)

    return templates.TemplateResponse(
        request, "admin/systems/edit.html",
        {
            "system": system,
            "current_user": current_user,
            "presets": THEME_PRESETS,
            "fonts": FONT_OPTIONS,
            "pages_tree": pages_tree,
        }
    )


@router.post("/{system_id}/edit")
def systems_edit(
    system_id: int,
    name: str = Form(...),
    description: str = Form(""),
    abbreviation: str = Form(""),
    translatable: Optional[str] = Form(None),
    theme_preset: str = Form("low-fantasy"),
    theme_bg_color: str = Form("#f5e9c8"),
    theme_text_color: str = Form("#2c1a0e"),
    theme_accent_color: str = Form("#8b2e2e"),
    theme_font_body: str = Form("IM Fell English"),
    theme_font_heading: str = Form("Cinzel"),
    theme_custom_css: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        return RedirectResponse("/admin/systems/", status_code=303)

    system.name = name.strip()
    system.description = description.strip() or None
    system.abbreviation = abbreviation.strip() or None
    system.translatable = (translatable == "on")

    if _slug(name) != system.slug:
        system.slug = unique_system_slug(name, db, exclude_id=system_id)

    system.theme = {
        "preset": theme_preset,
        "bg_color": theme_bg_color,
        "text_color": theme_text_color,
        "accent_color": theme_accent_color,
        "font_body": theme_font_body,
        "font_heading": theme_font_heading,
        "custom_css": theme_custom_css.strip(),
    }
    db.commit()
    return RedirectResponse(f"/admin/systems/{system_id}/edit?saved=1", status_code=303)


@router.post("/{system_id}/publish")
def systems_toggle_publish(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = db.query(System).filter(System.id == system_id).first()
    if system:
        system.is_published = not system.is_published
        db.commit()
    return RedirectResponse("/admin/systems/", status_code=303)


@router.post("/{system_id}/delete")
def systems_delete(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    system = db.query(System).filter(System.id == system_id).first()
    if system:
        system.is_archived = True
        db.commit()
    return RedirectResponse("/admin/systems/", status_code=303)
