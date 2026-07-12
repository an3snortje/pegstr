# aspire-blackboard-calendar

Pulls critical dates (assignment due dates, exams, course/institution events) from the
Aspire Blackboard Learn instance and keeps you informed:

1. Writes an **`.ics` calendar file** you can import/subscribe to from Outlook, Google Calendar or your phone.
2. *(Optional)* **Pushes events into an Outlook/M365 calendar** via Microsoft Graph — events appear automatically with a 1-day reminder, and moved dates are updated in place.
3. *(Optional)* **Notifies an n8n webhook** whenever dates are added, moved or removed, so you can fan out to email/WhatsApp/Teams.

State is tracked between runs, so you only get notified about *changes*.

## Quick start

```bash
cp .env.example .env      # fill in Blackboard access (see below)
docker compose up -d      # runs every 60 minutes
# or locally:
pip install -r requirements.txt
python -m app.main -v     # single run
```

Output lands in `data/aspire-critical-dates.ics`.

## Getting access to Blackboard (pick ONE, set `BB_AUTH_MODE`)

| Mode | When to use | Setup |
|---|---|---|
| `ics` **(recommended)** | Blackboard's calendar page offers an external calendar / iCal link | Log in via browser → Calendar → settings/share → copy the iCal URL into `BB_ICS_FEED_URL`. No password stored. |
| `cookie` | Aspire logs you in via SSO (Microsoft/Google) | Log in via browser → dev tools → Network → copy the `Cookie` request header into `BB_COOKIE`. Needs refreshing when the session expires. |
| `login` | Local Blackboard username/password (no SSO) | Set `BB_USERNAME` / `BB_PASSWORD`. |

In `cookie`/`login` mode the app calls Blackboard's own calendar REST API
(`/learn/api/public/v1/calendars/items`), which returns due dates, course events and
institution events in one list.

## Optional: sync into Outlook (Microsoft Graph)

1. Azure Portal → App registrations → new app.
2. API permissions → Microsoft Graph → **Application** → `Calendars.ReadWrite` → grant admin consent.
3. Certificates & secrets → new client secret.
4. In `.env`: `GRAPH_ENABLED=true` plus `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_USER`.

A dedicated calendar (default **"Aspire Blackboard"**) is created on the mailbox; the app
upserts into it, so re-runs never duplicate and moved dates are corrected in place.

## Optional: n8n change notifications

Set `N8N_WEBHOOK_URL`. On any change the app POSTs:

```json
{
  "summary": "2 new, 1 changed, 0 removed",
  "added":   [ { "uid": "...", "title": "...", "start": "...", "...": "..." } ],
  "changed": [ { "old": { }, "new": { } } ],
  "removed": [ ]
}
```

## Tests

```bash
pip install pytest && python -m pytest
```

## Moving this into its own repository

This project was developed inside `pegstr` because the automation session could not
create repositories. To split it out (from a machine with full GitHub access):

```bash
# 1. create the empty repo (GitHub UI, or: gh repo create an3snortje/aspire-blackboard-calendar --private)
# 2. push just this folder's contents:
git clone --branch claude/aspire-blackboard-calendar-elwirq https://github.com/an3snortje/pegstr tmp-split
cd tmp-split/aspire-blackboard-calendar
git init -b main && git add -A && git commit -m "Initial import"
git remote add origin https://github.com/an3snortje/aspire-blackboard-calendar.git
git push -u origin main
```

## Layout

```
app/
  main.py        entry point / scheduler loop
  config.py      env-driven configuration
  blackboard.py  fetchers: iCal feed, or REST calendar API behind login/cookie auth
  state.py       state persistence + change detection (new/moved/removed dates)
  ics_writer.py  .ics output
  graph_sync.py  optional Outlook push via Microsoft Graph
  notify.py      optional n8n webhook notification
tests/
```
