from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.errors import AssetValidationError


@dataclass(frozen=True)
class Asset:
    id: str
    title: str
    purpose: str
    runtime: bool
    allowed_roles: tuple[str, ...]
    alt: str
    path: Path
    kind: str
    sha256: str | None
    width_px: int | None
    height_px: int | None
    format: str | None


class AssetRepository:
    def __init__(
        self,
        manifest_path: Path,
        visual_usage_map_path: Path,
        brand_tokens_path: Path,
        project_root: Path | None = None,
    ) -> None:
        self.manifest_path = manifest_path
        self.visual_usage_map_path = visual_usage_map_path
        self.brand_tokens_path = brand_tokens_path
        self.project_root = project_root or Path.cwd()
        self._assets: dict[str, Asset] = {}
        self.visual_usage_map: dict[str, Any] = {}
        self.brand_tokens: dict[str, Any] = {}

    @property
    def assets(self) -> dict[str, Asset]:
        return self._assets

    def load(self) -> None:
        manifest = self._read_json(self.manifest_path)
        self.visual_usage_map = self._read_json(self.visual_usage_map_path)
        self.brand_tokens = self._read_json(self.brand_tokens_path)
        raw_assets = manifest.get("assets", {})
        self._assets = {}
        for asset_id, raw in raw_assets.items():
            path = self.project_root / raw["path"]
            self._assets[asset_id] = Asset(
                id=asset_id,
                title=raw["title"],
                purpose=raw["purpose"],
                runtime=bool(raw["runtime"]),
                allowed_roles=tuple(raw.get("allowed_roles", [])),
                alt=raw["alt"],
                path=path,
                kind=raw["kind"],
                sha256=raw.get("sha256"),
                width_px=raw.get("width_px"),
                height_px=raw.get("height_px"),
                format=raw.get("format"),
            )

    def validate(self, verify_checksums: bool = True) -> None:
        if not self._assets:
            self.load()
        errors: list[str] = []
        for asset in self._assets.values():
            if not asset.path.exists():
                errors.append(f"Asset file is missing: {asset.id} -> {asset.path}")
                continue
            if verify_checksums and asset.sha256:
                digest = hashlib.sha256(asset.path.read_bytes()).hexdigest()
                if digest != asset.sha256:
                    errors.append(f"Asset checksum mismatch: {asset.id}")
        if errors:
            raise AssetValidationError("; ".join(errors))

    def get_runtime_asset(self, asset_id: str) -> Asset:
        asset = self._assets.get(asset_id)
        if asset is None:
            raise AssetValidationError(f"Unknown asset_id: {asset_id}")
        if not asset.runtime:
            raise AssetValidationError(f"Design-reference asset cannot be sent: {asset_id}")
        return asset

    def has_runtime_asset(self, asset_id: str) -> bool:
        try:
            self.get_runtime_asset(asset_id)
        except AssetValidationError:
            return False
        return True

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise AssetValidationError(f"Expected object in {path}")
        return data
