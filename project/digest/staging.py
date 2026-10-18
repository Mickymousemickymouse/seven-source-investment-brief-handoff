"""Durable 08:00/20:00 preparation and 09:00/21:00 delivery gate.

This module records reading evidence; it does not collect browser content or
turn a source list into proof that the articles and attachments were read.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from .audio import narration_text
from .policy import BEIJING, SEVEN_SOURCES, complete_delivery, report_issues, report_window


def _in_root(root: Path, path: Path) -> tuple[str, Path]:
    root = root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"evidence is outside project: {path}") from exc
    if not resolved.is_file():
        raise ValueError(f"evidence file is missing: {path}")
    return relative.as_posix(), resolved


def _file_record(root: Path, path: Path) -> dict:
    relative, resolved = _in_root(root, path)
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": relative, "sha256": digest.hexdigest()}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp",
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def checkpoint_path(root: Path, day: date, edition: str, phase: str) -> Path:
    if phase not in ("preparation", "final"):
        raise ValueError("phase must be preparation or final")
    _, end = report_window(day, edition)
    return root / "work" / f"{day.isoformat()}-{end:%H%M}-{phase}.json"


def save_preparation(root: Path, day: date, edition: str, prepared_at: datetime,
                     source_files: dict[str, list[Path]], draft: Path | None = None) -> Path:
    """Save available source evidence and a draft; this never marks delivery complete."""
    start, end = report_window(day, edition)
    prep_start = end - timedelta(hours=1)
    if prepared_at.tzinfo is None or not prep_start <= prepared_at.astimezone(BEIJING) < end:
        raise ValueError("preparation time must fall in the final hour before delivery")
    if set(source_files) - set(SEVEN_SOURCES):
        raise ValueError("unknown source in preparation")
    path = checkpoint_path(root, day, edition, "preparation")
    prior = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    if prior and (prior.get("phase"), prior.get("day"), prior.get("edition"),
                  prior.get("window_start"), prior.get("window_end")) != (
                      "preparation_not_delivery", day.isoformat(), edition,
                      start.isoformat(), end.isoformat()):
        raise ValueError("existing preparation belongs to another window")
    evidence = dict(prior["evidence"]) if prior else {}
    for source, paths in source_files.items():
        existing = {record["path"]: record for record in evidence.get(source, [])}
        for file in paths:
            record = _file_record(root, file)
            existing[record["path"]] = record
        evidence[source] = list(existing.values())
    value = {
        "phase": "preparation_not_delivery", "day": day.isoformat(),
        "edition": edition, "window_start": start.isoformat(),
        "prep_start": prep_start.isoformat(), "window_end": end.isoformat(),
        "prepared_at": prepared_at.astimezone(BEIJING).isoformat(),
        "evidence": evidence,
        "missing_sources": sorted(source for source in SEVEN_SOURCES if not evidence.get(source)),
        "draft": _file_record(root, draft) if draft is not None else
                 (prior.get("draft") if prior else None),
    }
    _write_json(path, value)
    return path


def finalize(root: Path, day: date, edition: str, finished_at: datetime,
             refreshes: dict[str, dict], coverage: dict, audio: dict,
             report: Path, audio_file: Path) -> Path:
    """Write a final checkpoint only after all seven sources are refreshed.

    Each refresh needs a post-cutoff list snapshot with a real captured_at and
    explicit old-topic, comment, and attachment recheck results. The ordinary
    coverage and audio gate still applies independently.
    """
    start, end = report_window(day, edition)
    prep_path = checkpoint_path(root, day, edition, "preparation")
    if not prep_path.is_file():
        raise ValueError("preparation checkpoint is missing")
    prep = json.loads(prep_path.read_text(encoding="utf-8"))
    if (prep.get("phase"), prep.get("day"), prep.get("edition"),
        prep.get("window_start"), prep.get("window_end")) != (
            "preparation_not_delivery", day.isoformat(), edition,
            start.isoformat(), end.isoformat()):
        raise ValueError("preparation checkpoint belongs to another window")
    if finished_at.tzinfo is None or finished_at.astimezone(BEIJING) < end:
        raise ValueError("finalization is before the report cutoff")

    invalidated = []
    for source, records in prep["evidence"].items():
        for record in records:
            path = root / record["path"]
            if not path.is_file() or _file_record(root, path)["sha256"] != record["sha256"]:
                invalidated.append(source)
                break

    if set(refreshes) != set(SEVEN_SOURCES):
        raise ValueError("all seven sources need a final refresh")
    refreshed = {}
    for source in SEVEN_SOURCES:
        refresh = refreshes[source]
        if not all(refresh.get(key) for key in (
            "previous_items_rechecked", "comments_rechecked", "attachments_rechecked"
        )):
            raise ValueError(f"old topics, comments or attachments not rechecked: {source}")
        snapshot = Path(refresh["list_snapshot"])
        _in_root(root, snapshot)
        from .browser_review import verify_complete_snapshot
        data = verify_complete_snapshot(root, snapshot)
        if data.get("source") != source or data.get("window_start") != start.isoformat() or data.get("window_end") != end.isoformat():
            raise ValueError(f"reviewed browser source or window does not match: {source}")
        captured = datetime.fromisoformat(data["captured_at"])
        if (captured.tzinfo is None or captured.astimezone(BEIJING) < end
                or captured.astimezone(BEIJING) > finished_at.astimezone(BEIJING)):
            raise ValueError(f"final list boundary is not post-cutoff: {source}")
        refreshed[source] = {**_file_record(root, snapshot),
                             "captured_at": captured.astimezone(BEIJING).isoformat(),
                             "previous_items_rechecked": True,
                             "comments_rechecked": True,
                             "attachments_rechecked": True}

    if not complete_delivery(coverage, audio):
        raise ValueError("seven-source reading, announcements or audio gate failed")
    _in_root(root, report)
    text = report.read_text(encoding="utf-8")
    issues = report_issues(text)
    if issues:
        raise ValueError("report QA failed: " + "; ".join(issues))
    if audio.get("narration_sha256") != hashlib.sha256(
            narration_text(text).encode("utf-8")).hexdigest():
        raise ValueError("audio narration does not match report body")
    audio_record = _file_record(root, audio_file)
    if audio_record["sha256"] != audio.get("audio_sha256"):
        raise ValueError("audio file does not match its verified receipt")

    value = {
        "phase": "final_checked", "day": day.isoformat(), "edition": edition,
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "finished_at": finished_at.astimezone(BEIJING).isoformat(),
        "preparation": _file_record(root, prep_path),
        "invalidated_preparation_sources_rechecked": sorted(set(invalidated)),
        "final_source_snapshots": refreshed,
        "report": _file_record(root, report), "coverage": coverage,
        "audio": audio, "audio_file": audio_record,
    }
    path = checkpoint_path(root, day, edition, "final")
    _write_json(path, value)
    return path
