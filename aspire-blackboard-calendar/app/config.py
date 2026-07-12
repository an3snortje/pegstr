"""Environment-driven configuration. See .env.example for all settings."""

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    return int(raw) if raw else default


@dataclass
class Config:
    # --- Blackboard source ---
    # Base URL of the Blackboard Learn instance, no trailing slash.
    bb_base_url: str = field(default_factory=lambda: _env("BB_BASE_URL", "https://aspire.blackboard.com").rstrip("/"))
    # Auth mode: "login" (username/password form login), "cookie" (paste a
    # browser session cookie, required for SSO logins), or "ics" (public/secret
    # iCal feed URL from Blackboard's calendar page - simplest, use if available).
    bb_auth_mode: str = field(default_factory=lambda: _env("BB_AUTH_MODE", "login").lower())
    bb_username: str = field(default_factory=lambda: _env("BB_USERNAME"))
    bb_password: str = field(default_factory=lambda: _env("BB_PASSWORD"))
    # Raw Cookie header value for cookie mode, e.g. "BbRouter=...; JSESSIONID=..."
    bb_cookie: str = field(default_factory=lambda: _env("BB_COOKIE"))
    # iCal feed URL for ics mode (Blackboard calendar page -> "Get external calendar link")
    bb_ics_feed_url: str = field(default_factory=lambda: _env("BB_ICS_FEED_URL"))

    # How far back/forward to pull calendar items.
    days_back: int = field(default_factory=lambda: _env_int("DAYS_BACK", 7))
    days_forward: int = field(default_factory=lambda: _env_int("DAYS_FORWARD", 180))

    # --- Outputs ---
    data_dir: str = field(default_factory=lambda: _env("DATA_DIR", "data"))
    ics_output: str = field(default_factory=lambda: _env("ICS_OUTPUT", "data/aspire-critical-dates.ics"))
    state_file: str = field(default_factory=lambda: _env("STATE_FILE", "data/state.json"))

    # --- Optional: push to Outlook/M365 calendar via Microsoft Graph ---
    graph_enabled: bool = field(default_factory=lambda: _env("GRAPH_ENABLED", "false").lower() == "true")
    graph_tenant_id: str = field(default_factory=lambda: _env("GRAPH_TENANT_ID"))
    graph_client_id: str = field(default_factory=lambda: _env("GRAPH_CLIENT_ID"))
    graph_client_secret: str = field(default_factory=lambda: _env("GRAPH_CLIENT_SECRET"))
    # Mailbox to write to (client-credentials mode), e.g. andries@durbanoverall.co.za
    graph_user: str = field(default_factory=lambda: _env("GRAPH_USER"))
    graph_calendar_name: str = field(default_factory=lambda: _env("GRAPH_CALENDAR_NAME", "Aspire Blackboard"))

    # --- Optional: notify an n8n webhook when dates are added/changed ---
    n8n_webhook_url: str = field(default_factory=lambda: _env("N8N_WEBHOOK_URL"))

    # Timezone used for all-day/date-only items.
    timezone: str = field(default_factory=lambda: _env("TZ", "Africa/Johannesburg"))

    def validate(self) -> None:
        if self.bb_auth_mode == "login" and not (self.bb_username and self.bb_password):
            raise SystemExit("BB_AUTH_MODE=login requires BB_USERNAME and BB_PASSWORD")
        if self.bb_auth_mode == "cookie" and not self.bb_cookie:
            raise SystemExit("BB_AUTH_MODE=cookie requires BB_COOKIE")
        if self.bb_auth_mode == "ics" and not self.bb_ics_feed_url:
            raise SystemExit("BB_AUTH_MODE=ics requires BB_ICS_FEED_URL")
        if self.bb_auth_mode not in ("login", "cookie", "ics"):
            raise SystemExit(f"Unknown BB_AUTH_MODE: {self.bb_auth_mode}")
        if self.graph_enabled and not (
            self.graph_tenant_id and self.graph_client_id and self.graph_client_secret and self.graph_user
        ):
            raise SystemExit("GRAPH_ENABLED=true requires GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_USER")
