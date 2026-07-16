from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.assets.repository import AssetRepository
from app.content.models import SYSTEM_ROUTES, ScenarioBundle
from app.content.registry import ScenarioRegistry
from app.content.repository import ContentRepository
from app.content.validator import ScenarioValidator
from app.core.errors import AssetValidationError, ContentValidationError


def test_json_passes_schema_and_extended_validation(
    content_repository: ContentRepository,
) -> None:
    bundle = content_repository.load()
    assert bundle.schema_version == "1.2"
    assert bundle.scenario.id == "PREMATCH_INSTRUCTIONS_02"
    assert bundle.scenario.content_version == "2026-07-16.1-approved-v1"


def test_scenario_catalog_loads_enabled_scenarios(scenario_registry: ScenarioRegistry) -> None:
    assert scenario_registry.module_id == "football_parent_mvp"
    assert scenario_registry.start_scenario_id == "PREMATCH_GAME_REFUSAL_01"
    assert scenario_registry.enabled_order == (
        "PREMATCH_GAME_REFUSAL_01",
        "PREMATCH_INSTRUCTIONS_02",
        "CHILD_ERROR_LOOKS_AT_PARENT_03",
        "CHILD_LEFT_ON_BENCH_04",
        "DISPUTED_REFEREE_DECISION_05",
        "CHILD_SILENT_AFTER_DEFEAT_06",
        "PARENT_RESPONSE_AFTER_VICTORY_07",
    )
    assert set(scenario_registry.engines) == set(scenario_registry.enabled_order)


def test_all_enabled_scenarios_pass_schema(
    scenario_registry: ScenarioRegistry,
) -> None:
    assert len(scenario_registry.bundles) == 7
    assert all(bundle.scenario.title for bundle in scenario_registry.bundles.values())


def test_all_transitions_resolve(scenario_registry: ScenarioRegistry) -> None:
    for bundle in scenario_registry.bundles.values():
        _assert_transitions_resolve(bundle)


def _assert_transitions_resolve(bundle: ScenarioBundle) -> None:
    nodes = bundle.scenario.nodes
    for node in nodes.values():
        targets = [button.next for button in node.buttons]
        if node.next:
            targets.append(node.next)
        for target in targets:
            assert target in nodes or target in SYSTEM_ROUTES


def test_all_nodes_are_reachable(
    content_repository: ContentRepository,
    scenario_registry: ScenarioRegistry,
) -> None:
    validator = ScenarioValidator(
        content_repository.schema_path, content_repository.asset_repository
    )
    for bundle in scenario_registry.bundles.values():
        reachable = validator._reachable_nodes(bundle)  # noqa: SLF001
        assert reachable == set(bundle.scenario.nodes)


def test_missing_asset_is_rejected(tmp_path: Path, asset_repository: AssetRepository) -> None:
    manifest = json.loads((Path("assets") / "asset_manifest.json").read_text(encoding="utf-8"))
    manifest["assets"]["ui_dialogue_choice"]["path"] = "assets/runtime/not-found.png"
    manifest_path = tmp_path / "asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    broken_assets = AssetRepository(
        manifest_path=manifest_path,
        visual_usage_map_path=Path("assets") / "visual_usage_map.json",
        brand_tokens_path=Path("assets") / "brand_tokens.json",
    )
    broken_assets.load()
    with pytest.raises(AssetValidationError):
        broken_assets.validate()


def test_design_reference_asset_is_not_runtime(asset_repository: AssetRepository) -> None:
    with pytest.raises(AssetValidationError):
        asset_repository.get_runtime_asset("brand_graphic_elements")


def test_duplicate_json_key_is_rejected(tmp_path: Path, asset_repository: AssetRepository) -> None:
    bad_scenario = tmp_path / "bad.json"
    bad_scenario.write_text('{"schema_version":"1.2","schema_version":"1.2"}', encoding="utf-8")
    validator = ScenarioValidator(Path("content") / "scenario.schema.json", asset_repository)
    with pytest.raises(ContentValidationError):
        validator.validate_file(bad_scenario)
