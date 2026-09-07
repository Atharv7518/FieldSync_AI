from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models
from app.config import settings
from app.database import Base, engine
from app.schemas import HealthResponse

from app.routers import (
    analytics,
    audit,
    insights,
    matches,
    reports,
    reviews,
    schedule,
)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered infrastructure progress tracking API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule.router)
app.include_router(reports.router)
app.include_router(matches.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
app.include_router(insights.router)
app.include_router(audit.router)


@app.on_event("startup")
def create_database_tables() -> None:
    """Creates all Phase 1 MySQL tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


@app.get("/", tags=["System"])
def root():
    return {
        "message": "SIH Intelligent Progress Tracker API is running"
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Checks whether FastAPI can connect to MySQL."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return HealthResponse(
        status="healthy",
        database="connected",
        timestamp=datetime.now(timezone.utc),
    )