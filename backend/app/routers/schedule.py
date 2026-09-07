from datetime import date
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScheduleActivity
from app.schemas import (
    ScheduleActivityCreate,
    ScheduleActivityResponse,
    ScheduleImportResponse,
)


router = APIRouter(
    prefix="/api/activities",
    tags=["Schedule Activities"],
)


def clean_text(value) -> str | None:
    """Converts Excel/CSV values into clean text or None."""
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text if text else None


def parse_optional_date(value) -> date | None:
    """Converts CSV/Excel date values to Python date objects."""
    text_value = clean_text(value)

    if text_value is None:
        return None

    try:
        return pd.to_datetime(text_value).date()
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid date '{text_value}'. Use format YYYY-MM-DD."
        )


@router.post(
    "",
    response_model=ScheduleActivityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_activity(
    activity: ScheduleActivityCreate,
    db: Session = Depends(get_db),
):
    """Creates one planned L5/L6 schedule activity manually."""

    existing_activity = db.scalar(
        select(ScheduleActivity).where(
            ScheduleActivity.activity_code == activity.activity_code
        )
    )

    if existing_activity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Activity code '{activity.activity_code}' already exists.",
        )

    new_activity = ScheduleActivity(
        activity_code=activity.activity_code,
        activity_name=activity.activity_name,
        wbs_code=activity.wbs_code,
        wbs_level=activity.wbs_level,
        discipline=activity.discipline,
        planned_start=activity.planned_start,
        planned_finish=activity.planned_finish,
    )

    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)

    return new_activity


@router.get(
    "",
    response_model=list[ScheduleActivityResponse],
)
def list_schedule_activities(
    db: Session = Depends(get_db),
):
    """Returns all schedule activities stored in MySQL."""

    return db.scalars(
        select(ScheduleActivity).order_by(ScheduleActivity.id)
    ).all()


@router.post(
    "/upload",
    response_model=ScheduleImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_schedule_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a schedule CSV or Excel file and store new activities in MySQL.
    Duplicate activity codes are skipped safely.
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please choose a CSV or Excel file.",
        )

    file_name = file.filename.lower()

    if not (file_name.endswith(".csv") or file_name.endswith(".xlsx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv and .xlsx files are supported.",
        )

    file_content = await file.read()

    try:
        if file_name.endswith(".csv"):
            dataframe = pd.read_csv(BytesIO(file_content))
        else:
            dataframe = pd.read_excel(BytesIO(file_content))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read this file: {error}",
        )

    # Remove accidental spaces from column headings.
    dataframe.columns = [
        str(column).strip().lower()
        for column in dataframe.columns
    ]

    required_columns = {"activity_code", "activity_name"}
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            ),
        )

    existing_codes = set(
        db.scalars(select(ScheduleActivity.activity_code)).all()
    )

    new_activities = []
    skipped_duplicate_count = 0

    for row_number, row in dataframe.iterrows():
        activity_code = clean_text(row["activity_code"])
        activity_name = clean_text(row["activity_name"])

        if not activity_code or not activity_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Row {row_number + 2}: "
                    "activity_code and activity_name are required."
                ),
            )

        if activity_code in existing_codes:
            skipped_duplicate_count += 1
            continue

        try:
            new_activity = ScheduleActivity(
                activity_code=activity_code,
                activity_name=activity_name,
                wbs_code=clean_text(row.get("wbs_code")),
                wbs_level=clean_text(row.get("wbs_level")),
                discipline=clean_text(row.get("discipline")),
                planned_start=parse_optional_date(
                    row.get("planned_start")
                ),
                planned_finish=parse_optional_date(
                    row.get("planned_finish")
                ),
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row {row_number + 2}: {error}",
            )

        new_activities.append(new_activity)
        existing_codes.add(activity_code)

    db.add_all(new_activities)
    db.commit()

    return ScheduleImportResponse(
        message="Schedule imported successfully.",
        imported_count=len(new_activities),
        skipped_duplicate_count=skipped_duplicate_count,
        total_rows=len(dataframe),
    )