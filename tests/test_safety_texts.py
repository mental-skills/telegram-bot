from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

BANNED = (
    "%",
    "процент",
    "диагноз",
    "контролирующий родитель",
    "тревожный родитель",
    "неправильный родитель",
    "тип —",
    "тип -",
)


def iter_user_strings(value: object, path: str = "") -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"assessment", "methodology", "dimensions"}:
                continue
            yield from iter_user_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_user_strings(item, f"{path}[{index}]")
    elif isinstance(value, str):
        yield value


def test_no_diagnostic_percentages_or_banned_labels() -> None:
    scenario = json.loads(Path("content/PREMATCH_INSTRUCTIONS_02.json").read_text(encoding="utf-8"))
    texts = list(iter_user_strings(scenario))
    hits = [text for text in texts if any(term in text.lower() for term in BANNED)]
    assert hits == []
