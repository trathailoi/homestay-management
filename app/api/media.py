"""Media (image/video) upload API endpoints.

Cookie-authenticated; admin and receptionist may upload/list/delete. Files are
stored on the filesystem (see MediaService); there is no database record.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.deps import require_user
from app.models import User
from app.schemas.common import ListResponse, Meta, SuccessResponse
from app.services.media_service import MediaService

router = APIRouter(prefix="/media", tags=["media"])


@router.get("")
async def list_media(
    scope: str,
    room_number: str | None = None,
    _user: User = Depends(require_user),
) -> ListResponse[dict]:
    """List media for a scope (hero | gallery | room)."""
    items = MediaService().list_media(scope, room_number)
    return ListResponse(data=items, meta=Meta(total=len(items), page=1, per_page=100))


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_media(
    scope: str = Form(...),
    room_number: str | None = Form(None),
    file: UploadFile = File(...),
    _user: User = Depends(require_user),
) -> SuccessResponse[dict]:
    """Upload one image or video file to a scope."""
    data = await file.read()
    item = MediaService().save(scope, room_number, file.filename or "", data, file.content_type)
    return SuccessResponse(data=item)


@router.delete("")
async def delete_media(
    scope: str,
    filename: str,
    room_number: str | None = None,
    _user: User = Depends(require_user),
) -> SuccessResponse[dict]:
    """Delete one media file from a scope."""
    MediaService().delete(scope, room_number, filename)
    return SuccessResponse(data={"deleted": filename})
