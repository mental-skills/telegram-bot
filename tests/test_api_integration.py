from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from app.api.main import create_api_app
from app.core.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL API integration tests",
)


def integration_settings() -> Settings:
    return Settings(
        DATABASE_URL=TEST_DATABASE_URL,
        TELEGRAM_BOT_TOKEN="123456:test-token",  # noqa: S106 - test fixture
        CONTENT_DIR=PROJECT_ROOT / "content",
        ASSETS_DIR=PROJECT_ROOT / "assets",
        ENVIRONMENT="development",
        DEV_AUTH_ENABLED=True,
        DEV_AUTH_TELEGRAM_USER_ID=9876543210123,
        WEBAPP_SESSION_SECRET="integration-test-session-secret-123456",  # noqa: S106
        SESSION_COOKIE_SECURE=False,
    )


@pytest.mark.asyncio
async def test_api_route_restore_stale_and_scenario_02_boundary() -> None:
    app = create_api_app(settings=integration_settings())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        auth = await client.post("/api/v1/auth/dev")
        assert auth.status_code == 200

        age = await client.patch("/api/v1/me/age", json={"age_group": "9-12"})
        assert age.status_code == 200
        restarted = await client.post("/api/v1/training/restart")
        assert restarted.status_code == 200
        training = restarted.json()
        assert training["scenario_id"] == "PREMATCH_GAME_REFUSAL_01"
        assert "media" not in training["screen"]
        assert training["screen"]["visual"]["id"] == "premium_football_matrix"
        assert "ui_dialogue_choice" not in str(training)

        first_revision = training["revision"]
        first = await client.post(
            f"/api/v1/training/sessions/{training['session_id']}/transitions",
            json={"revision": first_revision, "option_id": "continue"},
        )
        assert first.status_code == 200
        training = first.json()["training"]

        stale = await client.post(
            f"/api/v1/training/sessions/{training['session_id']}/transitions",
            json={"revision": first_revision, "option_id": "a"},
        )
        assert stale.status_code == 409
        assert stale.json()["detail"] == "stale"

        for option_id in ("a", "a2", "continue", "continue", "continue", "continue"):
            response = await client.post(
                f"/api/v1/training/sessions/{training['session_id']}/transitions",
                json={"revision": training["revision"], "option_id": option_id},
            )
            assert response.status_code == 200, response.text
            training = response.json()["training"]
        assert training["screen"]["type"] == "completion"
        assert training["screen"]["visual"]["id"] == "premium_completion_network"
        assert "ui_achievement" not in str(training)

        next_response = await client.post(
            f"/api/v1/training/sessions/{training['session_id']}/transitions",
            json={"revision": training["revision"], "option_id": "next"},
        )
        assert next_response.status_code == 200
        scenario_02 = next_response.json()["training"]
        assert scenario_02["scenario_id"] == "PREMATCH_INSTRUCTIONS_02"
        assert scenario_02["screen"]["is_mini_app_boundary"] is True
        assert all(action["kind"] != "continue" for action in scenario_02["screen"]["actions"])

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as restored_client:
        await restored_client.post("/api/v1/auth/dev")
        restored = await restored_client.get("/api/v1/training/current")
        assert restored.status_code == 200
        assert restored.json()["scenario_id"] == "PREMATCH_INSTRUCTIONS_02"
        assert restored.json()["screen"]["is_mini_app_boundary"] is True
