from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from agentpost import __version__
from agentpost.api.errors import http_exception_handler, validation_exception_handler
from agentpost.api.middleware import request_context_middleware
from agentpost.api.routes.access import router as access_router
from agentpost.api.routes.admin import router as admin_router
from agentpost.api.routes.agents import router as agents_router
from agentpost.api.routes.approvals import router as approvals_router
from agentpost.api.routes.attachments import router as attachments_router
from agentpost.api.routes.connect import router as connect_router
from agentpost.api.routes.directory import router as directory_router
from agentpost.api.routes.human_auth import router as human_auth_router
from agentpost.api.routes.messages import router as messages_router
from agentpost.api.routes.oauth import router as oauth_router
from agentpost.api.routes.onboarding import router as onboarding_router
from agentpost.api.routes.orbit import router as orbit_router
from agentpost.api.routes.protocol import router as protocol_router
from agentpost.api.routes.system import router as system_router
from agentpost.api.routes.tasks import router as tasks_router
from agentpost.api.routes.wakeup import router as wakeup_router
from agentpost.config import Settings, get_settings
from agentpost.db import Database
from agentpost.observability.logging import configure_logging
from agentpost.wakeup.service import dispatch_pending_wakes

logger = logging.getLogger(__name__)


async def _wake_dispatch_loop(database: Database, settings: Settings) -> None:
    while True:
        try:
            with database.session_factory() as session:
                await asyncio.to_thread(dispatch_pending_wakes, session, settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("wake_dispatch_iteration_failed")
        await asyncio.sleep(settings.wake_dispatch_poll_seconds)


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    runtime_database = database or Database(runtime_settings.database_url)
    configure_logging(runtime_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        wake_task = (
            asyncio.create_task(_wake_dispatch_loop(runtime_database, runtime_settings))
            if runtime_settings.wake_dispatch_enabled
            else None
        )
        try:
            yield
        finally:
            if wake_task is not None:
                wake_task.cancel()
                with suppress(asyncio.CancelledError):
                    await wake_task
            runtime_database.dispose()

    app = FastAPI(
        title="AgentPost API",
        version=__version__,
        description="Human and AI task collaboration with durable messaging",
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.database = runtime_database
    app.middleware("http")(request_context_middleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(system_router)
    app.include_router(protocol_router)
    app.include_router(connect_router)
    app.include_router(oauth_router)
    app.include_router(admin_router)
    app.include_router(orbit_router)
    app.include_router(human_auth_router)
    app.include_router(tasks_router)
    app.include_router(wakeup_router)
    app.include_router(approvals_router)
    app.include_router(onboarding_router)
    app.include_router(agents_router)
    app.include_router(access_router)
    app.include_router(attachments_router)
    app.include_router(directory_router)
    app.include_router(messages_router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("agentpost.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
