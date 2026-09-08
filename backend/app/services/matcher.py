import re
from rapidfuzz import fuzz
from app.models import ProgressEvent, ScheduleActivity

SYNONYMS = {
    "erected": "erect",
    "erection": "erect",
    "installed": "install",
    "installation": "install",
    "completed": "",
    "complete": "",
    "started": "",
    "start": "",
    "team": "",
    "work": "",
    "near": "",
}


def normalize_text(text: str) -> str:
    """Cleans engineering text for fuzzy token matching."""
    if not text:
        return ""
    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)

    words = []
    for word in normalized.split():
        cleaned_word = SYNONYMS.get(word, word)
        if cleaned_word:
            words.append(cleaned_word)

    return " ".join(words)


def calculate_hybrid_score(
    event_description: str,
    activity_name: str,
) -> float:
    """
    Computes a lightweight, zero-RAM hybrid similarity score (0 to 100):
    - token_set_ratio (60%): Handles subset phrases and extra descriptor words
    - token_sort_ratio (40%): Evaluates strict token overlap regardless of word order
    """
    cleaned_event = normalize_text(event_description)
    cleaned_activity = normalize_text(activity_name)

    if not cleaned_event or not cleaned_activity:
        return 0.0

    set_score = fuzz.token_set_ratio(cleaned_event, cleaned_activity)
    sort_score = fuzz.token_sort_ratio(cleaned_event, cleaned_activity)

    hybrid_score = (set_score * 0.60) + (sort_score * 0.40)
    return round(hybrid_score, 2)


def find_best_schedule_match(
    event: ProgressEvent,
    activities: list[ScheduleActivity],
) -> tuple[ScheduleActivity, float]:
    """
    Finds the best matching schedule activity.
    Same-discipline activities are prioritized when discipline data is present.
    """
    if not activities:
        raise ValueError("No schedule activities are available for matching.")

    # Filter by discipline if present
    if event.discipline:
        discipline_candidates = [
            activity
            for activity in activities
            if activity.discipline
            and activity.discipline.strip().lower() == event.discipline.strip().lower()
        ]
        candidates = discipline_candidates or activities
    else:
        candidates = activities

    best_activity = candidates[0]
    best_score = calculate_hybrid_score(
        event.reported_description,
        best_activity.activity_name,
    )

    for activity in candidates[1:]:
        score = calculate_hybrid_score(
            event.reported_description,
            activity.activity_name,
        )
        if score > best_score:
            best_activity = activity
            best_score = score

    return best_activity, best_score