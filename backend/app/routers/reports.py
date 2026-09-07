from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProgressEvent, SourceReport
from app.schemas import (
    ExtractionResponse,
    ProgressEventResponse,
    SourceReportCreate,
    SourceReportResponse,
)
from app.services.extractor import extract_progress_events

from io import BytesIO

import pandas as pd


router = APIRouter(
    prefix="/api/reports",
    tags=["Daily Progress Reports"],
)


@router.post(
    "",
    response_model=SourceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_text_report(
    report: SourceReportCreate,
    db: Session = Depends(get_db),
):
    """Saves a free-text daily report."""

    new_report = SourceReport(
        source_type=report.source_type,
        raw_content=report.raw_content,
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report


@router.get(
    "",
    response_model=list[SourceReportResponse],
)
def list_reports(
    db: Session = Depends(get_db),
):
    """Returns all captured site reports."""

    return db.scalars(
        select(SourceReport).order_by(SourceReport.received_at.desc())
    ).all()


@router.post(
    "/{report_id}/extract",
    response_model=ExtractionResponse,
    status_code=status.HTTP_201_CREATED,
)
def extract_events_from_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """
    Extracts structured progress events from a stored text report.
    A report can be extracted only once in this MVP.
    """

    report = db.get(SourceReport, report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if not report.raw_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This report has no text content to extract.",
        )

    existing_event = db.scalar(
        select(ProgressEvent).where(
            ProgressEvent.source_report_id == report_id
        )
    )

    if existing_event:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This report was already extracted.",
        )

    extracted_data = extract_progress_events(report.raw_content)

    if not extracted_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No start, completion, or progress events were found "
                "in this report."
            ),
        )

    events = [
        ProgressEvent(
            source_report_id=report_id,
            **event_data,
        )
        for event_data in extracted_data
    ]

    db.add_all(events)
    db.commit()

    for event in events:
        db.refresh(event)

    return ExtractionResponse(
        message="Progress events extracted successfully.",
        source_report_id=report_id,
        extracted_count=len(events),
        events=events,
    )


@router.get(
    "/events/all",
    response_model=list[ProgressEventResponse],
)
def list_progress_events(
    db: Session = Depends(get_db),
):
    """Returns every extracted site-progress event."""

    return db.scalars(
        select(ProgressEvent).order_by(ProgressEvent.created_at.desc())
    ).all()

def clean_sheet_value(value) -> str | None:
    """Converts empty Excel cells into None."""

    if pd.isna(value):
        return None

    text = str(value).strip()
    return text if text else None


def parse_sheet_date(value):
    """Converts Excel/CSV date into a Python date."""

    text_value = clean_sheet_value(value)

    if text_value is None:
        return None

    try:
        return pd.to_datetime(text_value).date()
    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid date '{text_value}'. Use YYYY-MM-DD."
        )


def normalize_sheet_status(value: str) -> str | None:
    """Normalizes spreadsheet status values."""

    status_value = value.strip().lower()

    status_mapping = {
        "started": "started",
        "start": "started",
        "completed": "completed",
        "complete": "completed",
        "finished": "completed",
        "in progress": "progress",
        "progress": "progress",
        "ongoing": "progress",
    }

    return status_mapping.get(status_value)


@router.post(
    "/upload-sheet",
    status_code=status.HTTP_201_CREATED,
)
async def upload_discipline_progress_sheet(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Uploads a civil/piping/electrical progress CSV or Excel sheet.
    Each spreadsheet row becomes a structured ProgressEvent.
    """

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select a CSV or Excel file.",
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
            source_type = "csv"
        else:
            dataframe = pd.read_excel(BytesIO(file_content))
            source_type = "excel"
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read the uploaded file: {error}",
        )

    dataframe.columns = [
        str(column).strip().lower()
        for column in dataframe.columns
    ]

    required_columns = {
        "discipline",
        "activity_description",
        "status",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            ),
        )

    event_data_list = []

    for row_number, row in dataframe.iterrows():
        discipline = clean_sheet_value(row["discipline"])
        description = clean_sheet_value(row["activity_description"])
        raw_status = clean_sheet_value(row["status"])

        if not discipline or not description or not raw_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Row {row_number + 2}: discipline, "
                    "activity_description, and status are required."
                ),
            )

        event_type = normalize_sheet_status(raw_status)

        if not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Row {row_number + 2}: invalid status '{raw_status}'. "
                    "Use started, completed, or progress."
                ),
            )

        try:
            event_date = parse_sheet_date(row.get("event_date"))
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row {row_number + 2}: {error}",
            )

        progress_value = row.get("progress_percent")
        progress_percent = None

        if progress_value is not None and not pd.isna(progress_value):
            try:
                progress_percent = float(progress_value)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Row {row_number + 2}: "
                        "progress_percent must be a number."
                    ),
                )

        event_data_list.append(
            {
                "discipline": discipline,
                "reported_description": description,
                "event_type": event_type,
                "event_date": event_date,
                "progress_percent": progress_percent,
            }
        )

    source_report = SourceReport(
        source_type=source_type,
        file_name=file.filename,
        raw_content=dataframe.to_csv(index=False),
    )

    db.add(source_report)
    db.flush()

    events = [
        ProgressEvent(
            source_report_id=source_report.id,
            extraction_confidence=95.0,
            **event_data,
        )
        for event_data in event_data_list
    ]

    db.add_all(events)
    db.commit()

    return {
        "message": "Discipline progress sheet uploaded successfully.",
        "source_report_id": source_report.id,
        "source_type": source_type,
        "events_created": len(events),
    }