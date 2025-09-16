"""Rule-based parser for onboarding brief sections."""
from __future__ import annotations

import re
from typing import Iterable, List


def sentence_split(text: str) -> List[str]:
    """Split raw text into sentences using simple punctuation boundaries."""
    if not text:
        return []
    normalized = re.sub(r"\s+", " ", text.strip())
    # Split on punctuation that typically ends a sentence.
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    sentences = [part.strip() for part in parts if part.strip()]
    return sentences


def _first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def extract_title(text: str) -> str:
    """Return a brief title derived from the first sentence or line."""
    first_sentence = next(iter(sentence_split(text)), "")
    candidate = first_sentence.rstrip(". ") if first_sentence else None
    if not candidate:
        candidate = _first_nonempty_line(text) or "Onboarding Brief"
    if len(candidate) > 90:
        return "Onboarding Brief"
    # Append suffix if missing to reinforce artifact type.
    suffix = "– Onboarding Brief"
    if "brief" in candidate.lower():
        return candidate
    return f"{candidate} {suffix}".strip()


_GOAL_RE = re.compile(r"\b(goal|target|deliver|okr|kpi|outcome)s?\b", re.IGNORECASE)
_CONSTRAINT_RE = re.compile(
    r"\b(budget|budgets|deadline|deadlines|timeline|timelines|scope|scopes|constraint|constraints|compliance|security|tech|"
    r"technology|data|dependency|dependencies)\b",
    re.IGNORECASE,
)
_UNKNOWN_RE = re.compile(r"\b(unknown|unclear|tbd|open question)\b|\?", re.IGNORECASE)
_RISK_RE = re.compile(
    r"\b(risk|blocker|fail|dependency|legal|security|churn|outage|delay|issue|limit)\b",
    re.IGNORECASE,
)
_GOAL_LABEL_RE = re.compile(r"(goal|target|deliver|okr|kpi|outcome)s?:", re.IGNORECASE)
_CONSTRAINT_LABEL_RE = re.compile(
    r"(constraint|budget|deadline|timeline|scope|compliance|security|tech|data|dependency)s?:",
    re.IGNORECASE,
)
_UNKNOWN_LABEL_RE = re.compile(r"(unknown|unclear|tbd|open question)s?:", re.IGNORECASE)
_RISK_LABEL_RE = re.compile(r"(risk|blocker|dependency|legal|security|churn|outage|fail)s?:", re.IGNORECASE)
_STAKEHOLDER_LABEL_RE = re.compile(r"(stakeholder|sponsor|owner)s?:", re.IGNORECASE)


def _clean_prefix(text: str) -> str:
    return re.sub(r"^(goal[s]?|constraint[s]?|unknowns?|risks?|notes?):\s*",
                  "", text, flags=re.IGNORECASE)


def extract_context(sentences: Iterable[str]) -> str:
    """Select one to two sentences that provide project context."""
    context: List[str] = []
    exclusion_patterns = (
        _GOAL_RE,
        _CONSTRAINT_RE,
        _UNKNOWN_RE,
        _RISK_RE,
        _STAKEHOLDER_LABEL_RE,
    )
    for sentence in sentences:
        if any(pattern.search(sentence) for pattern in exclusion_patterns):
            continue
        cleaned = sentence.strip()
        if cleaned:
            context.append(cleaned)
        if len(context) == 2:
            break
    if not context and sentences:
        first = next(iter(sentences))
        if first:
            context.append(first.strip())
    return " ".join(context)


def extract_goals(chunks: Iterable[str]) -> List[str]:
    goals: List[str] = []
    for chunk in chunks:
        if not _GOAL_RE.search(chunk):
            continue
        body = chunk
        label = _GOAL_LABEL_RE.search(chunk)
        if label:
            body = chunk[label.end() :]
        pieces = re.split(r"[.;\n]\s*", body)
        for piece in pieces:
            candidate = _clean_prefix(piece).strip(" -•")
            if not candidate:
                continue
            lower = candidate.lower()
            if any(
                token in lower
                for token in (
                    "unknown",
                    "risk",
                    "constraint",
                    "stakeholder",
                    "budget",
                    "deadline",
                    "timeline",
                    "scope",
                )
            ):
                continue
            candidate = candidate.rstrip(". ")
            if candidate:
                normalized = candidate[0].upper() + candidate[1:] if candidate else candidate
                if normalized not in goals:
                    goals.append(normalized)
            if len(goals) >= 3:
                break
        if len(goals) >= 3:
            break
    return goals[:3]


def extract_constraints(chunks: Iterable[str]) -> List[str]:
    constraints: List[str] = []
    for chunk in chunks:
        match = _CONSTRAINT_RE.search(chunk)
        if not match:
            continue
        keyword = match.group(0).lower()
        body = chunk
        label = _CONSTRAINT_LABEL_RE.search(chunk)
        if label:
            body = chunk[label.end() :]
        elif keyword in {"tech", "technology", "data"}:
            # Avoid treating generic mentions as constraints without a label.
            continue
        pieces = re.split(r"[,;\n]\s*", body)
        if not label:
            pieces = [body]
        for piece in pieces:
            candidate = _clean_prefix(piece).strip(" -•")
            if not candidate:
                continue
            lower = candidate.lower()
            stop_after = False
            for marker in ("stakeholders", "unknowns", "risks", "goals"):
                if marker in lower:
                    candidate = candidate.split(marker, 1)[0].strip(" -•. ")
                    stop_after = True
                    lower = candidate.lower()
                    break
            if any(token in lower for token in ("unknown", "risk", "stakeholder", "goal")):
                if stop_after:
                    break
                continue
            candidate = candidate.rstrip(". ")
            if candidate and candidate not in constraints:
                constraints.append(candidate)
            if len(constraints) >= 5:
                break
            if stop_after:
                break
        if len(constraints) >= 5:
            break
    return constraints[:5]


_STAKEHOLDER_NAME_ROLE_RE = re.compile(
    r"(?P<name>[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+)+)\s*[–-]\s*(?P<role>[^,;]+)"
)
_PAREN_ROLE_RE = re.compile(r"([A-Z][A-Za-z'.-]+)\s*\(([^)]+)\)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9_.-]+\.[A-Za-z]{2,}")
_TITLED_NAME_RE = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")


def extract_stakeholders(text: str) -> List[str]:
    found: List[str] = []
    seen = set()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        lower_line = line.lower()
        for name, role in _PAREN_ROLE_RE.findall(line):
            label = f"{name} – {role.strip()}"
            if label not in seen:
                seen.add(label)
                found.append(label)
        for match in _STAKEHOLDER_NAME_ROLE_RE.finditer(line):
            label = f"{match.group('name')} – {match.group('role').strip()}"
            if label not in seen:
                seen.add(label)
                found.append(label)
        for email in _EMAIL_RE.findall(line):
            if email not in seen:
                seen.add(email)
                found.append(email)
        if any(token in lower_line for token in ("stakeholder", "owner", "sponsor")):
            for name in _TITLED_NAME_RE.findall(line):
                if name not in seen:
                    seen.add(name)
                    found.append(name)
        if len(found) >= 8:
            break
    return found[:8]


def extract_unknowns(sentences: Iterable[str]) -> List[str]:
    unknowns: List[str] = []
    for sentence in sentences:
        if _UNKNOWN_RE.search(sentence):
            body = sentence
            label = _UNKNOWN_LABEL_RE.search(sentence)
            if label:
                body = sentence[label.end() :]
            parts = re.split(r"[?•\u2022]\s*", body)
            for part in parts:
                cleaned = _clean_prefix(part).strip(" -•")
                if not cleaned:
                    continue
                cleaned = cleaned.rstrip("?. ")
                if not cleaned:
                    continue
                text = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
                if not text:
                    continue
                if not text.lower().startswith("clarify"):
                    text = f"Clarify {text}".strip()
                if not text.endswith('.'):
                    text = f"{text}."
                if text not in unknowns:
                    unknowns.append(text)
    return unknowns


def extract_risks(sentences: Iterable[str]) -> List[str]:
    risks: List[str] = []
    for sentence in sentences:
        if _RISK_RE.search(sentence):
            body = sentence
            label = _RISK_LABEL_RE.search(sentence)
            if label:
                body = sentence[label.end() :]
            pieces = re.split(r"[;•\u2022]\s*", body)
            if not label:
                pieces = [body]
            for piece in pieces:
                candidate = _clean_prefix(piece).strip(" -•")
                if not candidate:
                    continue
                lower = candidate.lower()
                if "unknown" in lower:
                    continue
                candidate = re.sub(r"\s+", " ", candidate).rstrip(". ")
                if candidate and candidate not in risks:
                    risks.append(candidate)
    return risks


def make_week1_plan(goals: List[str], risks: List[str], stakeholders: List[str]) -> List[str]:
    primary = stakeholders[0] if stakeholders else "primary stakeholder"
    step1 = f"Confirm goals/constraints with {primary}."
    step2 = "Get access to systems/data + create success metric."
    if goals:
        primary_goal = goals[0].rstrip('. ')
        step2 = f"Get access to systems/data + define metric for '{primary_goal}'."
    if risks:
        risk_summary = risks[0].rstrip('. ')
        step3 = f"Ship Day-5 brief: status, risks, decision needed (watch '{risk_summary}')."
    else:
        step3 = "Ship Day-5 brief: status, risks, decision needed."
    return [step1, step2, step3]


def parse_text(text: str) -> dict:
    sentences = sentence_split(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    combined = list(dict.fromkeys(sentences + lines)) if sentences else lines
    title = extract_title(text)
    context = extract_context(sentences)
    goals = extract_goals(combined or sentences)
    constraints = extract_constraints(combined or sentences)
    stakeholders = extract_stakeholders(text)
    unknowns = extract_unknowns(sentences)
    risks = extract_risks(sentences)
    week1_plan = make_week1_plan(goals, risks, stakeholders)
    return {
        "title": title or "Onboarding Brief",
        "context": context,
        "goals": goals,
        "constraints": constraints,
        "stakeholders": stakeholders,
        "unknowns": unknowns,
        "risks": risks,
        "week1_plan": week1_plan,
    }
