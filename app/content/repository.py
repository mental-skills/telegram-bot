from __future__ import annotations

import json
from pathlib import Path

from app.assets.repository import AssetRepository
from app.content.models import ScenarioBundle, UiTexts
from app.content.validator import ScenarioValidator


class ContentRepository:
    def __init__(
        self,
        scenario_path: Path,
        schema_path: Path,
        ui_texts_path: Path,
        asset_repository: AssetRepository,
    ) -> None:
        self.scenario_path = scenario_path
        self.schema_path = schema_path
        self.ui_texts_path = ui_texts_path
        self.asset_repository = asset_repository
        self._bundle: ScenarioBundle | None = None
        self._ui_texts: UiTexts | None = None

    def load(self) -> ScenarioBundle:
        validator = ScenarioValidator(self.schema_path, self.asset_repository)
        self._bundle = validator.validate_file(self.scenario_path)
        return self._bundle

    def get_bundle(self) -> ScenarioBundle:
        if self._bundle is None:
            return self.load()
        return self._bundle

    def get_ui_texts(self) -> UiTexts:
        if self._ui_texts is None:
            with self.ui_texts_path.open("r", encoding="utf-8") as file:
                self._ui_texts = UiTexts.model_validate(json.load(file))
        return self._ui_texts
