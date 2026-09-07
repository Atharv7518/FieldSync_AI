import re
from datetime import date

import pandas as pd


DISCIPLINES = [
    "civil",
    "piping",
    "electrical",
    "instrumentation",
    "mechanical",
    "hse",
]


def find_report_date(text: str) -> date | None:
    """Finds a date such as '15 January 2026' or '2026-01-15'."""

    patterns = [
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            try:
                return pd.to_datetime(match.group()).date()
            except (ValueError, TypeError):
                continue

    return None


def detect_discipline(sentence: str) -> str | None:
    """Finds the engineering discipline mentioned in a sentence."""

    sentence_lower = sentence.lower()

    for discipline in DISCIPLINES:
        if discipline in sentence_lower:
            return discipline.capitalize()

    return None


def detect_event_type(sentence: str) -> str | None:
    """Detects whether work was started, completed, or is in progress."""

    sentence_lower = sentence.lower()

    completed_words = [
        "completed",
        "complete",
        "finished",
        "finish",
        "erected",
        "installed",
    ]

    started_words = [
        "started",
        "start",
        "began",
        "begin",
        "commenced",
    ]

    progress_words = [
        "in progress",
        "ongoing",
        "continuing",
        "under progress",
    ]

    if any(word in sentence_lower for word in completed_words):
        return "completed"

    if any(word in sentence_lower for word in started_words):
        return "started"

    if any(word in sentence_lower for word in progress_words):
        return "progress"

    return None


def detect_progress_percent(sentence: str) -> float | None:
    """Extracts values such as 35% from a sentence."""

    match = re.search(r"\b(\d{1,3}(?:\.\d+)?)\s*%", sentence)

    if match:
        return float(match.group(1))

    return None


def calculate_confidence(
    discipline: str | None,
    event_type: str | None,
    event_date: date | None,
) -> float:
    """A simple transparent confidence score for the MVP."""

    confidence = 50.0

    if discipline:
        confidence += 20.0

    if event_type:
        confidence += 20.0

    if event_date:
        confidence += 10.0

    return confidence


def extract_progress_events(report_text: str) -> list[dict]:
    """
    Splits a daily report into sentences and returns useful work-progress events.
    """

    report_date = find_report_date(report_text)

    # Splits text after full stop, exclamation, or question mark.
    sentences = re.split(r"(?<=[.!?])\s+", report_text.strip())

    extracted_events = []

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        discipline = detect_discipline(sentence)
        event_type = detect_event_type(sentence)

        # Ignore heading text such as “Daily Progress Report - 15 January 2026”.
        if not event_type:
            continue

        progress_percent = detect_progress_percent(sentence)

        extracted_events.append(
            {
                "reported_description": sentence,
                "discipline": discipline,
                "event_type": event_type,
                "event_date": report_date,
                "progress_percent": progress_percent,
                "extraction_confidence": calculate_confidence(
                    discipline,
                    event_type,
                    report_date,
                ),
            }
        )

    return extracted_events