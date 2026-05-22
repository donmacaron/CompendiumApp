from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from dependencies import get_db, require_admin
from models.user import User
from models.page import Page

router = APIRouter(prefix="/api/pages", tags=["api-pages"])


class PageOrderItem(BaseModel):
    id: int
    parent_id: Optional[int] = None
    sort_order: int


@router.post("/reorder")
def reorder_pages(
    items: list[PageOrderItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Bulk update sort_order and parent_id for a list of pages."""
    if not items:
        return JSONResponse({"status": "ok", "updated": 0})

    updated = 0
    for item in items:
        page = db.query(Page).filter(Page.id == item.id).first()
        if page:
            page.parent_id  = item.parent_id
            page.sort_order = item.sort_order
            updated += 1

    db.commit()
    return JSONResponse({"status": "ok", "updated": updated})
