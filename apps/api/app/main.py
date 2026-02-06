from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.middleware import request_id_middleware, security_headers_middleware
from app.core.errors import error_response
from app.api.health import router as health_router
from app.api.auth import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="Order and Inventory API")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return error_response(request, "HTTP_ERROR", exc.detail, exc.status_code)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return error_response(request, "INTERNAL_ERROR", "Internal server error", 500)

    app.middleware("http")(request_id_middleware)
    app.middleware("http")(security_headers_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.include_router(health_router)
    app.include_router(auth_router)

    return app


app = create_app()
