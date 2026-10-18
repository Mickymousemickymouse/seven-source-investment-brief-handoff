"""Ingest one real browser-tool export; never run a substitute network scraper.

Run from the project after saving a logged-in Chrome page snapshot as JSON.
Preparation imports are attached to the 08:00/20:00 checkpoint. Final imports
remain list evidence until detail, comments and attachments are reviewed.
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from digest.browser_bridge import import_snapshot, save_browser_preparation
from digest.browser_review import complete_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    parser.add_argument("--edition", choices=("morning", "evening"), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--phase", choices=("preparation", "final"), required=True)
    parser.add_argument("--prepared-at", type=datetime.fromisoformat)
    parser.add_argument("--review-manifest", type=Path,
                        help="final-only opened-detail, comment and attachment reading evidence")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parent
    if arguments.phase == "preparation":
        if arguments.review_manifest is not None:
            parser.error("review manifest is only accepted in the final phase")
        if arguments.prepared_at is None:
            parser.error("--prepared-at with timezone is required for preparation")
        checkpoint = save_browser_preparation(
            root, arguments.day, arguments.edition, arguments.prepared_at,
            {arguments.source: arguments.snapshot},
        )
        records = json.loads(checkpoint.read_text(encoding="utf-8"))["evidence"][arguments.source]
        imported = root / next(record["path"] for record in records
                               if record["path"].endswith(f"/{arguments.source}.json"))
    else:
        imported = import_snapshot(root, arguments.day, arguments.edition,
                                   arguments.source, arguments.snapshot, "final")
        if arguments.review_manifest is not None:
            complete_snapshot(root, imported, arguments.review_manifest)
    record = json.loads(imported.read_text(encoding="utf-8"))
    print(json.dumps({"record": str(imported), "source": arguments.source,
                      "window_list_items": record["window_list_items"],
                      "complete": record["complete"], "issues": record["issues"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
