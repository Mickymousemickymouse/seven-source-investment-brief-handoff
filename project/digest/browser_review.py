"""Turn a final browser list into a reviewed receipt, only with item evidence.

The review manifest is written after a person/agent actually opens the member
pages and reads their content. This validator checks identity, pagination,
reading notes and file hashes; it cannot create reading evidence itself.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from .policy import BEIJING, X_ACCOUNTS, ZSXQ_GROUPS
from .staging import _write_json


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("review time needs an explicit timezone")
    return parsed.astimezone(BEIJING)


def _file(root: Path, record: dict, *, project_only: bool = False) -> tuple[Path, dict]:
    path = Path(record["path"])
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if project_only:
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("browser evidence must remain inside project") from exc
    if not path.is_file():
        raise ValueError(f"review evidence is missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != record.get("sha256"):
        raise ValueError(f"review evidence hash changed: {path}")
    return path, {"path": str(path), "sha256": digest}


def _native_url(source: str, item_id: str, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    path = parsed.path.rstrip("/").lower()
    if source in X_ACCOUNTS:
        return parsed.hostname == "x.com" and path == f"/{source.lower()}/status/{item_id}"
    return (parsed.hostname == "wx.zsxq.com"
            and path == f"/group/{source}/topic/{item_id}")


def _read_text(text: str, receipt: dict, captured: datetime,
               completed: datetime) -> None:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("opened body or comment text is missing")
    if receipt.get("text_sha256") != hashlib.sha256(text.encode("utf-8")).hexdigest():
        raise ValueError("body/comment reading hash does not match text")
    if not isinstance(receipt.get("notes"), str) or not receipt["notes"].strip():
        raise ValueError("body/comment has no substantive reading note")
    reviewed = _time(receipt["reviewed_at"])
    if not captured <= reviewed <= completed:
        raise ValueError("reading time is outside capture/completion interval")


def _attachment(root: Path, attachment: dict, captured: datetime,
                completed: datetime, evidence: list[dict]) -> None:
    if not attachment.get("id") or not attachment.get("filename"):
        raise ValueError("attachment lacks native identity or filename")
    if attachment.get("kind") in ("audio", "video"):
        return  # Source audio/video is outside the agreed reading scope.
    if attachment.get("excluded"):
        exclusion = attachment["excluded"]
        error = exclusion.get("browser_error")
        if error not in ("ERR_BLOCKED_BY_CLIENT", "APP_ONLY_CONTENT_PROTECTION"):
            raise ValueError("attachment exclusion lacks an approved browser reason")
        observed = _time(exclusion["observed_at"])
        if not captured <= observed <= completed:
            raise ValueError("attachment exclusion time is invalid")
        proof, record = _file(root, exclusion["proof"], project_only=True)
        proof_text = proof.read_text(encoding="utf-8")
        if error == "APP_ONLY_CONTENT_PROTECTION" and "仅支持在知识星球 App 内查看" not in proof_text:
            raise ValueError("App-only restriction is not present in browser proof")
        if error == "ERR_BLOCKED_BY_CLIENT" and error not in proof_text:
            raise ValueError("browser block is not present in browser proof")
        evidence.append(record)
        return
    if attachment.get("kind") not in ("image", "pdf"):
        raise ValueError("attachment type needs a dedicated full-unit reader")
    _, record = _file(root, attachment["file"])
    evidence.append(record)
    reading = attachment.get("read", {})
    reviewed = _time(reading["reviewed_at"])
    if not captured <= reviewed <= completed:
        raise ValueError("attachment reading time is invalid")
    units = reading.get("units")
    if (not isinstance(units, list) or not units or
            not all(isinstance(unit, dict) and unit.get("number") == index
                    and isinstance(unit.get("notes"), str) and unit["notes"].strip()
                    for index, unit in enumerate(units, 1))):
        raise ValueError("attachment lacks consecutive reviewed units")
    if reading.get("unit_count") != len(units):
        raise ValueError("attachment reading unit count does not match")
    if attachment["kind"] == "image" and len(units) != 1:
        raise ValueError("image reading must cover its original image")
    if attachment.get("kind") == "pdf":
        path = Path(record["path"])
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                info = subprocess.run(["pdfinfo", str(path)], capture_output=True,
                                      text=True, timeout=20, check=True)
            except (FileNotFoundError, subprocess.SubprocessError) as exc:
                raise ValueError("PDF page count could not be verified") from exc
            match = re.search(r"(?m)^Pages:\s*(\d+)\s*$", info.stdout)
            if match is None:
                raise ValueError("PDF page count could not be verified")
            page_count = int(match.group(1))
        else:
            page_count = len(PdfReader(str(path)).pages)
        if page_count != len(units):
            raise ValueError("PDF pages were not all reviewed")


def _comments(root: Path, detail: dict, captured: datetime,
              completed: datetime, evidence: list[dict]) -> None:
    enumeration = detail.get("comment_enumeration", {})
    comments = detail.get("comments")
    pages = detail.get("comment_pages")
    if (enumeration.get("complete") is not True or not isinstance(comments, list)
            or enumeration.get("unique_count") != len(comments)
            or not isinstance(pages, list) or not pages):
        raise ValueError("visible comment enumeration is incomplete")
    seen: set[str] = set()
    for comment in comments:
        identity = comment.get("comment_id")
        if not identity:
            basis = "\n".join(str(comment.get(key, "")) for key in
                              ("author", "published_at", "content"))
            identity = "local:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]
            if comment.get("local_id") != identity:
                raise ValueError("comment without native ID lacks labelled local dedupe ID")
        if identity in seen:
            raise ValueError("duplicate visible comment ID")
        seen.add(identity)
        _time(comment["published_at"])
        _read_text(comment.get("content"), comment.get("body_read", {}),
                   captured, completed)
        attachments = comment.get("attachments")
        if (not isinstance(attachments, list) or
                comment.get("attachment_enumeration", {}).get("complete") is not True or
                comment["attachment_enumeration"].get("count") != len(attachments)):
            raise ValueError("comment attachment enumeration is incomplete")
        for attachment in attachments:
            _attachment(root, attachment, captured, completed, evidence)
    page_ids = [item_id for page in pages for item_id in page.get("comment_ids", [])]
    if page_ids != [comment.get("comment_id") or comment["local_id"] for comment in comments]:
        raise ValueError("comment pages do not enumerate every visible comment")
    if any(pages[index].get("next_cursor") != pages[index + 1].get("cursor")
           for index in range(len(pages) - 1)):
        raise ValueError("comment pagination has a cursor gap")
    if pages[-1].get("terminal") is not True or pages[-1].get("next_cursor") is not None:
        raise ValueError("comment pagination has no visible endpoint")


def _audited_result(root: Path, imported: Path, manifest_path: Path) -> dict:
    """Recalculate a final list's item-level reading result from saved files.

    The list needs contiguous page cursors down to the 72-hour ZSXQ or 48-hour
    X lookback boundary. ZSXQ comments are checked on each lookback item. Every
    current-window item needs body and all accessible attachments reviewed.
    """
    root = root.resolve()
    imported = imported.resolve()
    record = json.loads(imported.read_text(encoding="utf-8"))
    if record.get("phase") != "final" or record.get("complete") not in (False, True):
        raise ValueError("review requires a final browser import")
    source = record["source"]
    raw_path, raw_record = _file(root, record["original"], project_only=True)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    manifest_path, manifest_record = _file(
        root, {"path": str(manifest_path),
               "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
        project_only=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source") != source or manifest.get("list_sha256") != raw_record["sha256"]:
        raise ValueError("review manifest does not match source list")
    start, end = (_time(record[key]) for key in ("window_start", "window_end"))
    captured = _time(record["captured_at"])
    completed = _time(manifest["completed_at"])
    if captured < end or completed < captured:
        raise ValueError("final reading precedes report cutoff or browser capture")
    if _time(raw["captured_at"]) != captured or raw.get("url") != record.get("observed_url"):
        raise ValueError("reviewed list differs from imported browser capture")
    home = urlparse(raw["url"])
    expected_home = (f"/{source.lower()}" if source in X_ACCOUNTS
                     else f"/group/{source}")
    if (home.scheme != "https" or home.hostname != ("x.com" if source in X_ACCOUNTS
            else "wx.zsxq.com") or home.path.rstrip("/").lower() != expected_home):
        raise ValueError("reviewed list URL does not identify the source")
    lookback = end - timedelta(hours=48 if source in X_ACCOUNTS else 72)
    cards = raw.get("cards", raw.get("articles"))
    if not isinstance(cards, list):
        raise ValueError("source list is missing")
    by_id = {}
    for card in cards:
        item_id = str(card.get("id", ""))
        if not item_id or item_id in by_id:
            raise ValueError("source list needs unique native item IDs")
        when = _time(card.get("date") or card.get("time"))
        if not _native_url(source, item_id, card.get("url", "")):
            raise ValueError("list item URL does not match source and native ID")
        by_id[item_id] = (card, when)
    if (record.get("visible_list_items") != len(cards)
            or record.get("window_list_items") != sum(start <= when < end
                                                       for _, when in by_id.values())):
        raise ValueError("reviewed list count differs from imported browser capture")
    pages = manifest.get("list_pages")
    lanes = ("posts", "replies", "reposts") if source in X_ACCOUNTS else ("timeline",)
    if not isinstance(pages, list) or not pages:
        raise ValueError("source list has no page/cursor audit")
    evidence = [raw_record, manifest_record]
    for page in pages:
        observation_path, observation_record = _file(root, page["browser_page"],
                                                     project_only=True)
        observation = json.loads(observation_path.read_text(encoding="utf-8"))
        if (observation.get("source") != source or observation.get("url") != raw["url"]
                or any(observation.get(key) != page.get(key) for key in
                       ("lane", "cursor", "next_cursor", "item_ids", "stop_reason", "terminal"))
                or not end <= _time(observation["captured_at"]) <= captured):
            raise ValueError("list page is not bound to the browser observation")
        if page.get("stop_reason") == "source_end" and not observation.get("endpoint_text", "").strip():
            raise ValueError("empty source needs observed endpoint text")
        evidence.append(observation_record)
    for lane in lanes:
        lane_pages = [page for page in pages if page.get("lane") == lane]
        if not lane_pages:
            raise ValueError(f"source lane was not checked: {lane}")
        ids = [item_id for page in lane_pages for item_id in page.get("item_ids", [])]
        expected = [item_id for item_id, (card, _) in by_id.items()
                    if card.get("lane", "timeline") == lane]
        if ids != expected:
            raise ValueError(f"list page IDs do not match visible cards: {lane}")
        if any(lane_pages[index].get("next_cursor") != lane_pages[index + 1].get("cursor")
               for index in range(len(lane_pages) - 1)):
            raise ValueError(f"source list has a cursor gap: {lane}")
        final_page = lane_pages[-1]
        if final_page.get("stop_reason") == "older_than_lookback":
            if not any(by_id[item_id][1] < lookback for item_id in final_page.get("item_ids", [])):
                raise ValueError(f"lookback boundary not observed: {lane}")
        elif final_page.get("stop_reason") != "source_end" or final_page.get("terminal") is not True:
            raise ValueError(f"source list has no exhaustive endpoint: {lane}")
        if final_page.get("stop_reason") == "source_end" and final_page.get("next_cursor") is not None:
            raise ValueError(f"source end still has a next cursor: {lane}")
    if any(page.get("lane") not in lanes for page in pages):
        raise ValueError("unexpected source lane")
    required = {item_id for item_id, (_, when) in by_id.items() if lookback <= when < end}
    details = manifest.get("details")
    if not isinstance(details, dict) or not required.issubset(details):
        raise ValueError("some lookback items lack opened-detail evidence")
    exclusions = []
    for item_id in sorted(required):
        detail_path, detail_record = _file(root, details[item_id], project_only=True)
        evidence.append(detail_record)
        detail = json.loads(detail_path.read_text(encoding="utf-8"))
        card, when = by_id[item_id]
        detail_captured = _time(detail["captured_at"])
        if (detail.get("item_id") != item_id
                or not _native_url(source, item_id, detail.get("url", ""))
                or _time(detail["published_at"]) != when
                or detail_captured < when or detail_captured > completed):
            raise ValueError("opened detail does not match listed native item")
        if start <= when < end:
            _read_text(detail.get("body"), detail.get("body_read", {}),
                       detail_captured, completed)
        if source in ZSXQ_GROUPS:
            _comments(root, detail, detail_captured, completed, evidence)
        attachments = detail.get("attachments")
        if not isinstance(attachments, list) or detail.get("attachment_count") != len(attachments):
            raise ValueError("opened detail has no complete attachment enumeration")
        for attachment in attachments:
            _attachment(root, attachment, detail_captured, completed, evidence)
            if attachment.get("excluded"):
                exclusions.append({"item_id": item_id, "filename": attachment["filename"],
                                   "reason": attachment["excluded"]["browser_error"]})
    return {**record, "complete": True, "issues": [],
              "reviewed_at": completed.isoformat(),
              "reviewed_lookback_items": len(required),
              "excluded_attachments": exclusions,
              "review_manifest": manifest_record,
              "evidence_files": evidence,
              "limitations": ["网页不提供后台评论总数或原生评论ID时，仅证明网页可见评论。"]
              if source in ZSXQ_GROUPS else []}


def complete_snapshot(root: Path, imported: Path, manifest_path: Path) -> Path:
    """Promote a partial list only after its saved detail evidence passes audit."""
    if json.loads(imported.read_text(encoding="utf-8")).get("complete") is not False:
        raise ValueError("review requires a partial final browser import")
    result = _audited_result(root, imported, manifest_path)
    _write_json(imported, result)
    return imported


def verify_complete_snapshot(root: Path, imported: Path) -> dict:
    """Repeat the full audit at delivery, catching edited or lost evidence."""
    record = json.loads(imported.read_text(encoding="utf-8"))
    if record.get("complete") is not True or not record.get("review_manifest"):
        raise ValueError("list-only browser capture cannot finalize")
    manifest, _ = _file(root, record["review_manifest"], project_only=True)
    expected = _audited_result(root, imported, manifest)
    if expected != record:
        raise ValueError("reviewed browser receipt changed after audit")
    return record
