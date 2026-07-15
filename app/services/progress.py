from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.content.models import SYSTEM_MAIN_MENU, SYSTEM_NEXT_SCENARIO, AgeGroup
from app.core.errors import ScenarioStateError
from app.db.models import TrainerSession, User
from app.engine.engine import ScenarioEngine
from app.engine.types import ScenarioScreen

CallbackStatus = Literal["ok", "stale", "duplicate", "main_menu", "next_unavailable"]


class UserRepositoryProtocol(Protocol):
    async def get_or_create(self, telegram_user_id: int, privacy_version: str) -> User: ...

    async def set_age(self, user: User, age_group: AgeGroup) -> None: ...


class ProgressRepositoryProtocol(Protocol):
    async def get_active_session(self, user_id: int, scenario_id: str) -> TrainerSession | None: ...

    async def get_session(self, session_id: int) -> TrainerSession | None: ...

    async def create_session(
        self,
        user_id: int,
        scenario_id: str,
        content_version: str,
        entry_node: str,
    ) -> TrainerSession: ...

    async def save_choice(
        self,
        trainer_session: TrainerSession,
        from_node: str,
        option_id: str,
        to_node: str,
        tracking_code: str | None,
        assessment: dict[str, object] | None,
    ) -> bool: ...

    async def complete_session(self, trainer_session: TrainerSession) -> None: ...

    async def reset_active_sessions(self, user_id: int, scenario_id: str) -> None: ...


@dataclass(frozen=True)
class CallbackPayload:
    session_id: int
    revision: int
    option_id: str

    def pack(self) -> str:
        return f"s:{self.session_id}:r:{self.revision}:o:{self.option_id}"

    @classmethod
    def unpack(cls, raw: str) -> CallbackPayload:
        parts = raw.split(":")
        if len(parts) != 6 or parts[0] != "s" or parts[2] != "r" or parts[4] != "o":
            raise ScenarioStateError("Invalid callback payload")
        return cls(session_id=int(parts[1]), revision=int(parts[3]), option_id=parts[5])


@dataclass(frozen=True)
class ProgressScreen:
    user: User
    trainer_session: TrainerSession
    screen: ScenarioScreen


@dataclass(frozen=True)
class CallbackResult:
    status: CallbackStatus
    progress_screen: ProgressScreen | None = None


class ProgressService:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol,
        progress_repository: ProgressRepositoryProtocol,
        engine: ScenarioEngine,
        privacy_version: str,
    ) -> None:
        self.user_repository = user_repository
        self.progress_repository = progress_repository
        self.engine = engine
        self.privacy_version = privacy_version

    async def get_or_create_user(self, telegram_user_id: int) -> User:
        return await self.user_repository.get_or_create(telegram_user_id, self.privacy_version)

    async def set_age(self, telegram_user_id: int, age_group: AgeGroup) -> User:
        user = await self.get_or_create_user(telegram_user_id)
        await self.user_repository.set_age(user, age_group)
        return user

    async def start_or_continue(self, telegram_user_id: int) -> ProgressScreen | None:
        user = await self.get_or_create_user(telegram_user_id)
        if user.age_group is None:
            return None
        trainer_session = await self.progress_repository.get_active_session(
            user.id, self.engine.scenario_id
        )
        if trainer_session is None:
            trainer_session = await self.progress_repository.create_session(
                user_id=user.id,
                scenario_id=self.engine.scenario_id,
                content_version=self.engine.content_version,
                entry_node=self.engine.entry_node,
            )
        screen = self.engine.render(trainer_session.current_node, user.age_group)  # type: ignore[arg-type]
        return ProgressScreen(user=user, trainer_session=trainer_session, screen=screen)

    async def restart(self, telegram_user_id: int) -> ProgressScreen | None:
        user = await self.get_or_create_user(telegram_user_id)
        if user.age_group is None:
            return None
        await self.progress_repository.reset_active_sessions(user.id, self.engine.scenario_id)
        trainer_session = await self.progress_repository.create_session(
            user_id=user.id,
            scenario_id=self.engine.scenario_id,
            content_version=self.engine.content_version,
            entry_node=self.engine.entry_node,
        )
        screen = self.engine.render(self.engine.entry_node, user.age_group)  # type: ignore[arg-type]
        return ProgressScreen(user=user, trainer_session=trainer_session, screen=screen)

    async def handle_callback(self, telegram_user_id: int, raw_callback: str) -> CallbackResult:
        payload = CallbackPayload.unpack(raw_callback)
        user = await self.get_or_create_user(telegram_user_id)
        if user.age_group is None:
            return CallbackResult(status="stale")

        trainer_session = await self.progress_repository.get_session(payload.session_id)
        if trainer_session is None or trainer_session.user_id != user.id:
            return CallbackResult(status="stale")
        if trainer_session.current_revision != payload.revision:
            return CallbackResult(status="stale")

        transition = self.engine.transition(trainer_session.current_node, payload.option_id)
        if transition.to_node == SYSTEM_MAIN_MENU:
            return CallbackResult(status="main_menu")
        if transition.to_node == SYSTEM_NEXT_SCENARIO:
            return CallbackResult(status="next_unavailable")
        if (
            trainer_session.current_node == "completion"
            and transition.to_node == self.engine.entry_node
        ):
            new_session = await self.progress_repository.create_session(
                user_id=user.id,
                scenario_id=self.engine.scenario_id,
                content_version=self.engine.content_version,
                entry_node=self.engine.entry_node,
            )
            screen = self.engine.render(self.engine.entry_node, user.age_group)  # type: ignore[arg-type]
            return CallbackResult(
                status="ok",
                progress_screen=ProgressScreen(
                    user=user, trainer_session=new_session, screen=screen
                ),
            )

        saved = await self.progress_repository.save_choice(
            trainer_session=trainer_session,
            from_node=transition.from_node,
            option_id=transition.option_id,
            to_node=transition.to_node,
            tracking_code=transition.tracking_code,
            assessment=transition.assessment,
        )
        if not saved:
            return CallbackResult(status="duplicate")

        screen = self.engine.render(transition.to_node, user.age_group)  # type: ignore[arg-type]
        if screen.is_completion:
            await self.progress_repository.complete_session(trainer_session)
        return CallbackResult(
            status="ok",
            progress_screen=ProgressScreen(
                user=user, trainer_session=trainer_session, screen=screen
            ),
        )

    async def reset_user_progress(self, telegram_user_id: int) -> None:
        user = await self.get_or_create_user(telegram_user_id)
        await self.progress_repository.reset_active_sessions(user.id, self.engine.scenario_id)
