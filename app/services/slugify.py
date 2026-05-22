from sqlalchemy.orm import Session
from sqlalchemy import and_


def make_slug(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    # lowercase and replace non-alphanumeric with hyphens
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80] or "page"


def unique_system_slug(text: str, db: Session, exclude_id: int = None) -> str:
    from models.system import System
    base = make_slug(text)
    slug = base
    counter = 1
    while True:
        q = db.query(System).filter(System.slug == slug)
        if exclude_id:
            q = q.filter(System.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def unique_page_slug(text: str, db: Session, system_id: int,
                     parent_id: int = None, exclude_id: int = None) -> str:
    from models.page import Page
    base = make_slug(text)
    slug = base
    counter = 1
    while True:
        q = db.query(Page).filter(
            Page.system_id == system_id,
            Page.parent_id == parent_id,
            Page.slug == slug
        )
        if exclude_id:
            q = q.filter(Page.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{base}-{counter}"
        counter += 1
