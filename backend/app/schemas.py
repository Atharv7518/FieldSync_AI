from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from typing import Literal, Optional


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime


class ScheduleActivityCreate(BaseModel):
    activity_code: str = Field(
        min_length=1,
        max_length=100,
        examples=["PIP-102"],
    )

    activity_name: str = Field(
        min_length=1,
        max_length=500,
        examples=["Erect Line 24-XX"],
    )

    wbs_code: Optional[str] = None
    wbs_level: Optional[str] = None
    discipline: Optional[str] = None
    planned_start: Optional[date] = None
    planned_finish: Optional[date] = None


class ScheduleActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_code: str
    activity_name: str
    wbs_code: Optional[str]
    wbs_level: Optional[str]
    discipline: Optional[str]
    planned_start: Optional[date]
    planned_finish: Optional[date]
    actual_start: Optional[date]
    actual_finish: Optional[date]
    status: str
    created_at: datetime


class ScheduleImportResponse(BaseModel):
    message: str
    imported_count: int
    skipped_duplicate_count: int
    total_rows: int


class SourceReportCreate(BaseModel):
    source_type: str = Field(
        default="text",
        examples=["text"],
    )

    raw_content: str = Field(
        min_length=5,
        examples=[
            "Piping team completed spool erection near Unit 24 today."
        ],
    )


class SourceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    file_name: Optional[str]
    raw_content: Optional[str]
    submitted_by_id: Optional[int]
    received_at: datetime


class ProgressEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_report_id: int
    reported_description: str
    discipline: Optional[str]
    event_type: Optional[str]
    event_date: Optional[date]
    progress_percent: Optional[float]
    extraction_confidence: Optional[float]
    created_at: datetime


class ExtractionResponse(BaseModel):
    message: str
    source_report_id: int
    extracted_count: int
    events: list[ProgressEventResponse]

class ActivityMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    progress_event_id: int
    schedule_activity_id: int
    confidence_score: float
    match_method: str
    review_status: str
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]


class MatchResultResponse(BaseModel):
    message: str
    event_id: int
    reported_description: str
    suggested_activity_code: str
    suggested_activity_name: str
    discipline: Optional[str]
    confidence_score: float
    review_status: str
    match: ActivityMatchResponse

class MatchReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class MatchReviewResponse(BaseModel):
    message: str
    match_id: int
    review_status: str
    schedule_activity_id: int
    actual_start: Optional[date]
    actual_finish: Optional[date]
    activity_status: str

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_id: Optional[int]
    old_value: Optional[dict]
    new_value: Optional[dict]
    created_at: datetime