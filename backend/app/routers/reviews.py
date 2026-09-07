from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivityMatch, AuditLog, ProgressEvent, ScheduleActivity
from app.schemas import MatchReviewRequest, MatchReviewResponse


router = APIRouter(
    prefix="/api/matches",
    tags=["Planner Review"],
)


@router.get("/pending")
def list_pending_matches(
    db: Session = Depends(get_db),
):
    """Returns AI matches that require planner review."""

    matches = db.scalars(
        select(ActivityMatch).where(
            ActivityMatch.review_status == "pending"
        )
    ).all()

    return matches


@router.patch(
    "/{match_id}/review",
    response_model=MatchReviewResponse,
)
def review_activity_match(
    match_id: int,
    review: MatchReviewRequest,
    db: Session = Depends(get_db),
):
    """
    Approve or reject an AI match.
    Only approval updates actual schedule progress.
    """

    match = db.get(ActivityMatch, match_id)

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found.",
        )

    if match.review_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This match has already been reviewed.",
        )

    event = db.get(ProgressEvent, match.progress_event_id)
    activity = db.get(ScheduleActivity, match.schedule_activity_id)

    if not event or not activity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Related event or schedule activity was not found.",
        )

    old_value = {
        "review_status": match.review_status,
        "actual_start": (
            activity.actual_start.isoformat()
            if activity.actual_start
            else None
        ),
        "actual_finish": (
            activity.actual_finish.isoformat()
            if activity.actual_finish
            else None
        ),
        "activity_status": activity.status,
    }

    match.review_status = review.decision
    match.reviewed_at = datetime.utcnow()

    # Only an approved match can change official actual progress.
    if review.decision == "approved":
        if event.event_type == "started":
            if (
                activity.actual_start is None
                or (
                    event.event_date
                    and event.event_date < activity.actual_start
                )
            ):
                activity.actual_start = event.event_date

            activity.status = "in_progress"

        elif event.event_type == "completed":
            if activity.actual_start is None:
                activity.actual_start = event.event_date

            activity.actual_finish = event.event_date
            activity.status = "completed"

        elif event.event_type == "progress":
            activity.status = "in_progress"

    new_value = {
        "review_status": match.review_status,
        "actual_start": (
            activity.actual_start.isoformat()
            if activity.actual_start
            else None
        ),
        "actual_finish": (
            activity.actual_finish.isoformat()
            if activity.actual_finish
            else None
        ),
        "activity_status": activity.status,
    }

    audit_log = AuditLog(
        entity_type="activity_match",
        entity_id=match.id,
        action=f"planner_{review.decision}",
        old_value=old_value,
        new_value=new_value,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(activity)

    return MatchReviewResponse(
        message=f"Match {review.decision} successfully.",
        match_id=match.id,
        review_status=match.review_status,
        schedule_activity_id=activity.id,
        actual_start=activity.actual_start,
        actual_finish=activity.actual_finish,
        activity_status=activity.status,
    )