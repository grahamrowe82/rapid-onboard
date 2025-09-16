"""Utilities for exporting onboarding brief data."""
from __future__ import annotations

from typing import Dict, Iterable, List


_SECTION_ORDER = [
    ("context", "Context"),
    ("goals", "Goals"),
    ("constraints", "Constraints"),
    ("stakeholders", "Stakeholders"),
    ("unknowns", "Unknowns"),
    ("risks", "Risks"),
    ("week1_plan", "Week 1 Plan"),
]


def _ensure_list(items: Iterable[str] | None) -> List[str]:
    if not items:
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def _format_list(items: Iterable[str]) -> List[str]:
    values = _ensure_list(items)
    if not values:
        return ["- —"]
    return [f"- {value}" for value in values]


def to_markdown(sections: Dict[str, object]) -> bytes:
    """Render the brief sections as Markdown and return UTF-8 encoded bytes."""
    title = str(sections.get("title") or "Onboarding Brief").strip()
    lines: List[str] = [f"# {title}", ""]
    for key, label in _SECTION_ORDER:
        lines.append(f"## {label}")
        lines.append("")
        if key == "context":
            context = str(sections.get("context") or "—").strip() or "—"
            lines.append(context)
        else:
            lines.extend(_format_list(sections.get(key)))
        lines.append("")
    markdown = "\n".join(lines).strip() + "\n"
    return markdown.encode("utf-8")
