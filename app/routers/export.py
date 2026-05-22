from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from dependencies import get_db
from config import settings
from models.system import System
from models.page import Page

router = APIRouter(tags=["export"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _xml_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _strip_html(html: str) -> str:
    """Crude HTML stripper — good enough for RSS descriptions."""
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()


def _html_to_md(html: str) -> str:
    """Convert basic HTML to Markdown without external deps."""
    import re
    h = html or ""
    # headings
    for i in range(6, 0, -1):
        h = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", lambda m, n=i: "#"*n + " " + m.group(1), h, flags=re.S)
    # bold / italic
    h = re.sub(r"<strong[^>]*>(.*?)</strong>", r"****", h, flags=re.S)
    h = re.sub(r"<b[^>]*>(.*?)</b>",           r"****", h, flags=re.S)
    h = re.sub(r"<em[^>]*>(.*?)</em>",          r"**",   h, flags=re.S)
    h = re.sub(r"<i[^>]*>(.*?)</i>",            r"**",   h, flags=re.S)
    # links
    h = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"[]()", h, flags=re.S)
    # images
    h = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>', r"![]()", h, flags=re.S)
    h = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*/?>', r"![]()", h, flags=re.S)
    # lists
    h = re.sub(r"<li[^>]*>(.*?)</li>", r"- ", h, flags=re.S)
    h = re.sub(r"<[uo]l[^>]*>", "", h)
    h = re.sub(r"</[uo]l>", "\n", h)
    # blockquote
    h = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>",
               lambda m: "\n".join("> " + l for l in m.group(1).splitlines()), h, flags=re.S)
    # code
    h = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"```\n\n```", h, flags=re.S)
    h = re.sub(r"<code[^>]*>(.*?)</code>", r"``", h, flags=re.S)
    # hr / br / p
    h = re.sub(r"<hr[^>]*/?>", "---", h)
    h = re.sub(r"<br[^>]*/?>", "  \n", h)
    h = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\n", h, flags=re.S)
    # strip remaining tags
    h = re.sub(r"<[^>]+>", "", h)
    # clean whitespace
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


# ── sitemap.xml ───────────────────────────────────────────────────────────────

@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    systems = db.query(System).filter(
        System.is_published == True, System.is_archived == False
    ).all()

    base = settings.SITE_URL.rstrip("/")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    # Homepage
    lines.append(f"""  <url>
    <loc>{base}/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>""")

    for system in systems:
        lines.append(f"""  <url>
    <loc>{base}/s/{system.slug}</loc>
    <lastmod>{system.updated_at.strftime('%Y-%m-%d')}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>""")

        pages = db.query(Page).filter(
            Page.system_id == system.id, Page.is_published == True
        ).all()

        for page in pages:
            lines.append(f"""  <url>
    <loc>{base}/s/{system.slug}/{page.slug}</loc>
    <lastmod>{page.updated_at.strftime('%Y-%m-%d')}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>""")

    lines.append("</urlset>")

    return Response(
        content="\n".join(lines),
        media_type="application/xml"
    )


# ── RSS per system ────────────────────────────────────────────────────────────

@router.get("/s/{system_slug}/rss.xml")
def system_rss(system_slug: str, db: Session = Depends(get_db)):
    system = db.query(System).filter(
        System.slug == system_slug,
        System.is_published == True,
        System.is_archived == False
    ).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")

    pages = db.query(Page).filter(
        Page.system_id == system.id,
        Page.is_published == True
    ).order_by(Page.updated_at.desc()).limit(20).all()

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = []
    for page in pages:
        pub = page.updated_at.strftime("%a, %d %b %Y %H:%M:%S +0000")
        desc = _xml_escape(_strip_html(page.content or "")[:300])
        items.append(f"""    <item>
      <title>{_xml_escape(page.title)}</title>
      <link>{base}/s/{system.slug}/{page.slug}</link>
      <description>{desc}</description>
      <pubDate>{pub}</pubDate>
      <guid>{base}/s/{system.slug}/{page.slug}</guid>
    </item>""")

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{_xml_escape(system.name)}</title>
    <link>{base}/s/{system.slug}</link>
    <description>{_xml_escape(system.description or system.name)}</description>
    <language>en</language>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>'''

    return Response(content=xml, media_type="application/rss+xml")


# ── Markdown export ───────────────────────────────────────────────────────────

@router.get("/s/{system_slug}/{page_slug}/export.md",
            response_class=PlainTextResponse)
def export_markdown(
    system_slug: str, page_slug: str,
    db: Session = Depends(get_db)
):
    system = db.query(System).filter(
        System.slug == system_slug,
        System.is_published == True,
        System.is_archived == False
    ).first()
    if not system:
        raise HTTPException(status_code=404)

    page = db.query(Page).filter(
        Page.system_id == system.id,
        Page.slug == page_slug,
        Page.is_published == True
    ).first()
    if not page:
        raise HTTPException(status_code=404)

    tags = f"\n**Tags:** {page.tags}" if page.tags else ""
    updated = page.updated_at.strftime("%Y-%m-%d")

    md = f"""# {page.title}

> System: {system.name}  
> Updated: {updated}{tags}

---

{_html_to_md(page.content or "")}
"""

    return PlainTextResponse(
        content=md,
        headers={
            "Content-Disposition": f'attachment; filename="{page.slug}.md"',
            "Content-Type": "text/markdown; charset=utf-8",
        }
    )
