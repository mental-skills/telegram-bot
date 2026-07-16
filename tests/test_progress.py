from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.content.models import AgeGroup
from app.content.registry import ScenarioRegistry
from app.db.models import TrainerSession, User
from app.services.progress import (
    STANDALONE_MODULE_ID,
    CallbackPayload,
    ProgressScreen,
    ProgressService,
)


@dataclass
class FakeUserRepository:
    user: User = field(default_factory=lambda: User(id=1, telegram_user_id=123))

    async def get_or_create(self, telegram_user_id: int, privacy_version: str) -> User:
        self.user.telegram_user_id = telegram_user_id
        self.user.privacy_version = privacy_version
        return self.user

    async def set_age(self, user: User, age_group: AgeGroup) -> None:
        user.age_group = age_group


@dataclass
class FakeProgressRepository:
    sessions: dict[int, TrainerSession] = field(default_factory=dict)
    next_id: int = 1
    duplicate: bool = False

    choices: set[tuple[int, str, str]] = field(default_factory=set)

    async def get_active_session(
        self, user_id: int, module_id: str, scenario_id: str
    ) -> TrainerSession | None:
        for session in self.sessions.values():
            if (
                session.user_id == user_id
                and session.module_id == module_id
                and session.scenario_id == scenario_id
                and session.status == "active"
            ):
                return session
        return None

    async def get_latest_session_for_module(
        self,
        user_id: int,
        module_id: str,
        scenario_ids: tuple[str, ...],
    ) -> TrainerSession | None:
        sessions = [
            session
            for session in self.sessions.values()
            if session.user_id == user_id
            and session.module_id == module_id
            and session.scenario_id in scenario_ids
        ]
        if not sessions:
            return None
        return max(sessions, key=lambda session: session.id)

    async def get_session(self, session_id: int) -> TrainerSession | None:
        return self.sessions.get(session_id)

    async def get_session_for_update(self, session_id: int) -> TrainerSession | None:
        return self.sessions.get(session_id)

    async def list_sessions_for_module(
        self,
        user_id: int,
        module_id: str,
        scenario_ids: tuple[str, ...],
    ) -> list[TrainerSession]:
        return sorted(
            [
                session
                for session in self.sessions.values()
                if session.user_id == user_id
                and session.module_id == module_id
                and session.scenario_id in scenario_ids
            ],
            key=lambda session: session.id,
            reverse=True,
        )

    async def create_session(
        self,
        user_id: int,
        module_id: str,
        scenario_id: str,
        content_version: str,
        entry_node: str,
    ) -> TrainerSession:
        session = TrainerSession(
            id=self.next_id,
            user_id=user_id,
            module_id=module_id,
            scenario_id=scenario_id,
            content_version=content_version,
            current_node=entry_node,
            current_revision=1,
            attempt_no=self.next_id,
            status="active",
        )
        self.sessions[session.id] = session
        self.next_id += 1
        return session

    async def save_choice(
        self,
        trainer_session: TrainerSession,
        from_node: str,
        option_id: str,
        to_node: str,
        tracking_code: str | None,
        assessment: dict[str, object] | None,
    ) -> bool:
        if self.duplicate:
            return False
        key = (trainer_session.id, from_node, option_id)
        if key in self.choices:
            return False
        self.choices.add(key)
        trainer_session.current_node = to_node
        trainer_session.current_revision += 1
        return True

    async def record_system_action(
        self,
        trainer_session: TrainerSession,
        option_id: str,
        to_node: str,
        tracking_code: str | None,
        assessment: dict[str, object] | None,
    ) -> bool:
        if self.duplicate:
            return False
        key = (trainer_session.id, trainer_session.current_node, option_id)
        if key in self.choices:
            return False
        self.choices.add(key)
        return True

    async def complete_session(self, trainer_session: TrainerSession) -> None:
        trainer_session.status = "completed"
        trainer_session.current_revision += 1

    async def reset_active_sessions(self, user_id: int, module_id: str, scenario_id: str) -> None:
        for session in self.sessions.values():
            if (
                session.user_id == user_id
                and session.module_id == module_id
                and session.scenario_id == scenario_id
            ):
                session.status = "reset"

    async def reset_active_sessions_for_module(self, user_id: int, module_id: str) -> None:
        for session in self.sessions.values():
            if session.user_id == user_id and session.module_id == module_id:
                session.status = "reset"


def make_service(registry: ScenarioRegistry) -> tuple[ProgressService, FakeProgressRepository]:
    user_repo = FakeUserRepository()
    progress_repo = FakeProgressRepository()
    service = ProgressService(user_repo, progress_repo, registry, privacy_version="test")
    return service, progress_repo


async def advance_progress(
    service: ProgressService,
    progress: ProgressScreen,
    option_id: str,
) -> ProgressScreen:
    payload = CallbackPayload(
        progress.trainer_session.id,
        progress.trainer_session.current_revision,
        option_id,
    )
    result = await service.handle_callback(123, payload.pack())
    assert result.status == "ok"
    assert result.progress_screen is not None
    return result.progress_screen


async def complete_current_scenario(
    service: ProgressService,
    progress: ProgressScreen,
) -> ProgressScreen:
    for option_id in ("continue", "a", "a2"):
        progress = await advance_progress(service, progress, option_id)
    for _ in range(24):
        if progress.screen.node_id == "completion":
            break
        assert progress.screen.buttons
        progress = await advance_progress(service, progress, progress.screen.buttons[0].id)
    else:
        raise AssertionError(f"completion not reached: {progress.screen.scenario_id}")
    assert progress.trainer_session.status == "completed"
    return progress


async def complete_scenario_01(service: ProgressService) -> ProgressScreen:
    progress = await service.start_or_continue(123)
    assert progress is not None
    return await complete_current_scenario(service, progress)


@pytest.mark.asyncio
async def test_save_and_restore_progress(scenario_registry: ScenarioRegistry) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    payload = CallbackPayload(
        progress.trainer_session.id, progress.trainer_session.current_revision, "continue"
    )
    result = await service.handle_callback(123, payload.pack())
    assert result.status == "ok"
    restored = await service.start_or_continue(123)
    assert restored is not None
    assert restored.trainer_session.current_node == "start_choice"
    assert restored.trainer_session.scenario_id == "PREMATCH_GAME_REFUSAL_01"


@pytest.mark.asyncio
async def test_stale_callback_is_ignored(scenario_registry: ScenarioRegistry) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    payload = CallbackPayload(progress.trainer_session.id, 999, "continue")
    result = await service.handle_callback(123, payload.pack())
    assert result.status == "stale"


@pytest.mark.asyncio
async def test_duplicate_callback_is_reported(scenario_registry: ScenarioRegistry) -> None:
    service, progress_repo = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    progress_repo.duplicate = True
    payload = CallbackPayload(
        progress.trainer_session.id, progress.trainer_session.current_revision, "continue"
    )
    result = await service.handle_callback(123, payload.pack())
    assert result.status == "duplicate"


@pytest.mark.asyncio
async def test_restart_creates_new_attempt(scenario_registry: ScenarioRegistry) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    first = await service.start_or_continue(123)
    second = await service.restart(123)
    assert first is not None and second is not None
    assert first.trainer_session.id != second.trainer_session.id
    assert second.trainer_session.current_node == scenario_registry.start_engine().entry_node


@pytest.mark.asyncio
async def test_full_route_starts_with_scenario_01(scenario_registry: ScenarioRegistry) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    assert progress.trainer_session.module_id == "football_parent_mvp"
    assert progress.trainer_session.scenario_id == "PREMATCH_GAME_REFUSAL_01"
    assert progress.screen.node_id == "intro"


@pytest.mark.asyncio
async def test_completion_01_is_restored_before_next(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    completed = await complete_scenario_01(service)
    restored = await service.start_or_continue(123)
    assert restored is not None
    assert restored.trainer_session.id == completed.trainer_session.id
    assert restored.screen.node_id == "completion"


@pytest.mark.asyncio
async def test_next_scenario_creates_scenario_02_session(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    completed = await complete_scenario_01(service)
    payload = CallbackPayload(
        completed.trainer_session.id,
        completed.trainer_session.current_revision,
        "next",
    )
    result = await service.handle_callback(123, payload.pack())
    assert result.status == "ok"
    assert result.progress_screen is not None
    assert result.progress_screen.trainer_session.scenario_id == "PREMATCH_INSTRUCTIONS_02"
    assert result.progress_screen.trainer_session.module_id == "football_parent_mvp"
    assert result.progress_screen.screen.node_id == "intro"


@pytest.mark.asyncio
async def test_repeated_next_scenario_callback_is_duplicate(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, progress_repo = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    completed = await complete_scenario_01(service)
    payload = CallbackPayload(
        completed.trainer_session.id,
        completed.trainer_session.current_revision,
        "next",
    )
    first = await service.handle_callback(123, payload.pack())
    second = await service.handle_callback(123, payload.pack())
    assert first.status == "ok"
    assert second.status == "duplicate"
    scenario2_sessions = [
        session
        for session in progress_repo.sessions.values()
        if session.scenario_id == "PREMATCH_INSTRUCTIONS_02"
        and session.module_id == "football_parent_mvp"
    ]
    assert len(scenario2_sessions) == 1


@pytest.mark.asyncio
async def test_repeated_repeat_callback_is_duplicate(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, progress_repo = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    completed = await complete_scenario_01(service)
    payload = CallbackPayload(
        completed.trainer_session.id,
        completed.trainer_session.current_revision,
        "repeat",
    )
    first = await service.handle_callback(123, payload.pack())
    second = await service.handle_callback(123, payload.pack())
    assert first.status == "ok"
    assert second.status == "duplicate"
    scenario1_sessions = [
        session
        for session in progress_repo.sessions.values()
        if session.scenario_id == "PREMATCH_GAME_REFUSAL_01"
        and session.module_id == "football_parent_mvp"
    ]
    assert len(scenario1_sessions) == 2


@pytest.mark.asyncio
async def test_standalone_scenario_02_does_not_mix_with_route(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, progress_repo = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    route = await service.start_or_continue(123)
    standalone = await service.start_or_continue_standalone(123, "PREMATCH_INSTRUCTIONS_02")
    assert route is not None and standalone is not None
    assert route.trainer_session.module_id == "football_parent_mvp"
    assert standalone.trainer_session.module_id == STANDALONE_MODULE_ID
    assert standalone.trainer_session.scenario_id == "PREMATCH_INSTRUCTIONS_02"
    assert len(progress_repo.sessions) == 2


@pytest.mark.asyncio
async def test_restart_scenario_02_keeps_route_progress(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, progress_repo = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    route = await service.start_or_continue(123)
    standalone = await service.start_or_continue_standalone(123, "PREMATCH_INSTRUCTIONS_02")
    restarted = await service.restart_scenario(123, "PREMATCH_INSTRUCTIONS_02")
    assert route is not None and standalone is not None and restarted is not None
    assert route.trainer_session.status == "active"
    assert standalone.trainer_session.status == "reset"
    assert restarted.trainer_session.module_id == STANDALONE_MODULE_ID
    assert len(progress_repo.sessions) == 3


@pytest.mark.asyncio
async def test_engine_is_selected_by_session_scenario_id(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "13-16")
    standalone = await service.start_or_continue_standalone(123, "PREMATCH_INSTRUCTIONS_02")
    assert standalone is not None
    assert standalone.screen.scenario_id == "PREMATCH_INSTRUCTIONS_02"
    assert standalone.screen.title == "Ситуация 2 из 7. Последние инструкции перед стартом"


@pytest.mark.asyncio
async def test_progress_summary_contains_only_enabled_situations(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    await service.start_or_continue(123)
    summary = await service.get_progress_summary(123)
    assert summary.available_count == 7
    assert summary.completed_count == 0
    assert [item.scenario_id for item in summary.situations] == [
        "PREMATCH_GAME_REFUSAL_01",
        "PREMATCH_INSTRUCTIONS_02",
        "CHILD_ERROR_LOOKS_AT_PARENT_03",
        "CHILD_LEFT_ON_BENCH_04",
        "DISPUTED_REFEREE_DECISION_05",
        "CHILD_SILENT_AFTER_DEFEAT_06",
        "PARENT_RESPONSE_AFTER_VICTORY_07",
    ]


@pytest.mark.asyncio
async def test_full_route_reaches_all_seven_and_module_completion(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    visited: list[str] = []
    for expected_id in scenario_registry.enabled_order:
        assert progress.trainer_session.scenario_id == expected_id
        visited.append(expected_id)
        progress = await complete_current_scenario(service, progress)
        progress = await advance_progress(service, progress, "next")
    assert tuple(visited) == scenario_registry.enabled_order
    assert progress.screen.node_id == "module_completion"
    summary = await service.get_progress_summary(123)
    assert summary.completed_count == 7


@pytest.mark.asyncio
async def test_every_situation_can_start_standalone_without_route_progress(
    scenario_registry: ScenarioRegistry,
) -> None:
    service, _ = make_service(scenario_registry)
    await service.set_age(123, "9-12")
    for scenario_id in scenario_registry.enabled_order:
        standalone = await service.start_or_continue_standalone(123, scenario_id)
        assert standalone is not None
        assert standalone.trainer_session.module_id == STANDALONE_MODULE_ID
        assert standalone.trainer_session.scenario_id == scenario_id
    summary = await service.get_progress_summary(123)
    assert summary.completed_count == 0
