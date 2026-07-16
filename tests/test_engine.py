from __future__ import annotations

from app.content.models import AgeGroup
from app.content.registry import ScenarioRegistry
from app.engine.engine import ScenarioEngine

FINAL_OPTIONS = [
    (first, f"{first}{number}")
    for first in ("a", "b", "c", "d")
    for number in (1, 2, 3)
]


def test_all_scenarios_use_three_age_versions(scenario_registry: ScenarioRegistry) -> None:
    ages: tuple[AgeGroup, ...] = ("6-8", "9-12", "13-16")
    for engine in scenario_registry.engines.values():
        intro_texts = {engine.render("intro", age).text for age in ages}
        question_texts = {engine.render("start_choice", age).text for age in ages}
        assert len(intro_texts) == 3, engine.scenario_id
        assert len(question_texts) == 3, engine.scenario_id


def test_every_scenario_has_exactly_12_complete_branches(
    scenario_registry: ScenarioRegistry,
) -> None:
    for engine in scenario_registry.engines.values():
        for first, second in FINAL_OPTIONS:
            first_transition = engine.transition("start_choice", first)
            second_transition = engine.transition(first_transition.to_node, second)
            now_screen = engine.render(second_transition.to_node, "9-12")
            assert now_screen.node_type == "outcome"
            repeated_transition = engine.transition(now_screen.node_id, "continue")
            repeated_screen = engine.render(repeated_transition.to_node, "9-12")
            assert repeated_screen.node_type == "outcome"
            advice_transition = engine.transition(repeated_screen.node_id, "continue")
            advice_screen = engine.render(advice_transition.to_node, "9-12")
            assert advice_screen.node_type == "advice"
            assert advice_screen.quote
            assert engine.transition(advice_screen.node_id, "continue").to_node == "summary_main"


def test_common_part_reaches_completion_for_all_scenarios(
    scenario_registry: ScenarioRegistry,
) -> None:
    for engine in scenario_registry.engines.values():
        node = "summary_main"
        for _ in range(24):
            screen = engine.render(node, "9-12")
            if screen.node_id == "completion":
                assert screen.is_completion
                break
            node = engine.transition(node, "continue").to_node
        else:
            raise AssertionError(f"completion was not reached: {engine.scenario_id}")


def test_media_nodes_have_text_fallback(scenario_registry: ScenarioRegistry) -> None:
    for engine in scenario_registry.engines.values():
        for node_id, node in engine.bundle.scenario.nodes.items():
            if node.media:
                assert engine.render(node_id, "6-8").text


def test_hidden_methodology_does_not_render(engine_01: ScenarioEngine) -> None:
    screen = engine_01.render("intro", "9-12")
    user_text = f"{screen.title}\n{screen.text}\n{screen.quote}"
    assert "Помочь родителю отреагировать" not in user_text
    assert "methodology" not in user_text


def test_scenario_06_safety_protocol_is_separate_and_not_completion(
    scenario_registry: ScenarioRegistry,
) -> None:
    engine = scenario_registry.get_engine("CHILD_SILENT_AFTER_DEFEAT_06")
    emergency_nodes = [
        node_id
        for node_id, node in engine.bundle.scenario.nodes.items()
        if node.type == "emergency"
    ]
    assert emergency_nodes
    for node_id in emergency_nodes:
        screen = engine.render(node_id, "9-12")
        assert not screen.is_completion
        assert screen.buttons
