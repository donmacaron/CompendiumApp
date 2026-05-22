from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from dependencies import get_db, require_admin
from models.user import User
from models.media import MediaFile
from models.system import System
from services.media import validate_upload, save_upload, delete_file

router = APIRouter(tags=["admin-media"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def media_list(
    request: Request,
    system_id: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    q = db.query(MediaFile)
    if system_id:
        q = q.filter(MediaFile.system_id == system_id)
    files = q.order_by(MediaFile.created_at.desc()).all()
    systems = db.query(System).filter(System.is_archived == False).all()

    return templates.TemplateResponse(
        request, "admin/media/list.html",
        {
            "files": files, "systems": systems,
            "selected_system": system_id,
            "current_user": current_user,
        }
    )


@router.post("/upload")
async def media_upload(
    system_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    content = await file.read()
    err = validate_upload(file.filename or "", file.content_type or "", len(content))
    if err:
        return JSONResponse({"error": err}, status_code=400)

    rel, url = save_upload(content, file.filename or "upload", system_id)

    mf = MediaFile(
        system_id=system_id,
        uploaded_by=current_user.id,
        filename=rel.split("/")[-1],
        original_name=file.filename or "",
        path=rel,
        url=url,
        mime_type=file.content_type or "",
        size_bytes=len(content),
    )
    db.add(mf)
    db.commit()
    db.refresh(mf)
    return JSONResponse({"url": url, "id": mf.id, "filename": mf.filename})


@router.post("/{media_id}/delete")
def media_delete(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    mf = db.query(MediaFile).filter(MediaFile.id == media_id).first()
    if mf:
        delete_file(mf.path)
        db.delete(mf)
        db.commit()
    return RedirectResponse("/admin/media/", status_code=303)
