from __future__ import annotations

from pathlib import Path

import pytest

from app.assets.repository import AssetRepository
from app.content.registry import ScenarioRegistry
from app.content.repository import ContentRepository
from app.engine.engine import ScenarioEngine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def asset_repository() -> AssetRepository:
    repository = AssetRepository(
        manifest_path=PROJECT_ROOT / "assets" / "asset_manifest.json",
        visual_usage_map_path=PROJECT_ROOT / "assets" / "visual_usage_map.json",
        brand_tokens_path=PROJECT_ROOT / "assets" / "brand_tokens.json",
        project_root=PROJECT_ROOT,
    )
    repository.load()
    return repository


@pytest.fixture()
def content_repository(asset_repository: AssetRepository) -> ContentRepository:
    return ContentRepository(
        scenario_path=PROJECT_ROOT / "content" / "PREMATCH_INSTRUCTIONS_02.json",
        schema_path=PROJECT_ROOT / "content" / "scenario.schema.json",
        ui_texts_path=PROJECT_ROOT / "content" / "ui_texts.ru.json",
        asset_repository=asset_repository,
    )


@pytest.fixture()
def scenario_registry(asset_repository: AssetRepository) -> ScenarioRegistry:
    return ScenarioRegistry.load(
        catalog_path=PROJECT_ROOT / "content" / "scenario_catalog.json",
        schema_path=PROJECT_ROOT / "content" / "scenario.schema.json",
        asset_repository=asset_repository,
        continue_label="Продолжить",
    )


@pytest.fixture()
def engine(content_repository: ContentRepository) -> ScenarioEngine:
    bundle = content_repository.load()
    ui = content_repository.get_ui_texts()
    return ScenarioEngine(bundle, continue_label=ui.continue_)


@pytest.fixture()
def engine_01(scenario_registry: ScenarioRegistry) -> ScenarioEngine:
    return scenario_registry.get_engine("PREMATCH_GAME_REFUSAL_01")


@pytest.fixture()
def engine_02(scenario_registry: ScenarioRegistry) -> ScenarioEngine:
    return scenario_registry.get_engine("PREMATCH_INSTRUCTIONS_02")
