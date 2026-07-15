from __future__ import annotations

from dataclasses import dataclass

from app.content.models import MediaRef, NodeType


@dataclass(frozen=True)
class ScreenButton:
    id: str
    label: str
    next_node: str
    tracking_code: str | None = None


@dataclass(frozen=True)
class ScenarioScreen:
    scenario_id: str
    content_version: str
    node_id: str
    node_type: NodeType
    title: str | None
    text: str
    quote: str | None
    media: MediaRef | None
    buttons: tuple[ScreenButton, ...]
    is_completion: bool


@dataclass(frozen=True)
class TransitionResult:
    from_node: str
    option_id: str
    to_node: str
    tracking_code: str | None
    assessment: dict[str, object] | None
