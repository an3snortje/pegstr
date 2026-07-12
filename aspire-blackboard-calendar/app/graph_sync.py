"""Optional: push events straight into an Outlook/M365 calendar via
Microsoft Graph (client-credentials app registration).

Required Graph application permission: Calendars.ReadWrite (admin consent).
Events are upserted into a dedicated calendar (GRAPH_CALENDAR_NAME) on the
GRAPH_USER mailbox; source uid -> Graph event id mapping lives in the state
file so re-runs update instead of duplicating.
"""

import logging

import requests

from .config import Config
from .models import Event

log = logging.getLogger(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"


class GraphSync:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._token: str | None = None
        self._calendar_id: str | None = None

    # ------------------------------------------------------------------ auth

    def _headers(self) -> dict:
        if self._token is None:
            import msal

            app = msal.ConfidentialClientApplication(
                self.cfg.graph_client_id,
                authority=f"https://login.microsoftonline.com/{self.cfg.graph_tenant_id}",
                client_credential=self.cfg.graph_client_secret,
            )
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            if "access_token" not in result:
                raise SystemExit(f"Graph auth failed: {result.get('error_description', result)}")
            self._token = result["access_token"]
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    # -------------------------------------------------------------- calendar

    def _calendar(self) -> str:
        if self._calendar_id:
            return self._calendar_id
        base = f"{GRAPH}/users/{self.cfg.graph_user}/calendars"
        resp = requests.get(base, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        for cal in resp.json().get("value", []):
            if cal["name"].lower() == self.cfg.graph_calendar_name.lower():
                self._calendar_id = cal["id"]
                return self._calendar_id
        resp = requests.post(base, headers=self._headers(), json={"name": self.cfg.graph_calendar_name}, timeout=30)
        resp.raise_for_status()
        self._calendar_id = resp.json()["id"]
        log.info("Created Outlook calendar '%s'", self.cfg.graph_calendar_name)
        return self._calendar_id

    # ---------------------------------------------------------------- upsert

    def sync(self, events: list[Event], graph_ids: dict[str, str]) -> dict[str, str]:
        """Upsert all events; returns the updated uid -> graph event id map."""
        cal_id = self._calendar()
        base = f"{GRAPH}/users/{self.cfg.graph_user}/calendars/{cal_id}/events"
        updated_map: dict[str, str] = {}

        for e in events:
            body = self._event_body(e)
            graph_id = graph_ids.get(e.uid)
            if graph_id:
                resp = requests.patch(f"{base}/{graph_id}", headers=self._headers(), json=body, timeout=30)
                if resp.status_code == 404:  # deleted manually in Outlook - recreate
                    graph_id = None
                else:
                    resp.raise_for_status()
            if not graph_id:
                resp = requests.post(base, headers=self._headers(), json=body, timeout=30)
                resp.raise_for_status()
                graph_id = resp.json()["id"]
            updated_map[e.uid] = graph_id

        # Remove Outlook events whose source event disappeared.
        for uid, graph_id in graph_ids.items():
            if uid not in updated_map:
                requests.delete(f"{base}/{graph_id}", headers=self._headers(), timeout=30)

        log.info("Graph sync complete: %d events upserted", len(updated_map))
        return updated_map

    def _event_body(self, e: Event) -> dict:
        title = f"[{e.course}] {e.title}" if e.course else e.title
        if e.all_day:
            start = {"dateTime": e.start_dt().date().isoformat() + "T00:00:00", "timeZone": self.cfg.timezone}
            end_date = max(e.end_dt().date(), e.start_dt().date())
            end = {"dateTime": end_date.isoformat() + "T00:00:00", "timeZone": self.cfg.timezone}
        else:
            start = {"dateTime": e.start_dt().isoformat(), "timeZone": "UTC"}
            end = {"dateTime": e.end_dt().isoformat(), "timeZone": "UTC"}
        return {
            "subject": title,
            "body": {"contentType": "text", "content": e.description or ""},
            "start": start,
            "end": end,
            "isAllDay": e.all_day,
            "location": {"displayName": e.location} if e.location else {"displayName": ""},
            "categories": [e.event_type] if e.event_type else [],
            "isReminderOn": True,
            "reminderMinutesBeforeStart": 24 * 60,
        }
