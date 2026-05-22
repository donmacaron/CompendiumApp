from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from dependencies import get_db, get_current_user
from models.user import User, Role
from services.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, current_user: User | None = Depends(get_current_user)):
    if current_user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {})


@router.post("/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "Invalid username or password"}
        )
    if not user.is_active:
        return templates.TemplateResponse(
            request, "auth/login.html",
            {"error": "This account has been suspended."}
        )
    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token", token,
        httponly=True, max_age=60 * 60 * 24 * 7, samesite="lax"
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, current_user: User | None = Depends(get_current_user)):
    if current_user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/register.html", {})


@router.post("/register")
@limiter.limit("5/minute")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"error": "Passwords do not match"}
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"error": "Password must be at least 6 characters"}
        )
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"error": "Username already taken"}
        )
    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse(
            request, "auth/register.html",
            {"error": "Email already registered"}
        )
    user = User(
        username=username, email=email,
        hashed_password=hash_password(password),
        role=Role.user
    )
    db.add(user)
    db.commit()
    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token", token,
        httponly=True, max_age=60 * 60 * 24 * 7, samesite="lax"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response
