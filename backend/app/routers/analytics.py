from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivityMatch, ProgressEvent, ScheduleActivity


router = APIRouter(
    prefix="/api/analytics",
    tags=["Project Analytics"],
)


def is_delayed(activity: ScheduleActivity) -> bool:
    """
    An activity is delayed when:
    1. Its actual finish date is later than planned finish, OR
    2. It is unfinished after its planned finish date.
    """

    if not activity.planned_finish:
        return False

    if (
        activity.actual_finish
        and activity.actual_finish > activity.planned_finish
    ):
        return True

    if (
        activity.status != "completed"
        and date.today() > activity.planned_finish
    ):
        return True

    return False


@router.get("/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
):
    """Returns project-level and discipline-level progress analytics."""

    activities = db.scalars(
        select(ScheduleActivity)
    ).all()

    events = db.scalars(
        select(ProgressEvent)
    ).all()

    matched_event_ids = set(
        db.scalars(
            select(ActivityMatch.progress_event_id)
        ).all()
    )

    pending_match_count = len(
        db.scalars(
            select(ActivityMatch).where(
                ActivityMatch.review_status == "pending"
            )
        ).all()
    )

    discipline_data = defaultdict(
        lambda: {
            "total": 0,
            "completed": 0,
            "in_progress": 0,
            "not_started": 0,
            "delayed": 0,
        }
    )

    completed_count = 0
    delayed_count = 0
    in_progress_count = 0
    not_started_count = 0

    for activity in activities:
        discipline = activity.discipline or "Not Specified"
        statistics = discipline_data[discipline]

        statistics["total"] += 1

        if activity.status == "completed":
            completed_count += 1
            statistics["completed"] += 1

        elif activity.status == "in_progress":
            in_progress_count += 1
            statistics["in_progress"] += 1

        else:
            not_started_count += 1
            statistics["not_started"] += 1

        if is_delayed(activity):
            delayed_count += 1
            statistics["delayed"] += 1

    return {
        "project_summary": {
            "total_schedule_activities": len(activities),
            "completed_activities": completed_count,
            "in_progress_activities": in_progress_count,
            "not_started_activities": not_started_count,
            "delayed_activities": delayed_count,
            "total_progress_events": len(events),
            "matched_progress_events": len(matched_event_ids),
            "unmatched_progress_events": (
                len(events) - len(matched_event_ids)
            ),
            "pending_planner_reviews": pending_match_count,
        },
        "discipline_summary": dict(discipline_data),
    }