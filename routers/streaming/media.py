# routers/media.py
import os
import mimetypes
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, Response
from utils.auth import verify_short_encrypted_url
from utils.aws_s3 import stream_s3_file
from config.config import MEDIA_ROOT_PATH

router = APIRouter(tags=["Media"])

# ── 1. Encrypted image token (profile pics) ───────────────────────────────────
@router.get("/images")
async def serve_encrypted_image(q: str = Query(...)):
    try:
        if not q:
            return Response(content="Bad Request: Missing token", status_code=400)

        extracted = verify_short_encrypted_url(q)
        if not extracted:
            return Response(content="Forbidden: Invalid token", status_code=403)

        s3_key = extracted["path"]
        return await stream_s3_file(s3_key)

    except Exception:
        return Response(content="Error fetching file", status_code=500)


# ── 2. S3 media streaming (services, used-products, local-jobs, careers) ──────
@router.get("/media/{folder}/services/{file_path:path}")
async def stream_service_media(folder: str, file_path: str):
    return await stream_s3_file(f"media/{folder}/services/{file_path}")


@router.get("/media/{folder}/used-product-listings/{file_path:path}")
async def stream_used_product_media(folder: str, file_path: str):
    return await stream_s3_file(f"media/{folder}/used-product-listings/{file_path}")


@router.get("/media/{folder}/local-jobs/{file_path:path}")
async def stream_local_job_media(folder: str, file_path: str):
    return await stream_s3_file(f"media/{folder}/local-jobs/{file_path}")


@router.get("/media/{folder}/careers/{file_path:path}")
async def stream_career_media(folder: str, file_path: str):
    return await stream_s3_file(f"media/{folder}/careers/{file_path}")


# ── 3. Local file system streaming (uploads) ──────────────────────────────────
@router.get("/uploads/{folder}/{file_path:path}")
async def serve_local_file(folder: str, file_path: str):
    try:
        full_path = os.path.join(MEDIA_ROOT_PATH, "uploads", folder, file_path)

        if not os.path.exists(full_path):
            return Response(content="File not found", status_code=404)

        file_size    = os.path.getsize(full_path)
        content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        filename     = os.path.basename(full_path)

        def _iter_file():
            with open(full_path, "rb") as f:
                while chunk := f.read(1024 * 64):
                    yield chunk

        return StreamingResponse(
            _iter_file(),
            headers={
                "Content-Type":        content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length":      str(file_size),
                "Cache-Control":       "no-store",
                "Pragma":              "no-cache",
                "Expires":             "0",
            },
        )
    except Exception:
        return Response(content="Server error", status_code=500)