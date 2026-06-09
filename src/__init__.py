from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.auth.routers import router as auth_router
from src.common.configs.logging import get_logger, setup_logging
from src.common.configs.settings import get_settings
from src.common.database.session import check_database_connection
from src.common.exceptions.api_exception import APIException
from src.common.handlers.exception_handler import (
    exception_handler,
    validation_exception_handler,
)
from src.common.middlewares.log_middleware import LoggingMiddleware
from src.common.routers import router as common_router

settings = get_settings()

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Application startup")
    await check_database_connection()
    yield
    logger.info("Application shutdown")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIException, exception_handler)
    app.add_exception_handler(Exception, exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)


def register_middlewares(app: FastAPI) -> None:
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


def register_routers(app: FastAPI) -> None:
    base_router = APIRouter(prefix="/api/v1")
    base_router.include_router(common_router, tags=["Common"])
    base_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(base_router)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # Add middlewares
    register_middlewares(app)

    # Add exception handlers
    register_exception_handlers(app)

    # Add routers
    register_routers(app)

    return app


app = create_app()
