from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import List
import aiofiles
import os
import mimetypes
import logging
from celery import Celery
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from services.backblaze_service import (
    upload_file_to_b2,
    list_files_in_b2,
    get_file_download_url,
    delete_file_from_b2,
    rename_file_in_b2,
    move_file_to_folder
)

drive_router = APIRouter()
logger = logging.getLogger("DriveAPI")
TEMP_DIR = "/tmp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Celery setup
celery_app = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

@celery_app.task
def async_upload_task(temp_path, final_key):
    return upload_file_to_b2(temp_path, final_key)

# Limiter
limiter = Limiter(key_func=get_remote_address)

# === ROUTES ===

@drive_router.post("/upload")
@limiter.limit("20/minute")
async def upload(request: Request, files: List[UploadFile] = File(...), folder: str = Form("")):
    results = []
    for file in files:
        try:
            filename = file.filename.strip()
            if not filename:
                results.append({"filename": None, "result": "❌ Empty filename skipped"})
                continue

            safe_filename = os.path.basename(filename)
            final_key = os.path.join(folder, safe_filename) if folder else safe_filename
            temp_path = os.path.join(TEMP_DIR, safe_filename)

            async with aiofiles.open(temp_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)

            async_upload_task.delay(temp_path, final_key)

            logger.info(f"📨 Queued for upload: {final_key}")
            results.append({
                "original": filename,
                "filename": final_key,
                "display_name": filename,
                "result": "⏳ Upload queued"
            })
        except Exception as e:
            logger.error(f"❌ Upload error [{file.filename}]: {e}")
            results.append({"filename": file.filename, "result": f"❌ Upload failed: {str(e)}"})

    return JSONResponse(status_code=207 if any(r["result"].startswith("❌") for r in results) else 200, content=results)

@drive_router.get("/files")
async def list_files():
    try:
        raw_files = list_files_in_b2()
        result = []

        for obj in raw_files:
            key = obj.get("filename") or obj.get("Key")
            size = obj.get("size") or obj.get("Size", 0)
            if not key or key.endswith("/"):
                continue

            mime_type, _ = mimetypes.guess_type(key)
            file_type = mime_type.split("/")[0] if mime_type else "file"
            download_url = get_file_download_url(key)
            if not download_url or isinstance(download_url, dict):
                continue

            result.append({
                "filename": key,
                "name": key,
                "display_name": os.path.basename(key),
                "type": file_type,
                "size": size,
                "download_url": download_url
            })
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"❌ Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@drive_router.get("/download/{filename}")
async def download_file(filename: str):
    try:
        safe_filename = os.path.basename(filename)
        url = get_file_download_url(safe_filename)
        if not url or isinstance(url, dict):
            raise HTTPException(status_code=404, detail=f"{filename} not found")
        return {"download_url": url}
    except Exception as e:
        logger.error(f"❌ Download URL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@drive_router.delete("/{filename}")
async def delete_file(filename: str):
    try:
        safe_filename = os.path.basename(filename)
        result = delete_file_from_b2(safe_filename)
        if result.startswith("✅"):
            logger.info(f"✅ Deleted from B2: {filename}")
            return {"filename": filename, "result": result}
        else:
            raise HTTPException(status_code=404, detail=result)
    except Exception as e:
        logger.error(f"❌ Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@drive_router.post("/rename")
async def rename_file(payload: dict):
    old_name = payload.get("old_name")
    new_name = payload.get("new_name")
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="Both 'old_name' and 'new_name' are required")
    try:
        result = rename_file_in_b2(old_name, new_name)
        logger.info(f"✅ Renamed: {old_name} → {new_name}")
        return {"result": result}
    except Exception as e:
        logger.error(f"❌ Rename error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@drive_router.post("/move")
async def move_file(payload: dict):
    filename = payload.get("filename")
    target_folder = payload.get("target_folder")
    if not filename or not target_folder:
        raise HTTPException(status_code=400, detail="'filename' and 'target_folder' are required")
    try:
        result = move_file_to_folder(filename, target_folder)
        logger.info(f"✅ Moved: {filename} → {target_folder}/")
        return {"result": result}
    except Exception as e:
        logger.error(f"❌ Move error: {e}")
        raise HTTPException(status_code=500, detail=str(e))