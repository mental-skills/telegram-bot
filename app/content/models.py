from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AgeGroup = Literal["6-8", "9-12", "13-16"]
NodeType = Literal["info", "choice", "outcome", "advice", "tool", "completion", "emergency"]

SYSTEM_MAIN_MENU = "__MAIN_MENU__"
SYSTEM_NEXT_SCENARIO = "__NEXT_SCENARIO__"
SYSTEM_ROUTES = {SYSTEM_MAIN_MENU, SYSTEM_NEXT_SCENARIO}


class MediaRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    mode: Literal["photo"] = "photo"
    show_once_per_session: bool | None = None
    presentation: Literal["hero", "card", "compact"] | None = None
    caption_strategy: Literal["auto", "caption", "separate_message"] | None = None


class ScenarioButton(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    next: str
    tracking_code: str | None = None


class ScenarioNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: NodeType
    title: str | None = None
    text: str | None = None
    text_by_age: dict[AgeGroup, str] | None = None
    quote: str | None = None
    buttons: list[ScenarioButton] = Field(default_factory=list)
    next: str | None = None
    assessment: dict[str, Any] | None = None
    methodology: dict[str, Any] | None = None
    media: MediaRef | None = None

    def text_for_age(self, age_group: AgeGroup) -> str:
        if self.text_by_age:
            return self.text_by_age[age_group]
        return self.text or ""


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    content_version: str
    sport: Literal["football"]
    language: Literal["ru"]
    title: str
    stage: Literal["before_match", "during_match", "after_match"]
    estimated_minutes: int | None = None
    age_groups: list[AgeGroup]
    entry_node: str
    dimensions: list[dict[str, Any]] = Field(default_factory=list)
    nodes: dict[str, ScenarioNode]
    asset_manifest: str | None = None


class ScenarioBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.2"]
    scenario: Scenario


class UiTexts(BaseModel):
    model_config = ConfigDict(extra="allow")

    age_prompt: str
    age_6_8: str
    age_9_12: str
    age_13_16: str
    back_to_menu: str
    continue_: str = Field(alias="continue")
    continue_training: str
    restart: str
    repeat_scenario: str
    privacy: str
    about: str
    tools: str
    change_age: str
    confirm_reset: str
    cancel: str
    retry: str
    start_title: str
    start_text: str
    menu_text: str
    age_saved: str
    no_active_session: str
    scenario_unavailable: str
    stale_callback: str
    duplicate_callback: str
    generic_error: str
    privacy_text: str
    reset_prompt: str
    reset_done: str
    help_text: str
    about_text: str
    tools_text: str
