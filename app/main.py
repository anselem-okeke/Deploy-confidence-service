import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes_details import router as details_router
from app.api.routes_health import router as health_router
from app.api.routes_score import router as score_router
from app.config import settings
from app.db.init_db import create_all_tables
from app.scheduler.updater import run_score_update_job, start_scheduler, stop_scheduler
from app.utils.logging import setup_logging

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s version=%s env=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    create_all_tables()
    logger.info("Database tables initialized")

    logger.info("About to run immediate score update job")
    run_score_update_job()

    logger.info("About to start scheduler")
    start_scheduler(settings.check_interval_seconds)

    logger.info("Startup sequence completed")

    try:
        yield
    finally:
        stop_scheduler()
        logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Deployment Confidence Service API",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(score_router)
app.include_router(details_router)


























# import logging
#
# from fastapi import FastAPI
#
# from app.api.routes_health import router as health_router
# from app.config import settings
# from app.db.init_db import create_all_tables
# from app.utils.logging import setup_logging
# from contextlib import asynccontextmanager
# from app.api.routes_details import router as details_router
# from app.api.routes_health import router as health_router
# from app.api.routes_score import router as score_router
# from app.scheduler.updater import run_score_update_job, start_scheduler, stop_scheduler
#
# setup_logging(settings.log_level)
# logger = logging.getLogger(__name__)
#
# app = FastAPI(
#     title=settings.app_name,
#     version=settings.app_version,
#     description="Deployment Confidence Service API",
# )
#
# app.include_router(health_router)
# app.include_router(score_router)
# app.include_router(details_router)
#
#
# @app.on_event("startup")
# def on_startup() -> None:
#     logger.info(
#         "Starting %s version=%s env=%s",
#         settings.app_name,
#         settings.app_version,
#         settings.app_env,
#     )
#
#     create_all_tables()
#     logger.info("Database tables initialized")
#
#     logger.info("About to run immediate score update job")
#     run_score_update_job()
#
#     logger.info("About to start scheduler")
#     start_scheduler(settings.check_interval_seconds)
#
#     logger.info("Startup sequence completed")
#
#
# @app.on_event("shutdown")
# def on_shutdown() -> None:
#     stop_scheduler()
#     logger.info("Shutting down %s", settings.app_name)