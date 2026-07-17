from __future__ import annotations

from app.api.schemas import (
    ActionResponse,
    MiniAppVisualResponse,
    ProgressResponse,
    ScreenResponse,
    SituationResponse,
    TrainingResponse,
)
from app.application import ApplicationRuntime
from app.content.models import SYSTEM_MAIN_MENU, SYSTEM_NEXT_SCENARIO
from app.engine.types import ScenarioScreen, ScreenButton
from app.mini_app.visuals import MiniAppVisualAsset
from app.modules.identity import CURRENT_MODULE, ModuleIdentityError
from app.services.progress import ProgressScreen, ProgressSummary

MODULE_COMPLETION_NODE_ID = "module_completion"


def present_training(
    progress: ProgressScreen,
    runtime: ApplicationRuntime,
) -> TrainingResponse:
    screen = progress.screen
    module_identity = getattr(runtime, "module_identity", CURRENT_MODULE)
    try:
        public_module_id = module_identity.public_module_id(progress.trainer_session.module_id)
        route_mode = module_identity.route_mode(progress.trainer_session.module_id)
    except ModuleIdentityError as exc:
        raise ValueError("Unknown session module identity") from exc
    visual_asset = runtime.mini_app_visuals.get_screen_visual(
        screen.scenario_id,
        screen.node_id,
        screen.node_type,
    )
    visual = present_visual(visual_asset) if visual_asset else None

    is_module_completion = (
        screen.node_id == MODULE_COMPLETION_NODE_ID
        and route_mode == "full"
        and progress.trainer_session.module_id == runtime.scenario_registry.module_id
    )
    actions = (
        _module_completion_actions(runtime)
        if is_module_completion
        else _screen_actions(screen)
    )
    bundle = runtime.scenario_registry.bundles[screen.scenario_id]
    return TrainingResponse(
        module_id=public_module_id,
        route_mode=route_mode,
        scenario_id=screen.scenario_id,
        content_version=screen.content_version,
        scenario_title=bundle.scenario.title,
        session_id=progress.trainer_session.id,
        revision=progress.trainer_session.current_revision,
        status=progress.trainer_session.status,
        screen=ScreenResponse(
            node_id=screen.node_id,
            type=screen.node_type,
            title=screen.title,
            text=screen.text,
            quote=screen.quote,
            visual=visual,
            actions=actions,
            is_completion=screen.is_completion,
            is_mini_app_boundary=False,
            stage=_screen_stage(screen),
        ),
    )


def present_visual(asset: MiniAppVisualAsset) -> MiniAppVisualResponse:
    return MiniAppVisualResponse(
        id=asset.id,
        url=f"/api/v1/mini-app/assets/{asset.id}",
        alt=asset.alt,
        kind=asset.kind,
    )


def present_progress(summary: ProgressSummary) -> ProgressResponse:
    return ProgressResponse(
        module_id=CURRENT_MODULE.canonical_module_id,
        route_mode="full",
        available_count=summary.available_count,
        completed_count=summary.completed_count,
        current_scenario_id=summary.current_scenario_id,
        situations=[
            SituationResponse(
                module_id=CURRENT_MODULE.canonical_module_id,
                route_mode="full",
                scenario_id=item.scenario_id,
                title=item.title,
                estimated_minutes=item.estimated_minutes,
                status=item.status,
                attempt_no=item.attempt_no,
            )
            for item in summary.situations
        ],
    )


def _screen_actions(screen: ScenarioScreen) -> list[ActionResponse]:
    return [_present_button(screen, button) for button in screen.buttons]


def _present_button(screen: ScenarioScreen, button: ScreenButton) -> ActionResponse:
    if button.next_node == SYSTEM_MAIN_MENU:
        kind = "main_menu"
    elif button.next_node == SYSTEM_NEXT_SCENARIO:
        kind = "next_scenario"
    elif screen.is_completion and button.id == "repeat":
        kind = "repeat"
    elif screen.node_type == "choice":
        kind = "choice"
    else:
        kind = "continue"
    return ActionResponse(id=button.id, label=button.label, kind=kind)


def _module_completion_actions(runtime: ApplicationRuntime) -> list[ActionResponse]:
    actions = [
        ActionResponse(
            id=f"open_{scenario_id.lower()}",
            label=bundle.scenario.short_title,
            kind="open_scenario",
            scenario_id=scenario_id,
        )
        for scenario_id, bundle in runtime.scenario_registry.bundles.items()
    ]
    actions.append(
        ActionResponse(
            id="home",
            label=runtime.ui_texts.back_to_menu,
            kind="main_menu",
        )
    )
    return actions


def _screen_stage(screen: ScenarioScreen) -> int:
    if screen.node_type == "outcome":
        return 4 if screen.node_id.endswith("_repeated") else 3
    if screen.node_type == "tool":
        return 6 if screen.node_id == "summary_main" else 7
    return {
        "info": 1,
        "choice": 2,
        "advice": 5,
        "completion": 8,
        "emergency": 7,
    }[screen.node_type]
