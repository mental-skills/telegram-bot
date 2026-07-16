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

    intro = repository.get_screen_visual("PREMATCH_GAME_REFUSAL_01", "intro", "info")
    choice = repository.get_screen_visual(
        "PREMATCH_GAME_REFUSAL_01", "start_choice", "choice"
    )
    outcome = repository.get_screen_visual(
        "PREMATCH_GAME_REFUSAL_01", "a1_outcome", "outcome"
    )

    assert intro is not None and intro.id == "premium_football_matrix"
    assert choice is None
    assert outcome is not None and outcome.id == "premium_consequence_signal"
    assert all("assets/mini_app" in asset.path.as_posix() for asset in (intro, outcome))
