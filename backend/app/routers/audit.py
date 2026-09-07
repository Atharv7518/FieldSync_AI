from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogResponse


router = APIRouter(
    prefix="/api/audit-logs",
    tags=["Audit Trail"],
)


@router.get(
    "",
    response_model=list[AuditLogResponse],
)
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Returns the most recent system changes.
    This provides traceability for planner review decisions.
    """

    return db.scalars(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()