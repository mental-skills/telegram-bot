from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)


class AuthResponse(BaseModel):
    authenticated: bool = True
    expires_in: int


class AgeRequest(BaseModel):
    age_group: Literal["6-8", "9-12", "13-16"]


class UserResponse(BaseModel):
    telegram_user_id: int
    age_group: str | None


class UiResponse(BaseModel):
    start_title: str
    start_text: str
    continue_training: str
    age_prompt: str
    age_options: dict[str, str]
    privacy_text: str


class MiniAppVisualResponse(BaseModel):
    id: str
    url: str
    alt: str
    kind: str


class MiniAppPresentationResponse(BaseModel):
    start_logo: MiniAppVisualResponse
    start_background: MiniAppVisualResponse
    home: MiniAppVisualResponse


ActionKind = Literal[
    "choice",
    "continue",
    "next_scenario",
    "repeat",
    "main_menu",
    "open_bot",
    "open_scenario",
]


class ActionResponse(BaseModel):
    id: str
    label: str
    kind: ActionKind
    href: str | None = None
    scenario_id: str | None = None


class ScreenResponse(BaseModel):
    node_id: str
    type: str
    title: str | None
    text: str
    quote: str | None
    visual: MiniAppVisualResponse | None
    actions: list[ActionResponse]
    is_completion: bool
    is_mini_app_boundary: bool = False
    stage: int
    stage_count: int = 8


class TrainingResponse(BaseModel):
    module_id: str
    route_mode: Literal["full", "standalone"]
    scenario_id: str
    content_version: str
    scenario_title: str
    session_id: int
    revision: int
    status: str
    screen: ScreenResponse


class SituationResponse(BaseModel):
    module_id: str
    route_mode: Literal["full", "standalone"]
    scenario_id: str
    title: str
    estimated_minutes: int | None
    status: Literal["not_started", "in_progress", "completed"]
    attempt_no: int | None


class ProgressResponse(BaseModel):
    module_id: str
    route_mode: Literal["full", "standalone"]
    available_count: int
    completed_count: int
    current_scenario_id: str | None
    situations: list[SituationResponse]


class BootstrapResponse(BaseModel):
    user: UserResponse
    ui: UiResponse
    presentation: MiniAppPresentationResponse
    progress: ProgressResponse
    training: TrainingResponse | None


class TransitionRequest(BaseModel):
    revision: int = Field(ge=1)
    option_id: str = Field(min_length=1, max_length=32)


class TransitionResponse(BaseModel):
    status: str
    training: TrainingResponse | None
