"""Entry point.

    python -m app.main                # single run
    python -m app.main --interval 60  # run forever, every 60 minutes

Pipeline: fetch from Blackboard -> diff against last run -> write .ics ->
(optional) push to Outlook via Graph -> (optional) notify n8n webhook -> save state.
"""

import argparse
import logging
import time

from .blackboard import BlackboardClient
from .config import Config
from .ics_writer import write_ics
from .state import diff_events, load_graph_ids, load_state, save_state

log = logging.getLogger("aspire")


def run_once(cfg: Config) -> None:
    events = BlackboardClient(cfg).fetch()

    previous = load_state(cfg.state_file)
    diff = diff_events(previous, events)
    log.info("Diff vs last run: %s", diff.summary())

    write_ics(events, cfg.ics_output)
    log.info("Wrote %d events to %s", len(events), cfg.ics_output)

    graph_ids = load_graph_ids(cfg.state_file)
    if cfg.graph_enabled:
        from .graph_sync import GraphSync

        graph_ids = GraphSync(cfg).sync(events, graph_ids)

    if cfg.n8n_webhook_url and not diff.is_empty:
        from .notify import notify_n8n

        notify_n8n(cfg.n8n_webhook_url, diff)

    save_state(cfg.state_file, events, graph_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Aspire Blackboard critical dates to a calendar")
    parser.add_argument("--interval", type=int, default=0, metavar="MINUTES",
                        help="run continuously at this interval (default: run once and exit)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    cfg = Config()
    cfg.validate()

    if args.interval <= 0:
        run_once(cfg)
        return

    while True:
        try:
            run_once(cfg)
        except SystemExit:
            raise
        except Exception:  # noqa: BLE001 - keep the scheduler alive on transient errors
            log.exception("Run failed; retrying at next interval")
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
