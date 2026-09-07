from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    # supervisor, planner, admin
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="supervisor",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class ScheduleActivity(Base):
    __tablename__ = "schedule_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Example: PIP-102, CIV-045
    activity_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    # Example: Erect Line 24-XX
    activity_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    wbs_code: Mapped[Optional[str]] = mapped_column(String(100))
    wbs_level: Mapped[Optional[str]] = mapped_column(String(20))

    # civil, piping, electrical, instrumentation, HSE
    discipline: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
    )

    planned_start: Mapped[Optional[date]] = mapped_column(Date)
    planned_finish: Mapped[Optional[date]] = mapped_column(Date)

    actual_start: Mapped[Optional[date]] = mapped_column(Date)
    actual_finish: Mapped[Optional[date]] = mapped_column(Date)

    # not_started, in_progress, completed, delayed
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_started",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class SourceReport(Base):
    __tablename__ = "source_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # text, excel, csv, voice
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    raw_content: Mapped[Optional[str]] = mapped_column(Text)

    submitted_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id")
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    progress_events: Mapped[list["ProgressEvent"]] = relationship(
        back_populates="source_report"
    )


class ProgressEvent(Base):
    __tablename__ = "progress_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    source_report_id: Mapped[int] = mapped_column(
        ForeignKey("source_reports.id"),
        nullable=False,
    )

    # Original work description from site report
    # Example: "Spool erected near Unit 24"
    reported_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    discipline: Mapped[Optional[str]] = mapped_column(String(100))

    # started, completed, progress
    event_type: Mapped[Optional[str]] = mapped_column(String(50))

    event_date: Mapped[Optional[date]] = mapped_column(Date)
    progress_percent: Mapped[Optional[float]] = mapped_column(Float)

    # Confidence of data extraction, 0 to 100
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    source_report: Mapped["SourceReport"] = relationship(
        back_populates="progress_events"
    )

    matches: Mapped[list["ActivityMatch"]] = relationship(
        back_populates="progress_event"
    )


class ActivityMatch(Base):
    __tablename__ = "activity_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    progress_event_id: Mapped[int] = mapped_column(
        ForeignKey("progress_events.id"),
        nullable=False,
    )

    schedule_activity_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_activities.id"),
        nullable=False,
    )

    # 0 to 100 match confidence
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # rapidfuzz, sentence_transformer, manual
    match_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # pending, approved, rejected
    review_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id")
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    progress_event: Mapped["ProgressEvent"] = relationship(
        back_populates="matches"
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Example: schedule_activity, activity_match
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Example: created, approved, rejected, updated
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id")
    )

    old_value: Mapped[Optional[dict]] = mapped_column(JSON)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )