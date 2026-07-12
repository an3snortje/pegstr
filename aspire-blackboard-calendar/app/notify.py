"""Optional: POST a summary of new/changed dates to an n8n webhook,
so n8n can fan out to email/WhatsApp/Teams as desired."""

import logging

import requests

from .state import Diff

log = logging.getLogger(__name__)


def notify_n8n(webhook_url: str, diff: Diff) -> None:
    payload = {
        "summary": diff.summary(),
        "added": [e.to_dict() for e in diff.added],
        "changed": [{"old": old.to_dict(), "new": new.to_dict()} for old, new in diff.changed],
        "removed": [e.to_dict() for e in diff.removed],
    }
    resp = requests.post(webhook_url, json=payload, timeout=30)
    resp.raise_for_status()
    log.info("n8n webhook notified: %s", diff.summary())
