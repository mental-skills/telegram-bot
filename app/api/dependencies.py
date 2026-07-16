from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import SessionTokenManager, WebAppAuthError
from app.application import ApplicationRuntime
from app.db.repositories import ProgressRepository, UserRepository
from app.services.progress import ProgressService

SESSION_COOKIE_NAME = "mental_skills_session"


def get_runtime(request: Request) -> ApplicationRuntime:
    return request.app.state.runtime  # type: ignore[no-any-return]


RuntimeDependency = Annotated[ApplicationRuntime, Depends(get_runtime)]


async def get_db(runtime: RuntimeDependency) -> AsyncIterator[AsyncSession]:
    async with runtime.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbDependency = Annotated[AsyncSession, Depends(get_db)]


def get_session_manager(runtime: RuntimeDependency) -> SessionTokenManager:
    return SessionTokenManager(
        secret=runtime.settings.webapp_session_secret,
        ttl_seconds=runtime.settings.webapp_session_ttl_seconds,
    )


SessionManagerDependency = Annotated[SessionTokenManager, Depends(get_session_manager)]


def get_current_telegram_user_id(
    manager: SessionManagerDependency,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> int:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return manager.verify(session_cookie)
    except WebAppAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


TelegramUserDependency = Annotated[int, Depends(get_current_telegram_user_id)]


def get_progress_service(
    db: DbDependency,
    runtime: RuntimeDependency,
) -> ProgressService:
    return ProgressService(
        user_repository=UserRepository(db),
        progress_repository=ProgressRepository(db),
        registry=runtime.scenario_registry,
        privacy_version=runtime.settings.privacy_version,
    )


ProgressServiceDependency = Annotated[ProgressService, Depends(get_progress_service)]
