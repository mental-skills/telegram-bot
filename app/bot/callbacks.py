from __future__ import annotations

from app.content.models import AgeGroup


def menu_callback(action: str) -> str:
    return f"m:{action}"


def age_callback(age_group: AgeGroup) -> str:
    return f"a:{age_group}"


def reset_callback(confirm: bool) -> str:
    return "reset:yes" if confirm else "reset:no"
