from __future__ import annotations

from pathlib import Path

import pytest

from app.assets.repository import AssetRepository
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
def engine(content_repository: ContentRepository) -> ScenarioEngine:
    bundle = content_repository.load()
    ui = content_repository.get_ui_texts()
    return ScenarioEngine(bundle, continue_label=ui.continue_)
