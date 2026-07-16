from __future__ import annotations

import csv
import json
import re
from typing import Any

from generate_approved_scenarios import CONTENT, ROOT, SCENARIO_META, SOURCE, build_all

CSV_SOURCE = ROOT / "docs" / "content" / "mental-skills-all-7-situations-approved-v1.csv"
REPORT = CONTENT / "approved_text_comparison_report.json"
USER_TEXT_KEYS = {
    "title",
    "short_title",
    "text",
    "text_by_age",
    "quote",
    "label",
    "full_explanation",
}


def _normalize_source_text(value: str) -> str:
    value = re.sub(r"[#>*`•]", " ", value)
    value = value.replace("- **", " ").replace("**", " ")
    return " ".join(value.split()).casefold()


def _user_texts(value: Any, path: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            if key in USER_TEXT_KEYS:
                result[child_path] = child
            result.update(_user_texts(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.update(_user_texts(child, f"{path}/{index}"))
    return result


def main() -> None:
    expected = build_all()
    mismatches: list[dict[str, Any]] = []
    text_field_count = 0
    scenario_results: list[dict[str, Any]] = []
    for number in range(1, 8):
        scenario_id = SCENARIO_META[number][0]
        actual = json.loads((CONTENT / f"{scenario_id}.json").read_text(encoding="utf-8"))
        expected_texts = _user_texts(expected[number])
        actual_texts = _user_texts(actual)
        text_field_count += len(expected_texts)
        paths = sorted(set(expected_texts) | set(actual_texts))
        scenario_mismatches = []
        for path in paths:
            if expected_texts.get(path) != actual_texts.get(path):
                item = {
                    "scenario_id": scenario_id,
                    "json_pointer": path,
                    "expected": expected_texts.get(path),
                    "actual": actual_texts.get(path),
                }
                mismatches.append(item)
                scenario_mismatches.append(item)
        scenario_results.append(
            {
                "scenario_id": scenario_id,
                "user_text_fields": len(expected_texts),
                "mismatches": len(scenario_mismatches),
            }
        )

    with CSV_SOURCE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    invalid_status_rows = [
        index + 2 for index, row in enumerate(rows) if row.get("approval_status") != "утверждено"
    ]
    csv_situations = sorted({int(row["situation_number"]) for row in rows})
    markdown_corpus = _normalize_source_text(SOURCE.read_text(encoding="utf-8-sig"))
    csv_rows_not_in_markdown = [
        index + 2
        for index, row in enumerate(rows)
        if _normalize_source_text(row["approved_text"]) not in markdown_corpus
    ]

    report = {
        "approved_version": "v1-2026-07-16",
        "approved_markdown": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "approved_csv": str(CSV_SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "approved_csv_rows": len(rows),
        "approved_csv_situations": csv_situations,
        "invalid_approval_status_rows": invalid_status_rows,
        "csv_rows_not_found_in_markdown": csv_rows_not_in_markdown,
        "scenario_results": scenario_results,
        "user_text_fields_checked": text_field_count,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "implementation_authorized_text": [
            "PARENT_RESPONSE_AFTER_VICTORY_07:/scenario/nodes/module_completion/title",
            "PARENT_RESPONSE_AFTER_VICTORY_07:/scenario/nodes/module_completion/text",
        ],
        "status": (
            "passed"
            if not mismatches
            and not invalid_status_rows
            and not csv_rows_not_in_markdown
            and csv_situations == list(range(1, 8))
            else "failed"
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"{report['status']}: {text_field_count} user text fields, "
        f"{len(mismatches)} mismatches, {len(rows)} approved CSV rows"
    )
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
