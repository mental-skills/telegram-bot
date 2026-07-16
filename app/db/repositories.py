from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.models import AgeGroup
from app.db.models import (
    ChoiceEvent,
    ContentVersion,
    SessionStatus,
    TechnicalEvent,
    TrainerSession,
    User,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, telegram_user_id: int, privacy_version: str) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is not None:
            return user
        user = User(telegram_user_id=telegram_user_id, privacy_version=privacy_version)
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_age(self, user: User, age_group: AgeGroup) -> None:
        user.age_group = age_group
        user.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(UTC)
        await self.session.flush()


class ProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_session(
        self, user_id: int, module_id: str, scenario_id: str
    ) -> TrainerSession | None:
        result = await self.session.execute(
            select(TrainerSession)
            .where(
                TrainerSession.user_id == user_id,
                TrainerSession.module_id == module_id,
                TrainerSession.scenario_id == scenario_id,
                TrainerSession.status == SessionStatus.active.value,
            )
            .order_by(TrainerSession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_session_for_module(
        self,
        user_id: int,
        module_id: str,
        scenario_ids: tuple[str, ...],
    ) -> TrainerSession | None:
        result = await self.session.execute(
            select(TrainerSession)
            .where(
                TrainerSession.user_id == user_id,
                TrainerSession.module_id == module_id,
                TrainerSession.scenario_id.in_(scenario_ids),
            )
            .order_by(TrainerSession.last_activity_at.desc(), TrainerSession.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_session(self, session_id: int) -> TrainerSession | None:
        result = await self.session.execute(
            select(TrainerSession).where(TrainerSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_session_for_update(self, session_id: int) -> TrainerSession | None:
        result = await self.session.execute(
            select(TrainerSession)
            .where(TrainerSession.id == session_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_sessions_for_module(
        self,
        user_id: int,
        module_id: str,
        scenario_ids: tuple[str, ...],
    ) -> list[TrainerSession]:
        result = await self.session.execute(
            select(TrainerSession)
            .where(
                TrainerSession.user_id == user_id,
                TrainerSession.module_id == module_id,
                TrainerSession.scenario_id.in_(scenario_ids),
            )
            .order_by(TrainerSession.last_activity_at.desc(), TrainerSession.id.desc())
        )
        return list(result.scalars().all())

    async def create_session(
        self,
        user_id: int,
        module_id: str,
        scenario_id: str,
        content_version: str,
        entry_node: str,
    ) -> TrainerSession:
        attempt_no = await self._next_attempt_no(user_id, module_id, scenario_id)
        trainer_session = TrainerSession(
            user_id=user_id,
            module_id=module_id,
            scenario_id=scenario_id,
            content_version=content_version,
            current_node=entry_node,
            attempt_no=attempt_no,
        )
        self.session.add(trainer_session)
        await self.session.flush()
        return trainer_session

    async def record_system_action(
        self,
        trainer_session: TrainerSession,
        option_id: str,
        to_node: str,
        tracking_code: str | None,
        assessment: dict[str, Any] | None,
    ) -> bool:
        event = ChoiceEvent(
            session_id=trainer_session.id,
            scenario_id=trainer_session.scenario_id,
            from_node=trainer_session.current_node,
            option_id=option_id,
            to_node=to_node,
            tracking_code=tracking_code,
            assessment_json=assessment,
        )
        self.session.add(event)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return False
        trainer_session.last_activity_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def complete_session(self, trainer_session: TrainerSession) -> None:
        trainer_session.status = SessionStatus.completed.value
        trainer_session.completed_at = datetime.now(UTC)
        trainer_session.last_activity_at = datetime.now(UTC)
        trainer_session.current_revision += 1
        await self.session.flush()

    async def reset_active_sessions(self, user_id: int, module_id: str, scenario_id: str) -> None:
        await self.session.execute(
            update(TrainerSession)
            .where(
                TrainerSession.user_id == user_id,
                TrainerSession.module_id == module_id,
                TrainerSession.scenario_id == scenario_id,
                TrainerSession.status == SessionStatus.active.value,
            )
            .values(status=SessionStatus.reset.value, last_activity_at=datetime.now(UTC))
        )

    async def reset_active_sessions_for_module(self, user_id: int, module_id: str) -> None:
        await self.session.execute(
            update(TrainerSession)
            .where(
                TrainerSession.user_id == user_id,
                TrainerSession.module_id == module_id,
                TrainerSession.status == SessionStatus.active.value,
            )
            .values(status=SessionStatus.reset.value, last_activity_at=datetime.now(UTC))
        )

    async def save_choice(
        self,
        trainer_session: TrainerSession,
        from_node: str,
        option_id: str,
        to_node: str,
        tracking_code: str | None,
        assessment: dict[str, Any] | None,
    ) -> bool:
        event = ChoiceEvent(
            session_id=trainer_session.id,
            scenario_id=trainer_session.scenario_id,
            from_node=from_node,
            option_id=option_id,
            to_node=to_node,
            tracking_code=tracking_code,
            assessment_json=assessment,
        )
        self.session.add(event)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return False
        trainer_session.current_node = to_node
        trainer_session.current_revision += 1
        trainer_session.last_activity_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def _next_attempt_no(self, user_id: int, module_id: str, scenario_id: str) -> int:
        result = await self.session.execute(
            select(func.max(TrainerSession.attempt_no)).where(
                TrainerSession.user_id == user_id,
                TrainerSession.module_id == module_id,
                TrainerSession.scenario_id == scenario_id,
            )
        )
        current = result.scalar_one_or_none() or 0
        return int(current) + 1


class ContentVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_loaded_version(self, scenario_id: str, version: str, checksum: str) -> None:
        result = await self.session.execute(
            select(ContentVersion).where(
                ContentVersion.scenario_id == scenario_id, ContentVersion.version == version
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.checksum = checksum
            existing.active = True
        else:
            self.session.add(
                ContentVersion(scenario_id=scenario_id, version=version, checksum=checksum)
            )
        await self.session.flush()


class TechnicalEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        event_type: str,
        session_id: int | None = None,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            TechnicalEvent(
                event_type=event_type,
                session_id=session_id,
                error_code=error_code,
                metadata_json=metadata,
            )
        )
        await self.session.flush()
