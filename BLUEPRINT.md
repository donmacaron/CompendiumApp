# COMPENDIUM — Full Build Blueprint
> Stack: FastAPI + Jinja2 + PostgreSQL + SQLAlchemy + Alembic + TipTap + HTMX + Alpine.js + Nginx + Docker Compose  
> Folder: `C:\Users\Don Macaron\Documents\_coding\Compendium`

---

## ⚠️ CRITICAL RULES FOR THE MODEL

1. **TemplateResponse syntax** — Starlette 0.40+:
   ```python
   # CORRECT
   return templates.TemplateResponse(request, "template.html", {"key": value})
   # WRONG — breaks with Starlette 0.40+
   return templates.TemplateResponse("template.html", {"request": request})
   ```

2. **All `open()` calls** must include `encoding="utf-8"`

3. **All file paths** use `pathlib.Path`, never string concatenation

4. **Every router** must import and use `get_current_user` dependency for protected routes

---

## PROJECT FOLDER STRUCTURE

```
Compendium/
├── docker-compose.yml
├── .env.example
├── .env
├── .gitignore
├── README.md
│
├── nginx/
│   └── nginx.conf
│
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── system.py
│   │   ├── page.py
│   │   ├── media.py
│   │   ├── revision.py
│   │   └── favorite.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── public.py
│   │   ├── admin/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py
│   │   │   ├── systems.py
│   │   │   ├── pages.py
│   │   │   ├── media.py
│   │   │   └── users.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── pages.py
│   │       ├── media.py
│   │       ├── search.py
│   │       └── favorites.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── page_tree.py
│   │   ├── slugify.py
│   │   ├── search.py
│   │   └── media.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── partials/
│   │   │   ├── nav.html
│   │   │   ├── sidebar_tree.html
│   │   │   ├── breadcrumb.html
│   │   │   ├── toc.html
│   │   │   └── flash.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   └── reset_password.html
│   │   ├── public/
│   │   │   ├── home.html
│   │   │   ├── system_home.html
│   │   │   └── page.html
│   │   └── admin/
│   │       ├── base_admin.html
│   │       ├── dashboard.html
│   │       ├── systems/
│   │       │   ├── list.html
│   │       │   ├── create.html
│   │       │   └── edit.html
│   │       ├── pages/
│   │       │   ├── list.html
│   │       │   └── edit.html
│   │       ├── media/
│   │       │   └── list.html
│   │       └── users/
│   │           └── list.html
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── base.css
│   │   │   ├── admin.css
│   │   │   ├── editor.css
│   │   │   └── themes/
│   │   │       ├── low-fantasy.css
│   │   │       ├── eldritch-tome.css
│   │   │       ├── tech-manual.css
│   │   │       ├── old-web-forum.css
│   │   │       ├── sci-fi-terminal.css
│   │   │       └── fantasy-wiki.css
│   │   ├── js/
│   │   │   ├── editor.js
│   │   │   ├── page_tree.js
│   │   │   ├── search.js
│   │   │   └── theme_preview.js
│   │   ├── img/
│   │   │   └── textures/
│   │   └── fonts/
│   │
│   └── migrations/
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│
└── data/
    ├── media/
    └── db/
```

---

## .env.example

```env
# Database
POSTGRES_USER=compendium
POSTGRES_PASSWORD=changeme
POSTGRES_DB=compendium
DATABASE_URL=postgresql://compendium:changeme@db:5432/compendium

# App
SECRET_KEY=change-this-to-a-random-64-char-string
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1

# Media
MEDIA_PATH=/app/data/media
MAX_UPLOAD_MB=10

# Email (optional for password reset)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@compendium.local
```

---

## docker-compose.yml

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - ./data/db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: ./app
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file: .env
    volumes:
      - ./data/media:/app/data/media
      - ./app:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    depends_on:
      - app
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./app/static:/static:ro
      - ./data/media:/media:ro
```

---

## nginx/nginx.conf

```nginx
events { worker_connections 1024; }

http {
  include       mime.types;
  default_type  application/octet-stream;
  sendfile      on;
  gzip          on;

  server {
    listen 80;

    location /static/ {
      alias /static/;
      expires 7d;
      add_header Cache-Control "public, immutable";
    }

    location /media/ {
      alias /media/;
      expires 7d;
    }

    location / {
      proxy_pass         http://app:8000;
      proxy_set_header   Host $host;
      proxy_set_header   X-Real-IP $remote_addr;
      proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    }
  }
}
```

---

## app/requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
jinja2==3.1.4
aiofiles==23.2.1
pillow==10.3.0
python-slugify==8.0.4
itsdangerous==2.2.0
httpx==0.27.0
pydantic-settings==2.2.1
```

---

## app/Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## DATABASE MODELS

### app/models/user.py
```python
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Role(str, enum.Enum):
    user = "user"
    editor = "editor"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_path = Column(String(500), nullable=True)
    role = Column(Enum(Role), default=Role.user, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete")
```

### app/models/system.py
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class System(Base):
    __tablename__ = "systems"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    abbreviation = Column(String(20), nullable=True)
    banner_path = Column(String(500), nullable=True)
    logo_path = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    theme = Column(JSON, nullable=True, default=dict)
    # theme example: {"preset": "low-fantasy", "bg_color": "#f5e9c8",
    # "text_color": "#2c1a0e", "accent_color": "#8b2e2e",
    # "font_body": "IM Fell English", "font_heading": "Cinzel", "custom_css": ""}

    pages = relationship("Page", back_populates="system", cascade="all, delete")
```

### app/models/page.py
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("pages.id"), nullable=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=True)       # TipTap HTML output
    content_json = Column(JSON, nullable=True)  # TipTap JSON
    summary = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)   # comma-separated
    is_published = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    system = relationship("System", back_populates="pages")
    parent = relationship("Page", remote_side=[id], back_populates="children")
    children = relationship("Page", back_populates="parent",
                            order_by="Page.sort_order", cascade="all, delete")
    revisions = relationship("PageRevision", back_populates="page", cascade="all, delete")
    favorites = relationship("UserFavorite", back_populates="page", cascade="all, delete")
```

### app/models/revision.py
```python
from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base

class PageRevision(Base):
    __tablename__ = "page_revisions"

    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    page = relationship("Page", back_populates="revisions")
    user = relationship("User")
```

### app/models/media.py
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger
from app.database import Base

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    url = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size_bytes = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### app/models/favorite.py
```python
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class UserFavorite(Base):
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    page = relationship("Page", back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "page_id"),)
```

---

## DEVELOPMENT PHASES

---

## PHASE 1 — Foundation (Infrastructure + Auth)
**Goal:** App boots in Docker, DB migrates, admin can log in.

### Step 1.1 — Create folder structure
Create all directories and empty `__init__.py` files as shown above.

### Step 1.2 — Write `app/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

### Step 1.3 — Write `app/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = False
    MEDIA_PATH: str = "/app/data/media"
    MAX_UPLOAD_MB: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
```

### Step 1.4 — Write all models
Import all in `app/models/__init__.py`.

### Step 1.5 — Initialize Alembic
```bash
cd app
alembic init migrations
```
Edit `migrations/env.py`: import Base + all models, set `target_metadata = Base.metadata`.

### Step 1.6 — Write `app/services/auth.py`
- `hash_password(password)` using passlib bcrypt
- `verify_password(plain, hashed)`
- `create_access_token(data, expires_minutes=60*24*7)` using python-jose
- `decode_token(token) -> dict | None`

### Step 1.7 — Write `app/dependencies.py`
```python
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, Role
from app.services.auth import decode_token

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("sub")).first()

def require_user(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return user

def require_admin(user = Depends(require_user)):
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
```

### Step 1.8 — Write `app/routers/auth.py`
- GET /auth/login -> render login form
- POST /auth/login -> verify, set httponly cookie, redirect to /
- GET /auth/register -> render register form
- POST /auth/register -> create user, set cookie, redirect to /
- GET /auth/logout -> delete cookie, redirect to /

### Step 1.9 — Write `app/main.py`
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import auth, public
from app.routers.admin import dashboard, systems, pages, media, users

app = FastAPI(title="Compendium")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="/app/data/media"), name="media")
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(dashboard.router, prefix="/admin")
app.include_router(systems.router, prefix="/admin/systems")
app.include_router(pages.router, prefix="/admin/pages")
app.include_router(media.router, prefix="/admin/media")
app.include_router(users.router, prefix="/admin/users")
```

### Step 1.10 — First Alembic migration
```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### Step 1.11 — Create first admin user
```python
# app/create_admin.py — run once: python create_admin.py
from app.database import SessionLocal
from app.models.user import User, Role
from app.services.auth import hash_password

db = SessionLocal()
admin = User(username="admin", email="admin@local.dev",
             hashed_password=hash_password("admin"), role=Role.admin)
db.add(admin)
db.commit()
print("Admin created: admin / admin")
```

### Step 1.12 — Verify Phase 1
- `docker compose up --build`
- Navigate to http://localhost/auth/login
- Login with admin / admin

---

## PHASE 2 — Admin: Systems CRUD + Theming
**Goal:** Admin can create systems and configure their visual theme.

### Step 2.1 — Base templates
- `base.html`: loads theme CSS dynamically from `system.theme.preset`
- Injects `system.theme.custom_css` in a `<style>` tag if present
- `admin/base_admin.html`: extends base, no system theme, left sidebar nav

### Step 2.2 — `app/services/slugify.py`
```python
from python_slugify import slugify as _slugify

def make_slug(text: str) -> str:
    return _slugify(text, max_length=80, word_boundary=True)

def unique_slug(text, model_class, db, exclude_id=None) -> str:
    base = make_slug(text)
    slug = base
    counter = 1
    while db.query(model_class).filter(
        model_class.slug == slug,
        model_class.id != exclude_id if exclude_id else True
    ).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
```

### Step 2.3 — `app/routers/admin/systems.py`
- GET /admin/systems/ -> list
- GET /admin/systems/create -> form
- POST /admin/systems/create -> create + slug + redirect to edit
- GET /admin/systems/{id}/edit -> edit + theme editor section
- POST /admin/systems/{id}/edit -> update system + theme JSON
- POST /admin/systems/{id}/delete -> set is_archived=True
- POST /admin/systems/{id}/publish -> toggle is_published

### Step 2.4 — Theme editor UI
In system edit template, add "Theme" section:
- Dropdown: Preset (low-fantasy, eldritch-tome, tech-manual, old-web-forum, sci-fi-terminal, fantasy-wiki)
- Color pickers: Background, Text, Accent (`<input type="color">`)
- Font dropdowns: Body font, Heading font
- Textarea: Custom CSS
- Live Preview: opens /s/{slug} in new tab

### Step 2.5 — Theme CSS files
`low-fantasy.css` (default):
```css
:root {
  --bg: #f5e9c8;
  --bg-alt: #ede0b0;
  --text: #2c1a0e;
  --text-muted: #7a5c3a;
  --accent: #8b2e2e;
  --border: #c4a96b;
  --font-body: 'IM Fell English', Georgia, serif;
  --font-heading: 'Cinzel', 'Times New Roman', serif;
}
body { background-color: var(--bg); color: var(--text); font-family: var(--font-body); }
h1, h2, h3, h4 { font-family: var(--font-heading); color: var(--accent); text-wrap: balance; }
```
Create the other 5 theme files with matching palettes.

---

## PHASE 3 — Admin: Pages + TipTap Editor
**Goal:** Admin can create, edit, and organize pages within a system.

### Step 3.1 — `app/services/page_tree.py`
```python
def build_tree(pages) -> list[dict]:
    by_id = {p.id: {"page": p, "children": []} for p in pages}
    roots = []
    for item in by_id.values():
        pid = item["page"].parent_id
        if pid and pid in by_id:
            by_id[pid]["children"].append(item)
        else:
            roots.append(item)
    return roots
```

### Step 3.2 — `app/routers/admin/pages.py`
- GET /admin/pages/{system_id}/ -> tree list
- GET /admin/pages/{system_id}/create?parent_id=X -> form
- POST /admin/pages/{system_id}/create -> create page, save revision
- GET /admin/pages/{system_id}/{page_id}/edit -> TipTap editor
- POST /admin/pages/{system_id}/{page_id}/edit -> save + new revision
- DELETE /admin/pages/{system_id}/{page_id} -> delete (HTMX)
- POST /admin/pages/reorder -> bulk update sort_order + parent_id
- GET /admin/pages/{system_id}/{page_id}/revisions -> list
- POST /admin/pages/{system_id}/{page_id}/revisions/{rev_id}/restore

### Step 3.3 — TipTap editor (`static/js/editor.js`)
Load TipTap from CDN. Init with extensions: StarterKit, Image, Link, Table, TableRow,
TableHeader, TableCell, Highlight, Underline. On update: sync HTML to hidden `<input id="content-input">`.
Toolbar buttons wired to editor commands.

### Step 3.4 — Image upload in editor
- Toolbar button -> file picker -> POST /api/media/upload
- Response: {"url": "/media/system_id/filename.jpg"}
- Insert into editor: editor.chain().focus().setImage({src: url}).run()

### Step 3.5 — Page tree drag-and-drop
Use SortableJS from CDN. On sort end: POST /admin/pages/reorder with [{id, sort_order, parent_id}].

### Step 3.6 — Recursive sidebar macro
```html
{# templates/partials/sidebar_tree.html #}
{% macro render_tree(nodes, current_page_id, system_slug) %}
  <ul>
    {% for node in nodes %}
    <li class="{% if node.page.id == current_page_id %}active{% endif %}">
      <a href="/s/{{ system_slug }}/{{ node.page.slug }}">{{ node.page.title }}</a>
      {% if node.children %}{{ render_tree(node.children, current_page_id, system_slug) }}{% endif %}
    </li>
    {% endfor %}
  </ul>
{% endmacro %}
```

---

## PHASE 4 — Public Frontend
**Goal:** Users can browse systems and read pages.

### Step 4.1 — `app/routers/public.py`
- GET / -> list published systems
- GET /s/{system_slug} -> system home
- GET /s/{system_slug}/{page_slug} -> page view:
  1. Load system + verify published
  2. Load page by slug
  3. Increment view_count
  4. Load all pages for sidebar tree
  5. Build breadcrumb (walk parent chain)
  6. Extract ToC from HTML (parse h2/h3 tags)
  7. Render page.html

### Step 4.2 — Templates
- `public/home.html`: grid of system cards (banner, name, description)
- `public/system_home.html`: full-width banner + top-level page list
- `public/page.html`: two-column layout (sidebar tree + content area)
  - Content: breadcrumb, h1, ToC, article body, tags, view count, last updated
  - Bottom: prev/next sibling page navigation

### Step 4.3 — Apply system theme in base.html
```html
{% if system %}
  <link rel="stylesheet" href="/static/css/themes/{{ system.theme.get('preset', 'low-fantasy') }}.css">
  {% if system.theme.get('custom_css') %}
  <style>{{ system.theme.custom_css | safe }}</style>
  {% endif %}
{% else %}
  <link rel="stylesheet" href="/static/css/themes/low-fantasy.css">
{% endif %}
```

---

## PHASE 5 — User System
**Goal:** Registration, login, favorites, reading history.

### Step 5.1 — Auth templates
Login + register forms with Alpine.js client validation.

### Step 5.2 — Nav bar with user state
Show username/logout if logged in, show login/register if not.

### Step 5.3 — Favorites API
- POST /api/favorites/add -> create UserFavorite
- POST /api/favorites/remove -> delete UserFavorite
- GET /api/favorites/check/{page_id} -> {is_favorite: bool}
Favorite button on page view uses HTMX hx-post + hx-swap.

### Step 5.4 — User favorites page
GET /user/favorites -> all favorited pages grouped by system.

### Step 5.5 — Reading history
Store last 20 page IDs in signed cookie. Show on user profile.

### Step 5.6 — User profile
GET /user/profile -> avatar, username, bio, joined date, recent favorites, history.

---

## PHASE 6 — Search
**Goal:** Full-text search across all content.

### Step 6.1 — PostgreSQL full-text search
```python
from sqlalchemy import or_

def search_pages(query, db, system_id=None, limit=20):
    q = db.query(Page).join(System).filter(
        Page.is_published == True,
        System.is_published == True,
        or_(
            Page.title.ilike(f"%{query}%"),
            Page.content.ilike(f"%{query}%"),
            Page.tags.ilike(f"%{query}%")
        )
    )
    if system_id:
        q = q.filter(Page.system_id == system_id)
    return q.order_by(Page.view_count.desc()).limit(limit).all()
```

### Step 6.2 — Search route
GET /search?q=goblin&system=dnd5e -> results page with highlighted snippets.

### Step 6.3 — Live search (Ctrl+K)
Modal triggered by Ctrl+K. Input wired with HTMX hx-get="/api/search" debounced 300ms.

---

## PHASE 7 — Admin Polish

### Step 7.1 — Media manager
GET /admin/media/ -> grid of all uploads, filterable by system, delete button.

### Step 7.2 — Revision history
List with date/editor/snippet. Restore button copies revision content back to page.

### Step 7.3 — User management
Table with role change dropdown (HTMX inline) and ban/unban toggle.

### Step 7.4 — Admin dashboard stats
Total systems, pages, users, recent edits, recent registrations.

---

## PHASE 8 — Export + SEO

### Step 8.1 — Sitemap: GET /sitemap.xml
### Step 8.2 — RSS per system: GET /s/{slug}/rss.xml
### Step 8.3 — Export page as Markdown: GET /s/{slug}/{page_slug}/export.md
### Step 8.4 — Print CSS: @media print in base.css (hide sidebar/nav, full-width content)

---

## PHASE 9 — Production Hardening

### Step 9.1 — Security headers in Nginx
```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

### Step 9.2 — Rate limiting with slowapi
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, ...):
    ...
```

### Step 9.3 — File upload validation
- Check content_type starts with image/
- Check size <= MAX_UPLOAD_MB
- Strip EXIF with Pillow before saving

### Step 9.4 — Auto-migrate on startup
```python
from alembic.config import Config
from alembic import command

@app.on_event("startup")
def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

---

## BUILD ORDER SUMMARY

| Phase | What Gets Built | Test By |
|---|---|---|
| 1 | Docker, DB, Auth | Login as admin at /auth/login |
| 2 | Systems CRUD + Themes | Create system, set theme |
| 3 | Pages + TipTap Editor | Create nested pages, insert image + table |
| 4 | Public Frontend | Browse as anonymous user |
| 5 | User Features | Register, login, favorite a page |
| 6 | Search | Search "goblin", get results |
| 7 | Admin Polish | View revisions, manage users |
| 8 | Export + SEO | /sitemap.xml returns XML |
| 9 | Production | No DEBUG errors, rate limits work |

---

## NOTES FOR THE LOCAL MODEL

- Always use `TemplateResponse(request, "template.html", {...})` NOT the old dict-with-request style
- Router files return `RedirectResponse` with `status_code=303` after POST (PRG pattern)
- All admin routes must call `require_admin` dependency
- Page slugs are scoped: unique within `(system_id, parent_id)` — enforce in service layer
- TipTap content stored as raw HTML in `page.content` — render with `{{ page.content | safe }}`
- The `sidebar_tree` macro must handle unlimited depth via recursion
- Media files live in `MEDIA_PATH/{system_id}/{filename}` — Nginx serves them directly
- Never store JWT in localStorage — httponly cookie only
