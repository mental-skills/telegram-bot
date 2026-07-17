from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "content" / "mental-skills-all-7-situations-approved-v1.md"
CONTENT = ROOT / "content"

SCENARIO_META = {
    1: ("PREMATCH_GAME_REFUSAL_01", "before_match", "ui_dialogue_choice"),
    2: ("PREMATCH_INSTRUCTIONS_02", "before_match", "ui_dialogue_choice"),
    3: ("CHILD_ERROR_LOOKS_AT_PARENT_03", "during_match", "ui_dialogue_choice"),
    4: ("CHILD_LEFT_ON_BENCH_04", "during_match", "ui_dialogue_choice"),
    5: ("DISPUTED_REFEREE_DECISION_05", "during_match", "ui_dialogue_choice"),
    6: ("CHILD_SILENT_AFTER_DEFEAT_06", "after_match", "ui_dialogue_choice"),
    7: ("PARENT_RESPONSE_AFTER_VICTORY_07", "after_match", "ui_dialogue_choice"),
}
CYR_TO_LATIN = {"А": "a", "Б": "b", "В": "c", "Г": "d"}
AGES = {"6–8 лет": "6-8", "9–12 лет": "9-12", "13–16 лет": "13-16"}
SYSTEM_MAIN_MENU = "__MAIN_MENU__"
SYSTEM_NEXT_SCENARIO = "__NEXT_SCENARIO__"


@dataclass(frozen=True)
class Block:
    title: str
    body: list[str]


def _plain_inline(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    return value


def _plain_text(lines: list[str]) -> str:
    rendered: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("> "):
            line = line[2:]
        if line.startswith("- "):
            line = f"• {line[2:]}"
        rendered.append(_plain_inline(line))
    while rendered and not rendered[0]:
        rendered.pop(0)
    while rendered and not rendered[-1]:
        rendered.pop()
    compact: list[str] = []
    for line in rendered:
        if not line and compact and not compact[-1]:
            continue
        compact.append(line)
    return "\n".join(compact)


def _blocks(lines: list[str], level: int) -> list[Block]:
    marker = "#" * level + " "
    indices = [index for index, line in enumerate(lines) if line.startswith(marker)]
    result: list[Block] = []
    for position, index in enumerate(indices):
        end = indices[position + 1] if position + 1 < len(indices) else len(lines)
        result.append(Block(lines[index][len(marker) :].strip(), lines[index + 1 : end]))
    return result


def _block(blocks: list[Block], title: str) -> Block:
    return next(item for item in blocks if item.title == title)


def _subsections(block: Block, level: int) -> list[Block]:
    return _blocks(block.body, level)


def _before_subheading(block: Block, level: int) -> list[str]:
    marker = "#" * level + " "
    end = next(
        (index for index, line in enumerate(block.body) if line.startswith(marker)),
        len(block.body),
    )
    return block.body[:end]


def _age_text(block: Block) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _subsections(block, 3):
        age = AGES.get(item.title)
        if age:
            result[age] = _plain_text(item.body)
    if set(result) != {"6-8", "9-12", "13-16"}:
        raise ValueError(f"Incomplete age text in {block.title}: {sorted(result)}")
    return result


def _choice_labels(block: Block) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in block.body:
        match = re.match(r"^- \*\*Вариант ([А-Г]):\*\*\s*(.+)$", line)
        if match:
            result[match.group(1)] = _plain_inline(match.group(2))
    if set(result) != set(CYR_TO_LATIN):
        raise ValueError(f"Expected four choices, found {result}")
    return result


def _branch_parts(block: Block) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _subsections(block, 4):
        result[item.title] = _plain_text(item.body)
    required = {
        "Что может произойти сейчас",
        "Если такая реакция повторяется",
        "Практический совет",
    }
    if not required.issubset(result):
        raise ValueError(f"Incomplete branch {block.title}: {sorted(result)}")
    ready = next(
        (text for title, text in result.items() if "фраз" in title.lower()),
        "",
    )
    if not ready:
        raise ValueError(f"Missing ready phrase in {block.title}")
    return {
        "now": result["Что может произойти сейчас"],
        "repeated": result["Если такая реакция повторяется"],
        "advice": result["Практический совет"],
        "quote": ready,
    }


def _media(asset_id: str, presentation: str = "card") -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "mode": "photo",
        "show_once_per_session": False,
        "presentation": presentation,
        "caption_strategy": "auto",
    }


def _tool_chunks(block: Block) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    preamble = _plain_text(_before_subheading(block, 3))
    if preamble:
        chunks.append((block.title, preamble))
    for subsection in _subsections(block, 3):
        chunks.append((subsection.title, _plain_text(subsection.body)))
    if not chunks:
        chunks.append((block.title, ""))
    return chunks


def _scenario_slices(lines: list[str]) -> dict[int, list[str]]:
    indices: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^# Ситуация №(\d+)\.\s+(.+)$", line)
        if match:
            indices.append((index, int(match.group(1))))
    result: dict[int, list[str]] = {}
    for position, (index, number) in enumerate(indices):
        end = indices[position + 1][0] if position + 1 < len(indices) else len(lines)
        result[number] = lines[index:end]
    return result


def _completion_actions(block: Block) -> tuple[str, list[str]]:
    body: list[str] = []
    primary = ""
    secondary: list[str] = []
    for line in block.body:
        # Internal editorial fixation stays in Markdown but never enters runtime JSON.
        if line.strip() == "# Итоговая фиксация":
            break
        primary_match = re.match(r"^\*\*Основная кнопка:\*\*\s*(.+?)\.?\s{0,2}$", line)
        secondary_match = re.match(r"^\*\*Дополнительные действия:\*\*\s*(.+?)\.?\s{0,2}$", line)
        if primary_match:
            primary = primary_match.group(1).rstrip(".")
        elif secondary_match:
            secondary = [item.strip().rstrip(".") for item in secondary_match.group(1).split(";")]
        else:
            body.append(line)
    if not primary or len(secondary) != 2:
        raise ValueError(f"Incomplete completion actions: {block.title}")
    while body and (not body[-1].strip() or body[-1].strip() == "---"):
        body.pop()
    return _plain_text(body), [primary, *secondary]


def build_scenario(number: int, lines: list[str]) -> dict[str, object]:
    heading = re.match(r"^# Ситуация №\d+\.\s+(.+)$", lines[0])
    if not heading:
        raise ValueError(f"Invalid situation heading: {lines[0]}")
    title = heading.group(1)
    scenario_id, stage, intro_asset = SCENARIO_META[number]
    source_id = next(
        re.search(r"`([A-Z0-9_]+)`", line).group(1)  # type: ignore[union-attr]
        for line in lines[:8]
        if line.startswith("**scenario_id:**")
    )
    if source_id != scenario_id:
        raise ValueError(f"Scenario id mismatch for {number}: {source_id} != {scenario_id}")
    short_title_line = next(
        line for line in lines[:8] if line.startswith("**Короткое название для карточки:**")
    )
    short_title = _plain_inline(short_title_line.split(":**", 1)[1])

    h2 = _blocks(lines[1:], 2)
    goal = _plain_text(_block(h2, "Образовательная цель").body)
    intros = _age_text(_block(h2, "Вводная ситуация"))
    questions = _age_text(_block(h2, "Первый вопрос родителю"))
    initial_labels = _choice_labels(_block(h2, "Первый выбор"))

    nodes: dict[str, dict[str, object]] = {
        "intro": {
            "type": "info",
            "title": f"Ситуация {number} из 7. {title}",
            "text_by_age": intros,
            "next": "start_choice",
            "methodology": {"full_explanation": goal},
            "media": _media(intro_asset, "hero"),
        },
        "start_choice": {
            "type": "choice",
            "text_by_age": questions,
            "buttons": [
                {
                    "id": CYR_TO_LATIN[letter],
                    "label": initial_labels[letter],
                    "next": f"{CYR_TO_LATIN[letter]}_choice",
                    "tracking_code": f"S{number:02d}_{CYR_TO_LATIN[letter].upper()}",
                }
                for letter in CYR_TO_LATIN
            ],
        },
    }

    variant_blocks = [item for item in h2 if re.match(r"^Вариант [А-Г]\. ", item.title)]
    if len(variant_blocks) != 4:
        raise ValueError(f"Situation {number} has {len(variant_blocks)} variants")
    final_branches = 0
    for variant in variant_blocks:
        match = re.match(r"^Вариант ([А-Г])\. ", variant.title)
        assert match is not None
        letter = match.group(1)
        latin = CYR_TO_LATIN[letter]
        branch_blocks = [
            item for item in _subsections(variant, 3) if re.match(fr"^{letter}[1-3]\. ", item.title)
        ]
        if len(branch_blocks) != 3:
            raise ValueError(
                f"Situation {number} variant {letter} has {len(branch_blocks)} branches"
            )
        nodes[f"{latin}_choice"] = {
            "type": "choice",
            "text": _plain_text(_before_subheading(variant, 3)),
            "buttons": [],
        }
        choice_buttons = nodes[f"{latin}_choice"]["buttons"]
        assert isinstance(choice_buttons, list)
        for branch in branch_blocks:
            branch_match = re.match(fr"^{letter}([1-3])\.\s+(.+)$", branch.title)
            assert branch_match is not None
            branch_number = branch_match.group(1)
            branch_id = f"{latin}{branch_number}"
            choice_buttons.append(
                {
                    "id": branch_id,
                    "label": _plain_inline(branch_match.group(2)),
                    "next": f"{branch_id}_now",
                    "tracking_code": f"S{number:02d}_{latin.upper()}{branch_number}",
                }
            )
            parts = _branch_parts(branch)
            nodes[f"{branch_id}_now"] = {
                "type": "outcome",
                "title": "Что может произойти сейчас",
                "text": parts["now"],
                "next": f"{branch_id}_repeated",
            }
            nodes[f"{branch_id}_repeated"] = {
                "type": "outcome",
                "title": "Если такая реакция повторяется",
                "text": parts["repeated"],
                "next": f"{branch_id}_advice",
            }
            nodes[f"{branch_id}_advice"] = {
                "type": "advice",
                "title": "Практический совет",
                "text": parts["advice"],
                "quote": parts["quote"],
                "next": "summary_main",
                "media": _media("ui_practice_task", "compact"),
            }
            final_branches += 1
    if final_branches != 12:
        raise ValueError(f"Situation {number} has {final_branches} final branches")

    summary = _block(h2, "Общий вывод")
    nodes["summary_main"] = {
        "type": "tool",
        "title": summary.title,
        "text": _plain_text(summary.body),
        "next": "tool_01",
        "media": _media("ui_insight", "card"),
    }

    summary_index = h2.index(summary)
    completion = _block(h2, "Завершение ситуации")
    completion_index = h2.index(completion)
    tool_blocks = h2[summary_index + 1 : completion_index]
    chunks: list[tuple[str, str, str]] = []
    for tool_block in tool_blocks:
        node_type = "emergency" if tool_block.title == "Отдельный протокол безопасности" else "tool"
        for chunk_title, chunk_text in _tool_chunks(tool_block):
            chunks.append((chunk_title, chunk_text, node_type))
    if not chunks:
        raise ValueError(f"Situation {number} has no practical tool")
    for index, (chunk_title, chunk_text, node_type) in enumerate(chunks, start=1):
        node_id = f"tool_{index:02d}"
        next_id = f"tool_{index + 1:02d}" if index < len(chunks) else "completion"
        asset = "ui_neural_focus" if "ритуал" in chunk_title.lower() else "ui_practice_task"
        nodes[node_id] = {
            "type": node_type,
            "title": chunk_title,
            "text": chunk_text,
            "next": next_id,
            "media": _media(asset, "compact"),
        }

    completion_text, completion_actions = _completion_actions(completion)
    primary_target = "module_completion" if number == 7 else SYSTEM_NEXT_SCENARIO
    nodes["completion"] = {
        "type": "completion",
        "title": "Ситуация пройдена",
        "text": completion_text,
        "buttons": [
            {"id": "next", "label": completion_actions[0], "next": primary_target},
            {"id": "repeat", "label": completion_actions[1], "next": "intro"},
            {"id": "home", "label": completion_actions[2], "next": SYSTEM_MAIN_MENU},
        ],
        "media": _media("ui_achievement", "hero"),
    }
    if number == 7:
        nodes["module_completion"] = {
            "type": "completion",
            "title": "Образовательный тренажёр завершён",
            "text": (
                "Пройдены все семь ситуаций.\n\n"
                "1. Правило трёх вопросов.\n"
                "2. Задача — действия — поддержка.\n"
                "3. Один спокойный сигнал — и внимание снова на игре.\n"
                "4. Чувство — факт — действия.\n"
                "5. Решение — реакция — продолжение игры.\n"
                "6. Пауза — выбор — возвращение.\n"
                "7. Радость — вклад — развитие."
            ),
            "buttons": [
                {
                    "id": "home",
                    "label": "Вернуться на главную",
                    "next": SYSTEM_MAIN_MENU,
                }
            ],
            "media": _media("ui_achievement", "hero"),
        }

    return {
        "schema_version": "1.2",
        "scenario": {
            "id": scenario_id,
            "content_version": "2026-07-16.1-approved-v1",
            "sport": "football",
            "language": "ru",
            "title": title,
            "short_title": short_title,
            "stage": stage,
            "estimated_minutes": 8,
            "age_groups": ["6-8", "9-12", "13-16"],
            "entry_node": "intro",
            "asset_manifest": "assets/asset_manifest.json",
            "nodes": nodes,
        },
    }


def build_all() -> dict[int, dict[str, object]]:
    lines = SOURCE.read_text(encoding="utf-8-sig").splitlines()
    slices = _scenario_slices(lines)
    if set(slices) != set(range(1, 8)):
        raise ValueError(f"Expected situations 1-7, found {sorted(slices)}")
    return {number: build_scenario(number, slices[number]) for number in range(1, 8)}


def main() -> None:
    scenarios = build_all()
    for number, bundle in scenarios.items():
        scenario_id = SCENARIO_META[number][0]
        path = CONTENT / f"{scenario_id}.json"
        path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
