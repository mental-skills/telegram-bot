from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.assets.repository import AssetRepository
from app.content.registry import ScenarioRegistry


def main() -> None:
    root = Path.cwd()
    assets = AssetRepository(
        manifest_path=root / "assets" / "asset_manifest.json",
        visual_usage_map_path=root / "assets" / "visual_usage_map.json",
        brand_tokens_path=root / "assets" / "brand_tokens.json",
        project_root=root,
    )
    registry = ScenarioRegistry.load(
        catalog_path=root / "content" / "scenario_catalog.json",
        schema_path=root / "content" / "scenario.schema.json",
        asset_repository=assets,
        continue_label="Продолжить",
    )
    loaded = ", ".join(registry.enabled_order)
    print(f"OK: {registry.module_id} [{loaded}]")


if __name__ == "__main__":
    main()
