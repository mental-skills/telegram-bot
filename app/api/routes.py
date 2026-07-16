from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import FileResponse

from app.api.auth import TelegramInitDataValidator, WebAppAuthError
from app.api.dependencies import (
    SESSION_COOKIE_NAME,
    ProgressServiceDependency,
    RuntimeDependency,
    SessionManagerDependency,
    TelegramUserDependency,
)
from app.api.presenter import (
    BOUNDARY_SCENARIO_ID,
    present_progress,
    present_training,
    present_visual,
)
from app.api.schemas import (
    AgeRequest,
    AuthResponse,
    BootstrapResponse,
    MiniAppPresentationResponse,
    ProgressResponse,
    SituationResponse,
    TelegramAuthRequest,
    TrainingResponse,
    TransitionRequest,
    TransitionResponse,
    UiResponse,
    UserResponse,
)

router = APIRouter()


def _set_session_cookie(
    response: Response,
    runtime: RuntimeDependency,
    manager: SessionManagerDependency,
    telegram_user_id: int,
) -> AuthResponse:
    token = manager.issue(telegram_user_id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=runtime.settings.webapp_session_ttl_seconds,
        httponly=True,
        secure=runtime.settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return AuthResponse(expires_in=runtime.settings.webapp_session_ttl_seconds)


@router.post("/api/v1/auth/telegram", response_model=AuthResponse)
async def telegram_auth(
    payload: TelegramAuthRequest,
    response: Response,
    runtime: RuntimeDependency,
    manager: SessionManagerDependency,
) -> AuthResponse:
    validator = TelegramInitDataValidator(
        bot_token=runtime.settings.telegram_bot_token,
        max_age_seconds=runtime.settings.telegram_auth_max_age_seconds,
    )
    try:
        user = validator.validate(payload.init_data)
    except WebAppAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _set_session_cookie(response, runtime, manager, user.telegram_user_id)


@router.post("/api/v1/auth/dev", response_model=AuthResponse)
async def dev_auth(
    response: Response,
    runtime: RuntimeDependency,
    manager: SessionManagerDependency,
) -> AuthResponse:
    if runtime.settings.environment == "production" or not runtime.settings.dev_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _set_session_cookie(
        response,
        runtime,
        manager,
        runtime.settings.dev_auth_telegram_user_id,
    )


@router.post("/api/v1/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/api/v1/bootstrap", response_model=BootstrapResponse)
async def bootstrap(
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
    runtime: RuntimeDependency,
) -> BootstrapResponse:
    user = await service.get_or_create_user(telegram_user_id)
    summary = await service.get_progress_summary(telegram_user_id)
    current = await service.get_current_progress(telegram_user_id)
    ui = runtime.ui_texts
    return BootstrapResponse(
        user=UserResponse(
            telegram_user_id=user.telegram_user_id,
            age_group=user.age_group,
        ),
        ui=UiResponse(
            start_title=ui.start_title,
            start_text=ui.start_text,
            continue_training=ui.continue_training,
            age_prompt=ui.age_prompt,
            age_options={
                "6-8": ui.age_6_8,
                "9-12": ui.age_9_12,
                "13-16": ui.age_13_16,
            },
            privacy_text=ui.privacy_text,
        ),
        presentation=MiniAppPresentationResponse(
            start_logo=present_visual(
                runtime.mini_app_visuals.get_surface("start_logo")
            ),
            start_background=present_visual(
                runtime.mini_app_visuals.get_surface("start_background")
            ),
            home=present_visual(runtime.mini_app_visuals.get_surface("home")),
        ),
        progress=present_progress(summary),
        training=present_training(current, runtime) if current else None,
    )


@router.patch("/api/v1/me/age", response_model=UserResponse)
async def set_age(
    payload: AgeRequest,
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
) -> UserResponse:
    user = await service.set_age(telegram_user_id, payload.age_group)
    return UserResponse(telegram_user_id=user.telegram_user_id, age_group=user.age_group)


@router.get("/api/v1/situations", response_model=list[SituationResponse])
async def situations(
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
) -> list[SituationResponse]:
    summary = await service.get_progress_summary(telegram_user_id)
    return list(present_progress(summary).situations)


@router.get("/api/v1/progress", response_model=ProgressResponse)
async def progress(
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
) -> ProgressResponse:
    return present_progress(await service.get_progress_summary(telegram_user_id))


@router.post("/api/v1/training/start-or-continue", response_model=TrainingResponse)
async def start_or_continue(
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
    runtime: RuntimeDependency,
) -> TrainingResponse:
    current = await service.start_or_continue(telegram_user_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="age_required")
    return present_training(current, runtime)


@router.get("/api/v1/training/current", response_model=TrainingResponse)
async def current_training(
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
    runtime: RuntimeDependency,
) -> TrainingResponse:
    current = await service.get_current_progress(telegram_user_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_progress")
    return present_training(current, runtime)


@router.post(
    "/api/v1/training/sessions/{session_id}/transitions",
    response_model=TransitionResponse,
)
async def transition(
    session_id: int,
    payload: TransitionRequest,
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
    runtime: RuntimeDependency,
) -> TransitionResponse:
    current = await service.get_current_progress(telegram_user_id)
    if current is None or current.trainer_session.id != session_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="stale")
    if current.trainer_session.scenario_id == BOUNDARY_SCENARIO_ID:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="scenario_02_intro_only",
        )

    result = await service.advance(
        telegram_user_id=telegram_user_id,
        session_id=session_id,
        revision=payload.revision,
        option_id=payload.option_id,
    )
    if result.status in {"stale", "duplicate", "next_unavailable"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.status)
    if result.status == "main_menu":
        return TransitionResponse(status="main_menu", training=None)
    if result.progress_screen is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.status)
    return TransitionResponse(
        status=result.status,
        training=present_training(result.progress_screen, runtime),
    )


@router.post("/api/v1/training/restart", response_model=TrainingResponse)
async def restart_training(
    telegram_user_id: TelegramUserDependency,
    service: ProgressServiceDependency,
    runtime: RuntimeDependency,
) -> TrainingResponse:
    current = await service.restart(telegram_user_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="age_required")
    return present_training(current, runtime)


@router.get("/api/v1/mini-app/assets/{asset_id}")
async def mini_app_asset(asset_id: str, runtime: RuntimeDependency) -> FileResponse:
    try:
        asset = runtime.mini_app_visuals.get_asset(asset_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="mini_app_asset_not_found",
        ) from exc
    return FileResponse(asset.path)


@router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
