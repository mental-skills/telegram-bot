from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.assets.repository import AssetRepository
from app.content.validator import ScenarioValidator


def main() -> None:
    root = Path.cwd()
    assets = AssetRepository(
        manifest_path=root / "assets" / "asset_manifest.json",
        visual_usage_map_path=root / "assets" / "visual_usage_map.json",
        brand_tokens_path=root / "assets" / "brand_tokens.json",
        project_root=root,
    )
    validator = ScenarioValidator(root / "content" / "scenario.schema.json", assets)
    bundle = validator.validate_file(root / "content" / "PREMATCH_INSTRUCTIONS_02.json")
    print(f"OK: {bundle.scenario.id} {bundle.scenario.content_version}")


if __name__ == "__main__":
    main()
