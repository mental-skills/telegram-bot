from __future__ import annotations

import json
from pathlib import Path
from shutil import copyfile
from types import SimpleNamespace

import pytest

from app.api.presenter import present_training
from app.assets.repository import AssetRepository
from app.content.registry import ScenarioRegistry
from app.db.models import TrainerSession, User
from app.modules.identity import CURRENT_MODULE
from app.services.progress import CallbackPayload, ProgressScreen
from tests.test_progress import (
    advance_progress,
    complete_current_scenario,
    make_service,
)


def _runtime(registry: ScenarioRegistry) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_registry=registry,
        mini_app_visuals=SimpleNamespace(get_screen_visual=lambda *_args: None),
        ui_texts=SimpleNamespace(back_to_menu="Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"),
    )


def _two_scenario_registry(
    tmp_path: Path,
    asset_repository: AssetRepository,
) -> ScenarioRegistry:
    project_root = Path(__file__).resolve().parents[1]
    first_path = tmp_path / "first.json"
    final_path = tmp_path / "final.json"
    copyfile(project_root / "content" / "PREMATCH_GAME_REFUSAL_01.json", first_path)
    final_payload = json.loads(
        (project_root / "content" / "PARENT_RESPONSE_AFTER_VICTORY_07.json").read_text(
            encoding="utf-8"
        )
    )
    final_payload["scenario"]["id"] = "TEST_FINAL_SCENARIO"
    final_path.write_text(json.dumps(final_payload, ensure_ascii=False), encoding="utf-8")
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "module_id": "football_parent_mvp",
                "start_scenario_id": "PREMATCH_GAME_REFUSAL_01",
                "scenarios": [
                    {
                        "scenario_id": "PREMATCH_GAME_REFUSAL_01",
                        "path": "first.json",
                        "enabled": True,
                    },
                    {
                        "scenario_id": "TEST_FINAL_SCENARIO",
                        "path": "final.json",
                        "enabled": True,
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return ScenarioRegistry.load(
        catalog_path=catalog_path,
        schema_path=project_root / "content" / "scenario.schema.json",
        asset_repository=asset_repository,
        continue_label="РџСЂРѕРґРѕР»Р¶РёС‚СЊ",
    )


def test_legacy_storage_ids_share_public_module_identity() -> None:
    assert CURRENT_MODULE.public_module_id("football_parent_mvp") == (
        "parents_football_competition"
    )
    assert CURRENT_MODULE.public_module_id("football_parent_standalone") == (
        "parents_football_competition"
    )
    assert CURRENT_MODULE.route_mode("football_parent_mvp") == "full"
    assert CURRENT_MODULE.route_mode("football_parent_standalone") == "standalone"
    with pytest.raises(ValueError):
        CURRENT_MODULE.public_module_id("unknown_module")


def test_api_training_exposes_public_identity_without_storage_keys(
    scenario_registry: ScenarioRegistry,
) -> None:
    engine = scenario_registry.start_engine()
    user = User(id=1, telegram_user_id=123, age_group="9-12")
    for storage_id, route_mode in (
        ("football_parent_mvp", "full"),
        ("football_parent_standalone", "standalone"),
    ):
        session = TrainerSession(
            id=1,
            user_id=user.id,
            module_id=storage_id,
            scenario_id=engine.scenario_id,
            content_version=engine.content_version,
            current_node=engine.entry_node,
            current_revision=1,
            status="active",
        )
        response = present_training(
            ProgressScreen(
                user=user,
                trainer_session=session,
                screen=engine.render("intro", "9-12"),
            ),
            _runtime(scenario_registry),  # type: ignore[arg-type]
        )
        payload = response.model_dump()
        assert payload["module_id"] == "parents_football_competition"
        assert payload["route_mode"] == route_mode
        assert storage_id not in json.dumps(payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_progress_and_standalone_sessions_do_not_mix(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, repository = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    route = await service.start_or_continue(123)
    standalone = await service.start_or_continue_standalone(123, "PREMATCH_INSTRUCTIONS_02")
    assert route is not None and standalone is not None

    summary = await service.get_progress_summary(123)

    assert summary.current_scenario_id == "PREMATCH_GAME_REFUSAL_01"
    assert summary.completed_count == 0
    assert [session.module_id for session in repository.sessions.values()] == [
        "football_parent_mvp",
        "football_parent_standalone",
    ]


@pytest.mark.asyncio
async def test_standalone_does_not_auto_start_next_scenario(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, repository = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue_standalone(123, "PREMATCH_GAME_REFUSAL_01")
    assert progress is not None

    for option_id in ("continue", "a", "a2"):
        result = await service.advance(
            123,
            progress.trainer_session.id,
            progress.trainer_session.current_revision,
            option_id,
            route_mode="standalone",
        )
        assert result.progress_screen is not None
        progress = result.progress_screen
    for _ in range(24):
        if progress.screen.node_id == "completion":
            break
        button = progress.screen.buttons[0]
        result = await service.advance(
            123,
            progress.trainer_session.id,
            progress.trainer_session.current_revision,
            button.id,
            route_mode="standalone",
        )
        assert result.progress_screen is not None
        progress = result.progress_screen
    else:
        raise AssertionError("standalone completion was not reached")

    result = await service.advance(
        123,
        progress.trainer_session.id,
        progress.trainer_session.current_revision,
        "next",
        route_mode="standalone",
    )
    assert result.status == "standalone_boundary"
    assert len(repository.sessions) == 1


@pytest.mark.asyncio
async def test_catalog_with_two_situations_completes_without_number_seven(
    tmp_path: Path,
    asset_repository: AssetRepository,
) -> None:
    registry = _two_scenario_registry(tmp_path, asset_repository)
    service, _ = make_service(registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    assert registry.enabled_order == ("PREMATCH_GAME_REFUSAL_01", "TEST_FINAL_SCENARIO")

    progress = await complete_current_scenario(service, progress)
    progress = await advance_progress(service, progress, "next")
    assert progress.trainer_session.scenario_id == "TEST_FINAL_SCENARIO"
    progress = await complete_current_scenario(service, progress)
    result = await service.handle_callback(
        123,
        CallbackPayload(
            progress.trainer_session.id,
            progress.trainer_session.current_revision,
            "next",
        ).pack(),
    )

    assert registry.next_scenario_id("TEST_FINAL_SCENARIO") is None
    assert result.status == "ok"
    assert result.progress_screen is not None
    assert result.progress_screen.screen.node_id == "module_completion"
