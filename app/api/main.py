from __future__ import annotations

from fastapi import FastAPI

from app.api.auth import SessionTokenManager
from app.api.routes import router
from app.application import ApplicationRuntime, build_runtime
from app.core.config import Settings, get_settings


def create_api_app(
    settings: Settings | None = None,
    runtime: ApplicationRuntime | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    if resolved_settings.environment == "production":
        if resolved_settings.dev_auth_enabled:
            raise RuntimeError("DEV_AUTH_ENABLED must be false in production")
        if not resolved_settings.session_cookie_secure:
            raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")
        if resolved_settings.webapp_session_secret.startswith("local-development-"):
            raise RuntimeError("WEBAPP_SESSION_SECRET must be changed in production")
    SessionTokenManager(
        secret=resolved_settings.webapp_session_secret,
        ttl_seconds=resolved_settings.webapp_session_ttl_seconds,
    )

    app = FastAPI(
        title="Mental Skills Mini App API",
        version="1.0.0",
        docs_url="/api/docs" if resolved_settings.environment != "production" else None,
        redoc_url=None,
        openapi_url=(
            "/api/openapi.json" if resolved_settings.environment != "production" else None
        ),
    )
    app.state.runtime = runtime or build_runtime(resolved_settings)
    app.include_router(router)
    return app


app = create_api_app()
