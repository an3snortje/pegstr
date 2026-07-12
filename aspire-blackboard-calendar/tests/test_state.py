from app.models import Event
from app.state import diff_events, load_state, save_state


def make(uid: str, title: str = "Exam", start: str = "2026-08-01T08:00:00+00:00") -> Event:
    return Event(uid=uid, title=title, start=start, end=start)


def test_diff_detects_added_changed_removed():
    previous = {"a": make("a"), "b": make("b"), "c": make("c")}
    current = [
        make("a"),                                          # unchanged
        make("b", start="2026-08-02T08:00:00+00:00"),       # moved
        make("d"),                                          # new
    ]
    diff = diff_events(previous, current)
    assert [e.uid for e in diff.added] == ["d"]
    assert [(o.uid, n.uid) for o, n in diff.changed] == [("b", "b")]
    assert [e.uid for e in diff.removed] == ["c"]
    assert not diff.is_empty
    assert diff.summary() == "1 new, 1 changed, 1 removed"


def test_diff_empty_when_nothing_changed():
    previous = {"a": make("a")}
    assert diff_events(previous, [make("a")]).is_empty


def test_state_roundtrip(tmp_path):
    path = str(tmp_path / "state.json")
    events = [make("a"), make("b")]
    save_state(path, events, {"a": "graph-id-1"})
    loaded = load_state(path)
    assert set(loaded) == {"a", "b"}
    assert loaded["a"].title == "Exam"
