import re

from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util

from app.models import ProgressEvent, ScheduleActivity


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# The model loads only when the first AI match is requested.
embedding_model = None


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


def get_embedding_model():
    """Loads the semantic AI model once and reuses it."""

    global embedding_model

    if embedding_model is None:
        embedding_model = SentenceTransformer(MODEL_NAME)

    return embedding_model


def normalize_text(text: str) -> str:
    """Cleans engineering text for RapidFuzz comparison."""

    normalized = text.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)

    words = []

    for word in normalized.split():
        cleaned_word = SYNONYMS.get(word, word)

        if cleaned_word:
            words.append(cleaned_word)

    return " ".join(words)


def calculate_fuzzy_score(
    event_description: str,
    activity_name: str,
) -> float:
    """RapidFuzz score from 0 to 100."""

    return round(
        fuzz.token_set_ratio(
            normalize_text(event_description),
            normalize_text(activity_name),
        ),
        2,
    )


def calculate_semantic_score(
    event_description: str,
    activity_name: str,
) -> float:
    """Sentence Transformer semantic score from 0 to 100."""

    model = get_embedding_model()

    embeddings = model.encode(
        [event_description, activity_name],
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    similarity = util.cos_sim(
        embeddings[0],
        embeddings[1],
    ).item()

    # Cosine similarity is usually between 0 and 1.
    # Convert it to a 0-100 score for the dashboard.
    return round(max(0, similarity) * 100, 2)


def calculate_hybrid_score(
    event_description: str,
    activity_name: str,
) -> float:
    """
    Combines keyword similarity and semantic similarity.
    RapidFuzz: 55%
    Sentence Transformer: 45%
    """

    fuzzy_score = calculate_fuzzy_score(
        event_description,
        activity_name,
    )

    semantic_score = calculate_semantic_score(
        event_description,
        activity_name,
    )

    return round(
        (fuzzy_score * 0.55) + (semantic_score * 0.45),
        2,
    )


def find_best_schedule_match(
    event: ProgressEvent,
    activities: list[ScheduleActivity],
) -> tuple[ScheduleActivity, float]:
    """
    Finds the best matching schedule activity.
    Same-discipline activities are preferred.
    """

    if event.discipline:
        discipline_candidates = [
            activity
            for activity in activities
            if activity.discipline
            and activity.discipline.lower() == event.discipline.lower()
        ]

        candidates = discipline_candidates or activities
    else:
        candidates = activities

    if not candidates:
        raise ValueError("No schedule activities are available for matching.")

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