from __future__ import annotations

import json
from collections import defaultdict, deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from app.assets.repository import AssetRepository
from app.content.models import SYSTEM_ROUTES, ScenarioBundle
from app.core.errors import ContentValidationError


class DuplicateKeyError(ValueError):
    pass


def _object_pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_no_duplicates(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file, object_pairs_hook=_object_pairs_without_duplicates)
    except DuplicateKeyError as exc:
        raise ContentValidationError(str(exc)) from exc
    if not isinstance(data, dict):
        raise ContentValidationError(f"Expected JSON object in {path}")
    return data


class ScenarioValidator:
    def __init__(self, schema_path: Path, asset_repository: AssetRepository) -> None:
        self.schema_path = schema_path
        self.asset_repository = asset_repository

    def validate_file(self, scenario_path: Path) -> ScenarioBundle:
        schema = load_json_no_duplicates(self.schema_path)
        raw = load_json_no_duplicates(scenario_path)
        errors = sorted(Draft202012Validator(schema).iter_errors(raw), key=str)
        if errors:
            details = "; ".join(error.message for error in errors[:5])
            raise ContentValidationError(f"JSON Schema validation failed: {details}")

        bundle = ScenarioBundle.model_validate(raw)
        self._validate_graph(bundle)
        self._validate_text_fallbacks(bundle)
        self._validate_media(bundle)
        self._validate_no_exitless_cycles(bundle)
        return bundle

    def _validate_graph(self, bundle: ScenarioBundle) -> None:
        scenario = bundle.scenario
        nodes = scenario.nodes
        if scenario.entry_node not in nodes:
            raise ContentValidationError(f"entry_node does not exist: {scenario.entry_node}")

        missing: list[str] = []
        for from_node, next_node in self._iter_edges(bundle):
            if next_node not in nodes and next_node not in SYSTEM_ROUTES:
                missing.append(f"{from_node} -> {next_node}")
        if missing:
            raise ContentValidationError("Missing next nodes: " + ", ".join(missing))

        reachable = self._reachable_nodes(bundle)
        unreachable = sorted(set(nodes) - reachable)
        if unreachable:
            raise ContentValidationError("Unreachable nodes: " + ", ".join(unreachable))

    def _validate_text_fallbacks(self, bundle: ScenarioBundle) -> None:
        for node_id, node in bundle.scenario.nodes.items():
            has_text = bool(node.text) or bool(node.text_by_age)
            if node.media and not has_text:
                raise ContentValidationError(f"Media node has no text fallback: {node_id}")
            if node.text_by_age:
                missing_ages = set(bundle.scenario.age_groups) - set(node.text_by_age)
                if missing_ages:
                    raise ContentValidationError(
                        f"Node {node_id} misses age texts: {', '.join(sorted(missing_ages))}"
                    )

    def _validate_media(self, bundle: ScenarioBundle) -> None:
        self.asset_repository.load()
        self.asset_repository.validate()
        for node_id, node in bundle.scenario.nodes.items():
            if node.media is None:
                continue
            if not self.asset_repository.has_runtime_asset(node.media.asset_id):
                raise ContentValidationError(
                    f"Node {node_id} uses missing or non-runtime asset: {node.media.asset_id}"
                )

    def _validate_no_exitless_cycles(self, bundle: ScenarioBundle) -> None:
        graph: dict[str, list[str]] = defaultdict(list)
        reverse: dict[str, list[str]] = defaultdict(list)
        completion_like: set[str] = set()
        for node_id, node in bundle.scenario.nodes.items():
            if node.type in {"completion", "emergency"}:
                completion_like.add(node_id)
            for _, to_node in self._iter_edges_for_node(node_id, node):
                if to_node in SYSTEM_ROUTES:
                    completion_like.add(node_id)
                    continue
                graph[node_id].append(to_node)
                reverse[to_node].append(node_id)

        can_reach_exit = set(completion_like)
        queue: deque[str] = deque(completion_like)
        while queue:
            current = queue.popleft()
            for previous in reverse[current]:
                if previous not in can_reach_exit:
                    can_reach_exit.add(previous)
                    queue.append(previous)

        reachable = self._reachable_nodes(bundle)
        trapped = sorted(reachable - can_reach_exit)
        if trapped:
            raise ContentValidationError(
                "Nodes cannot reach completion or a system route: " + ", ".join(trapped)
            )

    def _reachable_nodes(self, bundle: ScenarioBundle) -> set[str]:
        nodes = bundle.scenario.nodes
        reachable: set[str] = set()
        stack = [bundle.scenario.entry_node]
        while stack:
            node_id = stack.pop()
            if node_id in reachable or node_id in SYSTEM_ROUTES:
                continue
            reachable.add(node_id)
            node = nodes[node_id]
            stack.extend(
                next_node
                for _, next_node in self._iter_edges_for_node(node_id, node)
                if next_node not in SYSTEM_ROUTES
            )
        return reachable

    def _iter_edges(self, bundle: ScenarioBundle) -> Iterable[tuple[str, str]]:
        for node_id, node in bundle.scenario.nodes.items():
            yield from self._iter_edges_for_node(node_id, node)

    @staticmethod
    def _iter_edges_for_node(node_id: str, node: Any) -> Iterable[tuple[str, str]]:
        if node.next:
            yield node_id, node.next
        for button in node.buttons:
            yield node_id, button.next
