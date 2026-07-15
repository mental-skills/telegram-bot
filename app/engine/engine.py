from __future__ import annotations

from app.content.models import (
    SYSTEM_MAIN_MENU,
    SYSTEM_NEXT_SCENARIO,
    SYSTEM_ROUTES,
    AgeGroup,
    ScenarioBundle,
    ScenarioNode,
)
from app.core.errors import ScenarioStateError
from app.engine.types import ScenarioScreen, ScreenButton, TransitionResult


class ScenarioEngine:
    def __init__(self, bundle: ScenarioBundle, continue_label: str) -> None:
        self.bundle = bundle
        self.continue_label = continue_label

    @property
    def scenario_id(self) -> str:
        return self.bundle.scenario.id

    @property
    def content_version(self) -> str:
        return self.bundle.scenario.content_version

    @property
    def entry_node(self) -> str:
        return self.bundle.scenario.entry_node

    def render(self, node_id: str, age_group: AgeGroup) -> ScenarioScreen:
        node = self._get_node(node_id)
        return ScenarioScreen(
            scenario_id=self.scenario_id,
            content_version=self.content_version,
            node_id=node_id,
            node_type=node.type,
            title=node.title,
            text=node.text_for_age(age_group),
            quote=node.quote,
            media=node.media,
            buttons=tuple(self._buttons_for_node(node)),
            is_completion=node.type in {"completion", "emergency"},
        )

    def transition(self, current_node_id: str, option_id: str) -> TransitionResult:
        node = self._get_node(current_node_id)
        button = next((item for item in self._buttons_for_node(node) if item.id == option_id), None)
        if button is None:
            raise ScenarioStateError(f"Option {option_id} is not valid for node {current_node_id}")

        if (
            button.next_node not in self.bundle.scenario.nodes
            and button.next_node not in SYSTEM_ROUTES
        ):
            raise ScenarioStateError(f"Target node is missing: {button.next_node}")

        target_assessment = None
        if button.next_node in self.bundle.scenario.nodes:
            target_node = self.bundle.scenario.nodes[button.next_node]
            target_assessment = target_node.assessment

        return TransitionResult(
            from_node=current_node_id,
            option_id=option_id,
            to_node=button.next_node,
            tracking_code=button.tracking_code,
            assessment=target_assessment,
        )

    def is_system_route(self, node_id: str) -> bool:
        return node_id in {SYSTEM_MAIN_MENU, SYSTEM_NEXT_SCENARIO}

    def _get_node(self, node_id: str) -> ScenarioNode:
        try:
            return self.bundle.scenario.nodes[node_id]
        except KeyError as exc:
            raise ScenarioStateError(f"Scenario node not found: {node_id}") from exc

    def _buttons_for_node(self, node: ScenarioNode) -> list[ScreenButton]:
        if node.buttons:
            return [
                ScreenButton(
                    id=button.id,
                    label=button.label,
                    next_node=button.next,
                    tracking_code=button.tracking_code,
                )
                for button in node.buttons
            ]
        if node.next:
            return [
                ScreenButton(
                    id="continue",
                    label=self.continue_label,
                    next_node=node.next,
                    tracking_code=None,
                )
            ]
        return []
