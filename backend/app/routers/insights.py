from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScheduleActivity


router = APIRouter(
    prefix="/api/insights",
    tags=["Institutional Memory"],
)


@router.get("/institutional-memory")
def get_institutional_memory(
    db: Session = Depends(get_db),
):
    """
    Builds a queryable summary of actual project execution patterns.
    Future projects can use this data for planning and forecasting.
    """

    activities = db.scalars(
        select(ScheduleActivity)
    ).all()

    discipline_data = defaultdict(
        lambda: {
            "completed_activity_count": 0,
            "delayed_activity_count": 0,
            "total_actual_duration_days": 0,
            "total_planned_duration_days": 0,
            "actual_duration_samples": 0,
            "planned_duration_samples": 0,
        }
    )

    completed_with_actual_dates = 0

    for activity in activities:
        discipline = activity.discipline or "Not Specified"
        summary = discipline_data[discipline]

        if activity.status == "completed":
            summary["completed_activity_count"] += 1

        if (
            activity.planned_finish
            and activity.actual_finish
            and activity.actual_finish > activity.planned_finish
        ):
            summary["delayed_activity_count"] += 1

        if activity.actual_start and activity.actual_finish:
            actual_duration = (
                activity.actual_finish - activity.actual_start
            ).days

            summary["total_actual_duration_days"] += max(
                actual_duration,
                0,
            )

            summary["actual_duration_samples"] += 1
            completed_with_actual_dates += 1

        if activity.planned_start and activity.planned_finish:
            planned_duration = (
                activity.planned_finish - activity.planned_start
            ).days

            summary["total_planned_duration_days"] += max(
                planned_duration,
                0,
            )

            summary["planned_duration_samples"] += 1

    formatted_discipline_summary = {}

    for discipline, values in discipline_data.items():
        average_actual_duration = None
        average_planned_duration = None

        if values["actual_duration_samples"] > 0:
            average_actual_duration = round(
                values["total_actual_duration_days"]
                / values["actual_duration_samples"],
                2,
            )

        if values["planned_duration_samples"] > 0:
            average_planned_duration = round(
                values["total_planned_duration_days"]
                / values["planned_duration_samples"],
                2,
            )

        formatted_discipline_summary[discipline] = {
            "completed_activity_count": values[
                "completed_activity_count"
            ],
            "delayed_activity_count": values[
                "delayed_activity_count"
            ],
            "average_actual_duration_days": average_actual_duration,
            "average_planned_duration_days": average_planned_duration,
        }

    return {
        "message": (
            "Institutional memory summary generated from actual "
            "project execution data."
        ),
        "total_activities": len(activities),
        "completed_activities_with_actual_dates": (
            completed_with_actual_dates
        ),
        "discipline_execution_patterns": formatted_discipline_summary,
    }