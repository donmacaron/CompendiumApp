from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from dependencies import get_db, require_admin
from models.user import User
from models.media import MediaFile
from services.media import validate_upload, save_upload

router = APIRouter(prefix="/api/media", tags=["api-media"])


@router.get("/picker", response_class=HTMLResponse)
def media_picker_grid(
    system_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Returns image grid HTML for the in-editor media picker modal."""
    files = db.query(MediaFile).filter(
        MediaFile.system_id == system_id
    ).order_by(MediaFile.created_at.desc()).all()

    if not files:
        return HTMLResponse(
            '<p style="padding:20px;color:#7a5c3a;text-align:center;font-size:0.9em">' +
            'No images uploaded yet for this system.<br>' +
            'Use the Upload tab to add images.' +
            '</p>'
        )

    rows = []
    for f in files:
        rows.append(f'''
<div class="picker-thumb" onclick="insertMediaUrl(\'{f.url}\', \'{f.original_name}\')"
     title="{f.original_name}">
  <img src="{f.url}" alt="{f.original_name}"
       onerror="this.parentElement.style.display='none'">
  <div class="picker-thumb-name">{f.original_name[:22]}</div>
</div>''')

    return HTMLResponse('\n'.join(rows))


@router.post("/upload-inline")
async def media_upload_inline(
    system_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Upload from inside the editor — returns JSON with url."""
    content = await file.read()
    err = validate_upload(file.filename or "", file.content_type or "", len(content))
    if err:
        return JSONResponse({"error": err}, status_code=400)

    rel, url = save_upload(content, file.filename or "upload", system_id)

    from models.media import MediaFile
    mf = MediaFile(
        system_id=system_id,
        uploaded_by=current_user.id,
        filename=rel.split("/")[-1],
        original_name=file.filename or "",
        path=rel, url=url,
        mime_type=file.content_type or "",
        size_bytes=len(content),
    )
    db.add(mf)
    db.commit()
    db.refresh(mf)
    return JSONResponse({"url": url, "filename": mf.original_name, "id": mf.id})
