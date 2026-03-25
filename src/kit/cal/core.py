"""Calendar event data models."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, computed_field


class CalendarEvent(BaseModel):
    title: str
    start: datetime | None = None
    duration_minutes: int = 60
    location: str | None = None
    description: str | None = None
    calendar_id: str = "primary"
    all_day: bool = False
    date: str | None = None  # YYYY-MM-DD for all-day events

    @computed_field
    @property
    def end(self) -> datetime | None:
        if self.start:
            return self.start + timedelta(minutes=self.duration_minutes)
        return None


class TravelBuffer(BaseModel):
    title: str
    start: datetime
    end: datetime
    description: str = ""
    calendar_id: str = "primary"
