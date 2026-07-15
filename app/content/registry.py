from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.assets.repository import AssetRepository
from app.content.models import ScenarioBundle
from app.content.validator import ScenarioValidator, load_json_no_duplicates
from app.core.errors import ContentValidationError
from app.engine.engine import ScenarioEngine


class CatalogScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    path: str
    enabled: bool


class ScenarioCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str
    start_scenario_id: str
    scenarios: list[CatalogScenario]


class ScenarioRegistry:
    def __init__(
        self,
        catalog: ScenarioCatalog,
        engines: dict[str, ScenarioEngine],
        bundles: dict[str, ScenarioBundle],
    ) -> None:
        self.catalog = catalog
        self.engines = engines
        self.bundles = bundles
        self.enabled_order = tuple(item.scenario_id for item in catalog.scenarios if item.enabled)

    @classmethod
    def load(
        cls,
        catalog_path: Path,
        schema_path: Path,
        asset_repository: AssetRepository,
        continue_label: str,
    ) -> ScenarioRegistry:
        raw_catalog = load_json_no_duplicates(catalog_path)
        catalog = ScenarioCatalog.model_validate(raw_catalog)
        cls._validate_catalog_shape(catalog, catalog_path)

        validator = ScenarioValidator(schema_path, asset_repository)
        engines: dict[str, ScenarioEngine] = {}
        bundles: dict[str, ScenarioBundle] = {}
        seen: set[str] = set()
        for item in catalog.scenarios:
            if item.scenario_id in seen:
                raise ContentValidationError(
                    f"Duplicate scenario_id in catalog: {item.scenario_id}"
                )
            seen.add(item.scenario_id)
            scenario_path = catalog_path.parent / item.path
            if not scenario_path.exists():
                raise ContentValidationError(
                    f"Scenario file listed in catalog does not exist: {item.path}"
                )
            bundle = validator.validate_file(scenario_path)
            if bundle.scenario.id != item.scenario_id:
                raise ContentValidationError(
                    "Catalog scenario_id does not match JSON: "
                    f"{item.scenario_id} != {bundle.scenario.id}"
                )
            if item.enabled:
                bundles[item.scenario_id] = bundle
                engines[item.scenario_id] = ScenarioEngine(
                    bundle=bundle,
                    continue_label=continue_label,
                )

        if catalog.start_scenario_id not in engines:
            raise ContentValidationError(
                f"start_scenario_id is not enabled: {catalog.start_scenario_id}"
            )
        enabled_order = [item.scenario_id for item in catalog.scenarios if item.enabled]
        if len(enabled_order) != len(set(enabled_order)):
            raise ContentValidationError("Enabled scenario order contains duplicates")
        if enabled_order[0] != catalog.start_scenario_id:
            raise ContentValidationError("start_scenario_id must be first enabled scenario")
        return cls(catalog=catalog, engines=engines, bundles=bundles)

    @staticmethod
    def _validate_catalog_shape(catalog: ScenarioCatalog, catalog_path: Path) -> None:
        if not catalog.scenarios:
            raise ContentValidationError(f"Catalog has no scenarios: {catalog_path}")
        if not catalog.module_id:
            raise ContentValidationError("Catalog module_id is empty")
        ids = [item.scenario_id for item in catalog.scenarios]
        if len(ids) != len(set(ids)):
            raise ContentValidationError("Catalog contains duplicate scenario_id")
        if catalog.start_scenario_id not in ids:
            raise ContentValidationError(
                f"start_scenario_id does not exist in catalog: {catalog.start_scenario_id}"
            )

    @classmethod
    def load_json(cls, path: Path) -> ScenarioCatalog:
        with path.open("r", encoding="utf-8") as file:
            return ScenarioCatalog.model_validate(json.load(file))

    @property
    def module_id(self) -> str:
        return self.catalog.module_id

    @property
    def start_scenario_id(self) -> str:
        return self.catalog.start_scenario_id

    def get_engine(self, scenario_id: str) -> ScenarioEngine:
        try:
            return self.engines[scenario_id]
        except KeyError as exc:
            raise ContentValidationError(f"Scenario is not loaded: {scenario_id}") from exc

    def start_engine(self) -> ScenarioEngine:
        return self.get_engine(self.start_scenario_id)

    def next_scenario_id(self, scenario_id: str) -> str | None:
        try:
            index = self.enabled_order.index(scenario_id)
        except ValueError:
            return None
        next_index = index + 1
        if next_index >= len(self.enabled_order):
            return None
        return self.enabled_order[next_index]
