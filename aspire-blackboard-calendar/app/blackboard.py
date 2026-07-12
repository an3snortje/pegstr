"""Fetch critical dates from Blackboard Learn.

Three strategies, picked by BB_AUTH_MODE:

  ics    - fetch the iCal feed Blackboard exposes on its calendar page.
           No login needed once you have the (secret) feed URL. Most robust.
  login  - form login against /webapps/login/, then call the calendar REST API.
           Works for local Blackboard accounts, not for SSO/SAML logins.
  cookie - reuse a browser session cookie, then call the calendar REST API.
           Use this when the institution logs in via SSO.

The REST API used is the same one the Blackboard web calendar uses:
GET /learn/api/public/v1/calendars/items — returns course events, institution
events and gradebook due dates in one paged list.
"""

import logging
from datetime import datetime, timedelta, timezone

import requests
from icalendar import Calendar as ICal

from .config import Config
from .models import Event, iso_utc

log = logging.getLogger(__name__)

UA = "aspire-blackboard-calendar/1.0"


class BlackboardClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA

    # ------------------------------------------------------------------ auth

    def _login(self) -> None:
        cfg = self.cfg
        if cfg.bb_auth_mode == "cookie":
            self.session.headers["Cookie"] = cfg.bb_cookie
            return

        # Classic Blackboard form login. Fetch the login page first so any
        # nonce/one-time-token hidden fields can be replayed.
        login_page = self.session.get(f"{cfg.bb_base_url}/webapps/login/", timeout=30)
        login_page.raise_for_status()

        payload = {
            "user_id": cfg.bb_username,
            "password": cfg.bb_password,
            "login": "Login",
            "action": "login",
            "new_loc": "",
        }
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(login_page.text, "html.parser")
            form = soup.find("form", attrs={"name": "login"}) or soup.find("form")
            if form:
                for hidden in form.find_all("input", attrs={"type": "hidden"}):
                    name = hidden.get("name")
                    if name and name not in payload:
                        payload[name] = hidden.get("value", "")
        except Exception:  # noqa: BLE001 - hidden-field replay is best effort
            pass

        resp = self.session.post(f"{cfg.bb_base_url}/webapps/login/", data=payload, timeout=30)
        resp.raise_for_status()
        if "bad_stale_request" in resp.url or "You are not logged in" in resp.text:
            raise SystemExit(
                "Blackboard login failed. If Aspire uses SSO, use BB_AUTH_MODE=cookie "
                "or BB_AUTH_MODE=ics instead (see README)."
            )

    # --------------------------------------------------------------- fetchers

    def fetch(self) -> list[Event]:
        if self.cfg.bb_auth_mode == "ics":
            return self._fetch_ics_feed()
        self._login()
        return self._fetch_rest_calendar()

    def _fetch_ics_feed(self) -> list[Event]:
        resp = self.session.get(self.cfg.bb_ics_feed_url, timeout=60)
        resp.raise_for_status()
        cal = ICal.from_ical(resp.content)
        events: list[Event] = []
        for comp in cal.walk("VEVENT"):
            start = comp.get("dtstart").dt
            end_prop = comp.get("dtend")
            end = end_prop.dt if end_prop else start
            all_day = not isinstance(start, datetime)
            if all_day:
                start = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
                end = datetime(end.year, end.month, end.day, tzinfo=timezone.utc)
            events.append(
                Event(
                    uid=str(comp.get("uid", "")),
                    title=str(comp.get("summary", "")),
                    start=iso_utc(start),
                    end=iso_utc(end),
                    all_day=all_day,
                    location=str(comp.get("location", "") or ""),
                    description=str(comp.get("description", "") or ""),
                    event_type="IcsFeed",
                )
            )
        log.info("Fetched %d events from ICS feed", len(events))
        return events

    def _fetch_rest_calendar(self) -> list[Event]:
        cfg = self.cfg
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=cfg.days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        until = (now + timedelta(days=cfg.days_forward)).strftime("%Y-%m-%dT%H:%M:%SZ")

        url = f"{cfg.bb_base_url}/learn/api/public/v1/calendars/items"
        params: dict = {"since": since, "until": until, "limit": 200}
        events: list[Event] = []

        while True:
            resp = self.session.get(url, params=params, timeout=60)
            if resp.status_code in (401, 403):
                raise SystemExit(
                    f"Calendar API returned {resp.status_code}. Session cookie expired or "
                    "the login did not stick — refresh BB_COOKIE, or switch to BB_AUTH_MODE=ics."
                )
            resp.raise_for_status()
            body = resp.json()
            for item in body.get("results", []):
                events.append(self._normalise_rest_item(item))
            next_page = body.get("paging", {}).get("nextPage")
            if not next_page:
                break
            url = f"{cfg.bb_base_url}{next_page}"
            params = {}

        log.info("Fetched %d events from calendar REST API", len(events))
        return events

    @staticmethod
    def _normalise_rest_item(item: dict) -> Event:
        start = item.get("start") or item.get("end") or ""
        end = item.get("end") or start
        return Event(
            uid=item.get("id", ""),
            title=item.get("title", "(untitled)"),
            start=iso_utc(datetime.fromisoformat(start.replace("Z", "+00:00"))),
            end=iso_utc(datetime.fromisoformat(end.replace("Z", "+00:00"))),
            all_day=bool(item.get("disableAllDay") is False and item.get("allDay", False)),
            course=item.get("calendarName", ""),
            event_type=item.get("type", ""),
            location=item.get("location", "") or "",
            description=item.get("description", "") or "",
        )
