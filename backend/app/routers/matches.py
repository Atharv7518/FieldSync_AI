from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivityMatch, ProgressEvent, ScheduleActivity
from app.schemas import MatchResultResponse
from app.services.matcher import find_best_schedule_match


router = APIRouter(
    prefix="/api/events",
    tags=["AI Schedule Matching"],
)


@router.post(
    "/{event_id}/match",
    response_model=MatchResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def match_event_to_schedule(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Uses RapidFuzz to suggest the best L5/L6 schedule activity
    for one site progress event.
    """

    event = db.get(ProgressEvent, event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress event not found.",
        )

    existing_match = db.scalar(
        select(ActivityMatch).where(
            ActivityMatch.progress_event_id == event_id
        )
    )

    if existing_match:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This event already has a schedule match.",
        )

    activities = db.scalars(
        select(ScheduleActivity)
    ).all()

    if not activities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No schedule activities found. Upload a schedule first.",
        )

    best_activity, confidence_score = find_best_schedule_match(
        event,
        activities,
    )

    new_match = ActivityMatch(
        progress_event_id=event.id,
        schedule_activity_id=best_activity.id,
        confidence_score=confidence_score,
        match_method="hybrid_rapidfuzz_sentence_transformer",
        review_status="pending",
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return MatchResultResponse(
        message="Best schedule match suggested. Planner review is required.",
        event_id=event.id,
        reported_description=event.reported_description,
        suggested_activity_code=best_activity.activity_code,
        suggested_activity_name=best_activity.activity_name,
        discipline=event.discipline,
        confidence_score=confidence_score,
        review_status=new_match.review_status,
        match=new_match,
    )