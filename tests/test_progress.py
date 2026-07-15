from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.content.models import AgeGroup
from app.db.models import TrainerSession, User
from app.engine.engine import ScenarioEngine
from app.services.progress import CallbackPayload, ProgressService


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

    async def get_active_session(self, user_id: int, scenario_id: str) -> TrainerSession | None:
        for session in self.sessions.values():
            if (
                session.user_id == user_id
                and session.scenario_id == scenario_id
                and session.status == "active"
            ):
                return session
        return None

    async def get_session(self, session_id: int) -> TrainerSession | None:
        return self.sessions.get(session_id)

    async def create_session(
        self,
        user_id: int,
        scenario_id: str,
        content_version: str,
        entry_node: str,
    ) -> TrainerSession:
        session = TrainerSession(
            id=self.next_id,
            user_id=user_id,
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
        trainer_session.current_node = to_node
        trainer_session.current_revision += 1
        return True

    async def complete_session(self, trainer_session: TrainerSession) -> None:
        trainer_session.status = "completed"
        trainer_session.current_revision += 1

    async def reset_active_sessions(self, user_id: int, scenario_id: str) -> None:
        for session in self.sessions.values():
            if session.user_id == user_id and session.scenario_id == scenario_id:
                session.status = "reset"


def make_service(engine: ScenarioEngine) -> tuple[ProgressService, FakeProgressRepository]:
    user_repo = FakeUserRepository()
    progress_repo = FakeProgressRepository()
    service = ProgressService(user_repo, progress_repo, engine, privacy_version="test")
    return service, progress_repo


@pytest.mark.asyncio
async def test_save_and_restore_progress(engine: ScenarioEngine) -> None:
    service, _ = make_service(engine)
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


@pytest.mark.asyncio
async def test_stale_callback_is_ignored(engine: ScenarioEngine) -> None:
    service, _ = make_service(engine)
    await service.set_age(123, "9-12")
    progress = await service.start_or_continue(123)
    assert progress is not None
    payload = CallbackPayload(progress.trainer_session.id, 999, "continue")
    result = await service.handle_callback(123, payload.pack())
    assert result.status == "stale"


@pytest.mark.asyncio
async def test_duplicate_callback_is_reported(engine: ScenarioEngine) -> None:
    service, progress_repo = make_service(engine)
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
async def test_restart_creates_new_attempt(engine: ScenarioEngine) -> None:
    service, _ = make_service(engine)
    await service.set_age(123, "9-12")
    first = await service.start_or_continue(123)
    second = await service.restart(123)
    assert first is not None and second is not None
    assert first.trainer_session.id != second.trainer_session.id
    assert second.trainer_session.current_node == engine.entry_node
