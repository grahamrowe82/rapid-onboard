"""Flask app for generating rapid onboarding briefs."""
from __future__ import annotations

import json
from typing import Any, Dict

from flask import Flask, Response, render_template, request

from .export import to_markdown
from .logic import parse_text

app = Flask(__name__)
app.secret_key = "rapid-onboard"

_INPUT_LIMIT = 2000


def _default_sections() -> Dict[str, Any]:
    return {
        "title": "Onboarding Brief",
        "context": "",
        "goals": [],
        "constraints": [],
        "stakeholders": [],
        "unknowns": [],
        "risks": [],
        "week1_plan": [],
    }


@app.route("/", methods=["GET"])
def home() -> str:
    return render_template(
        "index.html",
        sections=None,
        original_text="",
        error=None,
    )


def _coerce_sections(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    sections = _default_sections()
    if not raw:
        return sections
    for key in sections:
        value = raw.get(key)
        if key in {"context", "title"}:
            sections[key] = str(value or "").strip()
        elif isinstance(value, list):
            sections[key] = [str(item).strip() for item in value if str(item).strip()]
        elif value:
            sections[key] = [str(value).strip()]
    return sections


@app.route("/brief", methods=["POST"])
def brief() -> str:
    text = request.form.get("text", "").strip()
    if len(text) > _INPUT_LIMIT:
        return render_template(
            "index.html",
            sections=None,
            original_text=text[:_INPUT_LIMIT],
            error="Trim input (2,000 char limit).",
        )
    if not text:
        return render_template(
            "index.html",
            sections=None,
            original_text="",
            error="Provide kickoff notes to generate a brief.",
        )
    sections = parse_text(text)
    section_json = json.dumps(sections)
    return render_template(
        "index.html",
        sections=sections,
        original_text=text,
        error=None,
        section_json=section_json,
    )


@app.route("/download.md", methods=["POST"])
def download_markdown() -> Response:
    section_data = request.form.get("section_data")
    sections: Dict[str, Any] | None = None
    if section_data:
        try:
            sections = json.loads(section_data)
        except json.JSONDecodeError:
            sections = None
    if sections is None:
        text = request.form.get("text", "")
        sections = parse_text(text) if text else _default_sections()
    normalized = _coerce_sections(sections)
    markdown_bytes = to_markdown(normalized)
    return Response(
        markdown_bytes,
        mimetype="text/markdown",
        headers={
            "Content-Disposition": "attachment; filename=onboarding_brief.md",
        },
    )


if __name__ == "__main__":
    app.run(debug=True)
