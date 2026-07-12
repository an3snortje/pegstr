"""Write the normalised events out as an .ics file that any calendar app
(Outlook, Google, phone) can import or subscribe to."""

import os

from icalendar import Calendar, Event as ICalEvent

from .models import Event


def write_ics(events: list[Event], path: str) -> None:
    cal = Calendar()
    cal.add("prodid", "-//aspire-blackboard-calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Aspire Blackboard — Critical Dates")

    for e in events:
        item = ICalEvent()
        item.add("uid", f"{e.uid}@aspire-blackboard-calendar")
        title = f"[{e.course}] {e.title}" if e.course else e.title
        item.add("summary", title)
        if e.all_day:
            item.add("dtstart", e.start_dt().date())
            item.add("dtend", e.end_dt().date())
        else:
            item.add("dtstart", e.start_dt())
            item.add("dtend", e.end_dt())
        if e.location:
            item.add("location", e.location)
        if e.description:
            item.add("description", e.description)
        if e.event_type:
            item.add("categories", e.event_type)
        cal.add_component(item)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(cal.to_ical())
