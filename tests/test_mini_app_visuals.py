from pathlib import Path

from app.mini_app.visuals import MiniAppVisualRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mini_app_visual_map_never_resolves_telegram_runtime_cards() -> None:
    repository = MiniAppVisualRepository(
        manifest_path=PROJECT_ROOT / "assets" / "mini_app" / "manifest.json",
        presentation_path=PROJECT_ROOT / "content" / "mini_app_visuals.json",
        project_root=PROJECT_ROOT,
    )
    repository.load()

    scenario_ids = (
        "PREMATCH_GAME_REFUSAL_01",
        "PREMATCH_INSTRUCTIONS_02",
        "CHILD_ERROR_LOOKS_AT_PARENT_03",
        "CHILD_LEFT_ON_BENCH_04",
        "DISPUTED_REFEREE_DECISION_05",
        "CHILD_SILENT_AFTER_DEFEAT_06",
        "PARENT_RESPONSE_AFTER_VICTORY_07",
    )
    for scenario_id in scenario_ids:
        intro = repository.get_screen_visual(scenario_id, "intro", "info")
        choice = repository.get_screen_visual(scenario_id, "start_choice", "choice")
        outcome = repository.get_screen_visual(scenario_id, "a1_now", "outcome")
        assert intro is not None and intro.id == "premium_football_matrix"
        assert choice is None
        assert outcome is not None and outcome.id == "premium_consequence_signal"
        assert all("assets/mini_app" in asset.path.as_posix() for asset in (intro, outcome))
