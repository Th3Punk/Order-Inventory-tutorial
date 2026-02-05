from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse


def error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request.headers.get("X-Request-Id"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
