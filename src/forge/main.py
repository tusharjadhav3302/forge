"""FastAPI application entry point for Forge webhook gateway."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forge import __version__
from forge.api.routes import health_router
from forge.config import get_settings
from forge.orchestrator.checkpointer import close_redis_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown."""
    settings = get_settings()
    logger.info(f"Starting Forge v{__version__} with log level {settings.log_level}")

    # Startup
    yield

    # Shutdown
    logger.info("Shutting down Forge...")
    await close_redis_pool()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Forge SDLC Orchestrator",
        description="AI-Integrated SDLC Orchestrator webhook gateway",
        version=__version__,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(health_router)

    # Additional routers will be added here as implemented:
    # app.include_router(jira_router)
    # app.include_router(github_router)

    return app


# Create the app instance
app = create_app()


def main() -> None:
    """Run the application with uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "forge.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.log_level == "DEBUG",
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
