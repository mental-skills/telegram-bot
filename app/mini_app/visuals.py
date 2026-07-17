from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MiniAppVisualAsset:
    id: str
    path: Path
    alt: str
    kind: str


class MiniAppVisualRepository:
    """Loads web-only assets and maps scenario screens to presentation ids."""

    def __init__(
        self,
        manifest_path: Path,
        presentation_path: Path,
        project_root: Path | None = None,
    ) -> None:
        self.manifest_path = manifest_path
        self.presentation_path = presentation_path
        self.project_root = (project_root or Path.cwd()).resolve()
        self._assets: dict[str, MiniAppVisualAsset] = {}
        self._surfaces: dict[str, str] = {}
        self._scenarios: dict[str, dict[str, Any]] = {}

    def load(self) -> None:
        manifest = self._read_json(self.manifest_path)
        presentation = self._read_json(self.presentation_path)
        assets: dict[str, MiniAppVisualAsset] = {}
        for asset_id, raw in manifest.get("assets", {}).items():
            path = (self.project_root / raw["path"]).resolve()
            allowed_root = (self.project_root / "assets" / "mini_app").resolve()
            if raw.get("shared_brand") is True:
                expected_brand = (
                    self.project_root / "assets" / "runtime" / "brand_logo_horizontal.png"
                ).resolve()
                if path != expected_brand or raw.get("kind") != "logo":
                    raise RuntimeError(f"Invalid shared Mini App brand asset: {asset_id}")
            else:
                try:
                    path.relative_to(allowed_root)
                except ValueError as exc:
                    raise RuntimeError(
                        f"Mini App asset is outside assets/mini_app: {asset_id}"
                    ) from exc
            if not path.is_file():
                raise RuntimeError(f"Mini App asset is missing: {asset_id} -> {path}")
            assets[asset_id] = MiniAppVisualAsset(
                id=asset_id,
                path=path,
                alt=str(raw["alt"]),
                kind=str(raw["kind"]),
            )
        self._assets = assets
        self._surfaces = {
            str(key): str(value) for key, value in presentation.get("surfaces", {}).items()
        }
        self._scenarios = {
            str(key): value for key, value in presentation.get("scenarios", {}).items()
        }
        referenced = set(self._surfaces.values())
        for config in self._scenarios.values():
            referenced.update(value for value in config.get("types", {}).values() if value)
            referenced.update(value for value in config.get("nodes", {}).values() if value)
        missing = referenced.difference(self._assets)
        if missing:
            raise RuntimeError(f"Unknown Mini App visual ids: {', '.join(sorted(missing))}")

    def get_asset(self, asset_id: str) -> MiniAppVisualAsset:
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise KeyError(f"Unknown Mini App asset: {asset_id}") from exc

    def get_surface(self, surface: str) -> MiniAppVisualAsset:
        try:
            asset_id = self._surfaces[surface]
        except KeyError as exc:
            raise KeyError(f"Unknown Mini App surface: {surface}") from exc
        return self.get_asset(asset_id)

    def get_screen_visual(
        self,
        scenario_id: str,
        node_id: str,
        node_type: str,
    ) -> MiniAppVisualAsset | None:
        config = self._scenarios.get(scenario_id, {})
        asset_id = config.get("nodes", {}).get(node_id)
        if asset_id is None:
            asset_id = config.get("types", {}).get(node_type)
        return self.get_asset(asset_id) if asset_id else None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise RuntimeError(f"Expected object in {path}")
        return data
