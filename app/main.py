from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.routes.core import router as core_router
from app.api.v1.routes.phase2 import router as phase2_router
from app.api.v1.routes.pilot import router as pilot_router
from app.api.webhooks.whatsapp import router as whatsapp_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.debug)
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.exception_handler(DomainError)
    async def domain_error_handler(_, exc: DomainError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(core_router, prefix="/api/v1")
    app.include_router(pilot_router, prefix="/api/v1")
    app.include_router(phase2_router, prefix="/api/v1")
    app.include_router(whatsapp_router, prefix="/webhooks")

    return app


app = create_app()
