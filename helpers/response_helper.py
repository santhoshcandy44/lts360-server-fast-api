from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Optional
from config import API_DOC_BASE_URL

from fastapi import Request
from fastapi.responses import JSONResponse

def send_json_response(
    status_code: int,
    message: str,
    data: Any = None,
    is_successful: bool = True,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "isSuccessful": is_successful,
            "status": "success" if is_successful else "error",
            "message": message,
            "data": data if data is not None else "",
        },
    )


def send_error_response(
    request: Request,
    status_code: int,
    message: str,
    error_details: Optional[Any] = None,
    error_code: str = "ERROR",
) -> JSONResponse:
    error_response = {
        "status": "error",
        "statusCode": status_code,
        "error": {
            "code": error_code,
            "message": message,
            "details": error_details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
        },
        "requestId": str(uuid4()),
        "documentation_url": f"{API_DOC_BASE_URL}/docs/errors",
    }
    return JSONResponse(
        status_code=status_code,
        content={
            "isSuccessful": False,
            "status": "error",
            "message": message,
            "data": error_response,
        },
    )

class AppException(Exception):
    def __init__(self, status_code: int, message: str, error_code: str = None):
        self.status_code = status_code
        self.message     = message
        self.error_code  = error_code
