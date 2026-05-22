from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from models.page import Page
from models.system import System
import re


def highlight(text: str, query: str, max_len: int = 160) -> str:
    """Extract a snippet around the first match and wrap it in <mark>."""
    if not text or not query:
        return (text or "")[:max_len]

    q_lower = query.lower()
    t_lower = text.lower()
    pos = t_lower.find(q_lower)

    if pos == -1:
        return text[:max_len]

    start = max(0, pos - 60)
    end = min(len(text), pos + len(query) + 100)
    snippet = ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")

    # Wrap match in <mark> — case-insensitive replace
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    snippet = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", snippet)
    return snippet


def search_pages(
    query: str,
    db: Session,
    system_slug: str = "",
    limit: int = 20
) -> list[dict]:
    if not query or len(query.strip()) < 2:
        return []

    q = query.strip()

    base = db.query(Page, System).join(
        System, Page.system_id == System.id
    ).filter(
        Page.is_published == True,
        System.is_published == True,
        System.is_archived == False,
        or_(
            func.lower(Page.title).contains(func.lower(q)),
            func.lower(Page.content).contains(func.lower(q)),
            func.lower(Page.tags).contains(func.lower(q)),
        )
    )

    if system_slug:
        base = base.filter(System.slug == system_slug)

    rows = base.order_by(
        Page.view_count.desc()
    ).limit(limit).all()

    results = []
    for page, system in rows:
        # Title match scores higher in snippet
        in_title = q.lower() in (page.title or "").lower()
        snippet_source = page.content or page.tags or ""
        results.append({
            "page": page,
            "system": system,
            "snippet": highlight(snippet_source, q),
            "in_title": in_title,
        })

    # Re-sort: title matches first
    results.sort(key=lambda x: (not x["in_title"], -x["page"].view_count))
    return results
