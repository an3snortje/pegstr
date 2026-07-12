"""Normalised event model shared by all fetchers and outputs."""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class Event:
    uid: str                 # stable id from the source system
    title: str
    start: str               # ISO 8601 UTC, e.g. "2026-08-01T08:00:00+00:00"
    end: str                 # ISO 8601 UTC
    all_day: bool = False
    course: str = ""         # course/calendar the event belongs to
    event_type: str = ""     # e.g. GradebookColumn (due date), Course, Institution
    location: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Event":
        return Event(**d)

    def start_dt(self) -> datetime:
        return datetime.fromisoformat(self.start)

    def end_dt(self) -> datetime:
        return datetime.fromisoformat(self.end)


def iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
