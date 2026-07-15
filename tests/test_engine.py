from __future__ import annotations

from app.content.models import AgeGroup
from app.engine.engine import ScenarioEngine

FINAL_OPTIONS = [
    ("a", "a1", "a1_advice"),
    ("a", "a2", "a2_advice"),
    ("a", "a3", "a3_advice"),
    ("b", "b1", "b1_advice"),
    ("b", "b2", "b2_advice"),
    ("b", "b3", "b3_advice"),
    ("c", "c1", "c1_advice"),
    ("c", "c2", "c2_advice"),
    ("c", "c3", "c3_advice"),
    ("d", "d1", "d1_advice"),
    ("d", "d2", "d2_advice"),
    ("d", "d3", "d3_advice"),
]


def test_age_texts_are_used(engine: ScenarioEngine) -> None:
    ages: tuple[AgeGroup, ...] = ("6-8", "9-12", "13-16")
    texts = {age: engine.render("start_choice", age).text for age in ages}
    assert len(set(texts.values())) == 3
    assert "Подросток" in texts["13-16"]


def test_each_of_12_final_branches_reaches_advice(engine: ScenarioEngine) -> None:
    for first, second, expected_advice in FINAL_OPTIONS:
        first_transition = engine.transition("start_choice", first)
        intent = engine.transition(first_transition.to_node, "continue")
        second_transition = engine.transition(intent.to_node, second)
        outcome = engine.transition(second_transition.to_node, "continue")
        assert outcome.to_node == expected_advice
        advice_screen = engine.render(outcome.to_node, "9-12")
        assert advice_screen.node_type == "advice"
        assert advice_screen.quote


def test_common_part_reaches_completion(engine: ScenarioEngine) -> None:
    node = "summary_main"
    for _ in range(6):
        screen = engine.render(node, "9-12")
        if screen.node_id == "completion":
            assert screen.is_completion
            return
        transition = engine.transition(node, "continue")
        node = transition.to_node
    raise AssertionError("completion was not reached")


def test_media_nodes_have_text_fallback(engine: ScenarioEngine) -> None:
    bundle = engine.bundle
    for node_id, node in bundle.scenario.nodes.items():
        if node.media:
            assert engine.render(node_id, "6-8").text


def test_assessment_and_methodology_do_not_render(engine: ScenarioEngine) -> None:
    screen = engine.render("a1_advice", "9-12")
    user_text = f"{screen.title}\n{screen.text}\n{screen.quote}"
    assert "dimension_scores" not in user_text
    assert "technical_tags" not in user_text
    assert "methodology" not in user_text


def test_c3_advice_has_three_age_versions(engine: ScenarioEngine) -> None:
    ages: tuple[AgeGroup, ...] = ("6-8", "9-12", "13-16")
    texts = [engine.render("c3_advice", age).text for age in ages]
    assert len(set(texts)) == 3
