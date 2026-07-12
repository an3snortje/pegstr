"""Persist previously-seen events and diff each run against them,
so new or moved critical dates can trigger notifications."""

import json
import os
from dataclasses import dataclass, field

from .models import Event


@dataclass
class Diff:
    added: list[Event] = field(default_factory=list)
    changed: list[tuple[Event, Event]] = field(default_factory=list)  # (old, new)
    removed: list[Event] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.changed or self.removed)

    def summary(self) -> str:
        return f"{len(self.added)} new, {len(self.changed)} changed, {len(self.removed)} removed"


def load_state(path: str) -> dict[str, Event]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {uid: Event.from_dict(d) for uid, d in raw.get("events", {}).items()}


def save_state(path: str, events: list[Event], graph_ids: dict[str, str] | None = None) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "events": {e.uid: e.to_dict() for e in events},
        "graph_ids": graph_ids or {},
    }
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    os.replace(tmp, path)


def load_graph_ids(path: str) -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("graph_ids", {})


def diff_events(previous: dict[str, Event], current: list[Event]) -> Diff:
    diff = Diff()
    current_by_uid = {e.uid: e for e in current}

    for uid, event in current_by_uid.items():
        old = previous.get(uid)
        if old is None:
            diff.added.append(event)
        elif (old.start, old.end, old.title) != (event.start, event.end, event.title):
            diff.changed.append((old, event))

    for uid, old in previous.items():
        if uid not in current_by_uid:
            diff.removed.append(old)

    return diff
