from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from routers import auth, public, search, export
from routers import user as user_router
from routers.admin import dashboard
from routers.admin import systems as admin_systems
from routers.admin import pages   as admin_pages
from routers.admin import users   as admin_users
from routers.admin import media   as admin_media
from routers.api   import favorites as api_favorites
from routers.api   import search    as api_search
from routers.api   import media     as api_media
from routers.api   import pages     as api_pages

limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]          = "SAMEORIGIN"
        response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"]         = "1; mode=block"
        response.headers["Permissions-Policy"]       = "geolocation=(), microphone=(), camera=()"
        return response

app = FastAPI(title="Compendium", docs_url=None, redoc_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
media_path = Path("/app/data/media")
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")

@app.on_event("startup")
def run_migrations():
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("✅ Alembic migrations: up to date")
    except Exception as e:
        print(f"⚠️  Migration warning: {e}")

app.include_router(auth.router)
app.include_router(public.router)
app.include_router(search.router)
app.include_router(export.router)
app.include_router(user_router.router)
app.include_router(api_favorites.router)
app.include_router(api_search.router)
app.include_router(api_media.router)
app.include_router(api_pages.router)
app.include_router(dashboard.router,      prefix="/admin")
app.include_router(admin_systems.router,  prefix="/admin/systems")
app.include_router(admin_pages.router,    prefix="/admin/pages")
app.include_router(admin_users.router,    prefix="/admin/users")
app.include_router(admin_media.router,    prefix="/admin/media")
