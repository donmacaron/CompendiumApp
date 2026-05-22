from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from dependencies import get_db
from services.search import search_pages

router = APIRouter(prefix="/api/search", tags=["api-search"])


@router.get("/", response_class=HTMLResponse)
def live_search(
    request: Request,
    q: str = Query(default=""),
    db: Session = Depends(get_db)
):
    """HTMX endpoint — returns result rows HTML only."""
    if not q or len(q.strip()) < 2:
        return HTMLResponse("")

    results = search_pages(q.strip(), db, limit=8)

    if not results:
        return HTMLResponse(
            '<p style="padding:12px 16px;color:#7a5c3a;font-size:0.9em">No results found.</p>'
        )

    rows = []
    for r in results:
        page = r["page"]
        system = r["system"]
        rows.append(f'''
<a href="/s/{system.slug}/{page.slug}" class="search-result-item"
   onclick="closeSearch()">
  <div class="search-result-title">{page.title}</div>
  <div class="search-result-meta">{system.name}</div>
  <div class="search-result-snippet">{r["snippet"]}</div>
</a>''')

    return HTMLResponse("\n".join(rows))
