import os
from fastapi import APIRouter, HTTPException, Response, status
from loguru import logger
from app.services.storage import get_s3_object_data

router = APIRouter(prefix="/storage", tags=["storage"])

@router.get("/{s3_key:path}", summary="Stream storage asset or proxy image")
async def get_storage_asset(s3_key: str):
    """
    Public storage proxy endpoint.
    Streams images and documents directly from MinIO or fallback local storage.
    Enables client browsers to access assets in production/CIS without requiring direct port 9000 access.
    """
    clean_key = s3_key.lstrip("/")
    
    # 1. Try fetching from MinIO Object Storage
    try:
        content, ctype = get_s3_object_data(clean_key)
        if content:
            return Response(
                content=content,
                media_type=ctype or "image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Content-Disposition": "inline"
                }
            )
    except Exception as err:
        logger.warning(f"Storage proxy fetch error from S3 for '{clean_key}': {err}")

    # 2. Fallback: Check local disk storage (data/temp, data/uploads)
    fname = os.path.basename(clean_key)
    for folder in ["data/temp", "data/uploads"]:
        local_path = os.path.join(folder, fname)
        if os.path.exists(local_path) and os.path.isfile(local_path):
            try:
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
                ext = os.path.splitext(fname)[1].lower()
                mime_map = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                    ".pdf": "application/pdf"
                }
                media_type = mime_map.get(ext, "application/octet-stream")
                return Response(
                    content=file_bytes,
                    media_type=media_type,
                    headers={
                        "Cache-Control": "public, max-age=86400",
                        "Content-Disposition": "inline"
                    }
                )
            except Exception:
                pass

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Storage asset '{clean_key}' not found.")
