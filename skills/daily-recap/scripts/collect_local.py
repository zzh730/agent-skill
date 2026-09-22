#!/usr/bin/env python3
"""Collect local visible session evidence and Shadow indexes without source writes."""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
TOOL_LIMIT = 6000


def timestamp(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(value / 1000 if value > 1e11 else value, UTC)
        text = str(value).strip().strip('"\'')
        if text.endswith(" UTC"):
            text = text[:-4].replace(" ", "T") + "+00:00"
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def window(date, timezone, as_of=None):
    zone = ZoneInfo(timezone)
    cutoff = timestamp(as_of) if as_of else dt.datetime.now(UTC)
    if cutoff is None:
        raise ValueError("--as-of must be an ISO timestamp with a timezone")
    day = dt.date.fromisoformat(date) if date else cutoff.astimezone(zone).date()
    start = dt.datetime.combine(day, dt.time.min, zone).astimezone(UTC)
    end = min(dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, zone).astimezone(UTC), cutoff)
    if end <= start:
        raise ValueError("Requested date starts at or after the cutoff")
    return day.isoformat(), start, end


def redact(text):
    # Best effort only; keep artifacts private and inspect before sharing.
    text = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,}|xox[baprs]-[A-Za-z0-9-]{12,})\b", "[REDACTED]", text)
    return text


def visible_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(visible_text(x) for x in content if isinstance(x, (dict, str)))
    if isinstance(content, dict):
        if content.get("type") in {"thinking", "reasoning", "redacted_thinking"}:
            return ""
        for key in ("text", "output", "content"):
            if key in content:
                return visible_text(content[key])
    return ""


def compact(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


class Collector:
    def __init__(self, home, shadow, output, date, timezone, as_of=None, exclude=()):
        self.home, self.shadow, self.output = Path(home), Path(shadow), Path(output)
        self.day, self.start, self.end = window(date, timezone, as_of)
        self.exclude = set(exclude)
        self.sessions, self.meetings = [], []
        self.errors = []
        self.coverage = {}
        self.manifest = {
            "schema_version": 1, "date": self.day, "timezone": timezone,
            "start": self.start.isoformat(), "end_exclusive": self.end.isoformat(),
            "generated_at": dt.datetime.now(UTC).isoformat(), "sources": self.coverage,
            "errors": self.errors, "semantic_review": "not_started",
            "remote_cloud_coverage": "not_checked_by_local_collector",
            "slack_coverage": "not_checked_by_local_collector",
            "privacy": "Local artifacts; redaction is best effort. Do not publish raw evidence.",
        }
        self.output.mkdir(parents=True, exist_ok=False, mode=0o700)
        (self.output / "sessions").mkdir(mode=0o700)

    def error(self, source, path, message):
        self.errors.append({"source": source, "path": str(path), "error": str(message)})

    def rows(self, source, path):
        try:
            with path.open(encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError("Expected a JSON object")
                        yield line_number, row
                    except (ValueError, TypeError) as exc:
                        self.error(source, f"{path}:{line_number}", exc)
        except (OSError, UnicodeError) as exc:
            self.error(source, path, exc)

    def event(self, when, role, text, ref, **extra):
        time = timestamp(when)
        if not text:
            return None
        if time is None:
            self.error("unplaced_timestamp", ref.get("path", "unknown"), f"Missing or invalid event timestamp: {ref}")
            return None
        if time >= self.end:
            return None
        text = redact(text)
        clipped = role in {"tool", "action"} and len(text) > TOOL_LIMIT
        return {
            "timestamp": time.isoformat(), "scope": "today" if time >= self.start else "prior_context",
            "role": role, "text": text[:TOOL_LIMIT] if clipped else text,
            "truncated": clipped, "source_ref": ref, **extra,
        }

    def save_session(self, source, session_id, events, paths, **metadata):
        events = [e for e in events if e]
        # Deduplicate exact records while retaining raw source provenance.
        unique = {}
        for e in events:
            key = (e.get("event_id") or "", e["timestamp"], e["role"], e["text"])
            if key in unique:
                other = unique[key].setdefault("additional_refs", [])
                if e["source_ref"] != unique[key]["source_ref"]:
                    other.append(e["source_ref"])
            else:
                unique[key] = e
        events = sorted(unique.values(), key=lambda e: e["timestamp"])
        today = [e for e in events if e["scope"] == "today"]
        if not today:
            return
        key = source + ":" + str(session_id)
        excluded = str(session_id) in self.exclude
        digest = hashlib.sha256(key.encode()).hexdigest()[:20]
        target = self.output / "sessions" / f"{source}-{digest}.jsonl"
        if not excluded:
            with target.open("w", encoding="utf-8") as stream:
                for e in events:
                    stream.write(json.dumps(e, ensure_ascii=False) + "\n")
            os.chmod(target, 0o600)
        first = next((e for e in today if e["role"] == "user" and e.get("human_input") is not False), today[0])
        self.sessions.append({
            "key": key, "provider": source, "session_id": str(session_id),
            "raw_paths": [str(p) for p in paths], "evidence_path": None if excluded else str(target),
            "events_today": len(today), "prior_context_events": len(events) - len(today),
            "tool_excerpts_truncated": sum(e["truncated"] for e in events),
            "first_event_today": today[0]["timestamp"], "last_event_today": today[-1]["timestamp"],
            "prompt_preview": first["text"][:600],
            "review_status": "excluded" if excluded else "unread",
            "reason": "Explicit --exclude-session" if excluded else "Awaiting semantic review",
            **metadata,
        })

    def scan_jsonl(self, source, paths):
        grouped = collections.defaultdict(lambda: {"events": [], "paths": [], "metadata": {}})
        for path in paths:
            sid, metadata, events, fallback = path.stem, {}, [], []
            if source == "antigravity":
                sid = path.parents[2].name
            for line, row in self.rows(source, path):
                ref = {"path": str(path), "line": line}
                when = row.get("timestamp", row.get("created_at"))
                if source == "codex":
                    p = row.get("payload") or {}
                    if not isinstance(p, dict):
                        continue
                    if row.get("type") == "session_meta":
                        sid = p.get("id", p.get("session_id", sid))
                        metadata.update(cwd=p.get("cwd"), origin=p.get("source"))
                    elif row.get("type") == "response_item":
                        kind, role = p.get("type"), p.get("role")
                        if kind == "message" and role in {"user", "assistant"} and p.get("channel") != "analysis":
                            body = visible_text(p.get("content"))
                            synthetic = role == "user" and (body.lstrip().startswith(("<heartbeat>", "# AGENTS.md instructions", "<environment_context>")))
                            events.append(self.event(when, role, body, ref, human_input=False if synthetic else role == "user", event_id=p.get("id")))
                        elif kind in {"function_call", "custom_tool_call"}:
                            events.append(self.event(when, "action", p.get("name", "") + " " + compact(p.get("arguments", p.get("input", ""))), ref, call_id=p.get("call_id")))
                        elif kind in {"function_call_output", "custom_tool_call_output"}:
                            events.append(self.event(when, "tool", visible_text(p.get("output")), ref, call_id=p.get("call_id")))
                    elif row.get("type") == "event_msg" and p.get("type") in {"user_message", "agent_message"}:
                        role = "user" if p["type"] == "user_message" else "assistant"
                        fallback.append(self.event(when, role, visible_text(p.get("message")), ref, human_input=role == "user"))
                elif source == "claude":
                    # Subagents may share a parent sessionId; preserve each separate stream.
                    parent_sid = row.get("sessionId", sid)
                    sid = f"{parent_sid}/{path.stem}" if "subagents" in path.parts else parent_sid
                    if row.get("cwd"):
                        metadata["cwd"] = row["cwd"]
                    if row.get("type") in {"custom-title", "ai-title"}:
                        metadata["title"] = row.get("customTitle", row.get("aiTitle"))
                    msg = row.get("message") or {}
                    role = msg.get("role") if isinstance(msg, dict) else None
                    if role not in {"user", "assistant"}:
                        continue
                    extra = {"event_id": row.get("uuid"), "parent_id": row.get("parentUuid"), "sidechain": row.get("isSidechain", False)}
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        events.append(self.event(when, role, content, ref, human_input=role == "user" and not row.get("isMeta", False), **extra))
                    elif isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            kind = block.get("type")
                            if kind == "text":
                                events.append(self.event(when, role, block.get("text", ""), ref, human_input=role == "user" and not row.get("isMeta", False), **extra))
                            elif kind == "tool_use":
                                events.append(self.event(when, "action", block.get("name", "") + " " + compact(block.get("input", {})), ref, call_id=block.get("id"), **extra))
                            elif kind == "tool_result":
                                events.append(self.event(when, "tool", visible_text(block.get("content")), ref, call_id=block.get("tool_use_id"), **extra))
                else:
                    kind = row.get("type")
                    roles = {"USER_INPUT": "user", "PLANNER_RESPONSE": "assistant", "GENERIC": "action", "ERROR_MESSAGE": "tool"}
                    if kind in roles:
                        body = visible_text(row.get("content")) or compact(row.get("error", ""))
                        if kind == "USER_INPUT":
                            match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", body, re.S)
                            if match:
                                body = match.group(1)
                        events.append(self.event(when, roles[kind], body, ref, event_id=str(row.get("step_index")), human_input=kind == "USER_INPUT" and row.get("source") == "USER_EXPLICIT", status=row.get("status")))
                    elif kind != "SYSTEM_MESSAGE":
                        self.error(source, f"{path}:{line}", f"Unsupported transcript event type: {kind}")
            if source == "codex":
                for role in ("user", "assistant"):
                    if not any(e and e["role"] == role for e in events):
                        events.extend(e for e in fallback if e and e["role"] == role)
            item = grouped[str(sid)]
            item["events"].extend(events)
            item["paths"].append(path)
            item["metadata"].update(metadata)
        for sid, item in grouped.items():
            self.save_session(source, sid, item["events"], item["paths"], **item["metadata"])

    def scan_devin(self, path):
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            sessions = conn.execute("SELECT id, title, working_directory, main_chain_id FROM sessions").fetchall()
            for session in sessions:
                sid = session["id"]
                rows = conn.execute("SELECT row_id,node_id,parent_node_id,created_at,chat_message FROM message_nodes WHERE session_id=? ORDER BY row_id", (sid,)).fetchall()
                parents = {r["node_id"]: r["parent_node_id"] for r in rows}
                main, node = set(), session["main_chain_id"]
                while node is not None and node not in main:
                    main.add(node)
                    node = parents.get(node)
                events = []
                for row in rows:
                    ref = {"path": str(path), "table": "message_nodes", "row_id": row["row_id"], "session_id": sid}
                    try:
                        msg = json.loads(row["chat_message"])
                        meta = msg.get("metadata") or {}
                        when = meta.get("created_at") or row["created_at"]
                        role = msg.get("role")
                        if role not in {"user", "assistant", "tool"}:
                            continue
                        telemetry = meta.get("telemetry") or {}
                        source = telemetry.get("source")
                        synthetic = source in {"cache_keepalive", "system", "tool_result"}
                        content = msg.get("content", "")
                        extra = {"event_id": msg.get("message_id"), "node_id": row["node_id"], "parent_node_id": row["parent_node_id"], "branch": "main" if row["node_id"] in main else "alternate_or_subagent", "human_input": role == "user" and not synthetic, "input_origin": source, "timestamp_basis": "message_metadata" if meta.get("created_at") else "row_created_at"}
                        events.append(self.event(when, role, visible_text(content), ref, **extra))
                        for call in msg.get("tool_calls") or []:
                            if isinstance(call, dict):
                                events.append(self.event(when, "action", call.get("name", "") + " " + compact(call.get("arguments", {})), ref, call_id=call.get("id"), **extra))
                        # Some versions store visible tool calls as content blocks.
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") in {"tool_use", "tool_call"}:
                                    events.append(self.event(when, "action", compact({k: block[k] for k in ("name", "input", "arguments") if k in block}), ref, **extra))
                    except (ValueError, TypeError, AttributeError) as exc:
                        self.error("devin", f"{path}:row={row['row_id']}", exc)
                self.save_session("devin", sid, events, [path], title=session["title"], cwd=session["working_directory"])
            self.coverage["devin"]["sessions_in_database"] = len(sessions)

    def scan_shadow(self):
        root = self.shadow / "Meetings"
        folders = sorted({p.parent for p in root.rglob("*.md") if p.parent.name[:4].isdigit()})
        for folder in folders:
            files = sorted(folder.glob("*.md"))
            metadata = {}
            meta_path = None
            try:
                for path in files:
                    text = path.read_text(encoding="utf-8")
                    if text.startswith("---"):
                        match = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
                        if match:
                            values = dict(re.findall(r"^(\w+):\s*(.*?)\s*$", match.group(1), re.M))
                            if values.get("type", "").strip('"\'') == "meeting":
                                metadata, meta_path = values, path
                                break
                start, end = timestamp(metadata.get("startedAt")), timestamp(metadata.get("endedAt"))
                date = metadata.get("date", folder.name[:10]).strip('"\'')
                if start:
                    included = start < self.end and (end > self.start if end and end > start else start >= self.start)
                    basis = "startedAt/endedAt" if end else "startedAt"
                else:
                    try:
                        dt.date.fromisoformat(date)
                    except ValueError:
                        self.error("shadow", folder, "No valid meeting date")
                        continue
                    included = date == self.day
                    basis = "frontmatter_date" if "date" in metadata else "folder_date"
                if included:
                    self.meetings.append({
                        "key": str(folder), "title": metadata.get("title", folder.name[11:]).strip('"\''),
                        "date_basis": basis, "declared_date": date,
                        "started_at": start.isoformat() if start else None,
                        "ended_at": end.isoformat() if end else None,
                        "metadata_path": str(meta_path) if meta_path else None,
                        "text_paths": [str(f) for f in files if f.name != "Screenshots.md"],
                        "review_status": "unread", "speaker_attribution": "requires_review",
                    })
            except (OSError, UnicodeError) as exc:
                self.error("shadow", folder, exc)
        self.coverage["shadow"]["meeting_folders_scanned"] = len(folders)

    def run(self):
        roots = {
            "codex": [self.home / ".codex/sessions", self.home / ".codex/archived_sessions"],
            "claude": [self.home / ".claude/projects"],
            "antigravity": [self.home / ".gemini/antigravity-cli/brain"],
            "devin": [self.home / ".local/share/devin/cli/sessions.db"],
            "shadow": [self.shadow / "Meetings"],
        }
        for source, paths in roots.items():
            present = [p for p in paths if p.exists()]
            self.coverage[source] = {"status": "available" if present else "unavailable", "roots": [str(p) for p in paths], "missing_roots": [str(p) for p in paths if not p.exists()], "review_status": "not_started"}
            if not present:
                continue
            try:
                if source == "devin":
                    self.scan_devin(present[0])
                elif source == "shadow":
                    self.scan_shadow()
                else:
                    pattern = "*/.system_generated/logs/transcript_full.jsonl" if source == "antigravity" else "**/*.jsonl"
                    files = sorted({f for root in present for f in root.glob(pattern)})
                    self.coverage[source]["files_scanned"] = len(files)
                    self.scan_jsonl(source, files)
                    if source == "antigravity":
                        conv = self.home / ".gemini/antigravity-cli/conversations"
                        expected = {p.stem for p in conv.glob("*.db")}
                        actual = {p.parents[2].name for p in files}
                        missing = sorted(expected - actual)
                        self.coverage[source]["missing_transcript_ids"] = missing
                        if missing:
                            self.error(source, conv, f"Missing full text exports: {missing}")
            except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
                self.error(source, str(paths), exc)
            self.coverage[source]["active_items"] = len(self.meetings) if source == "shadow" else sum(s["provider"] == source for s in self.sessions)
            source_errors = any(e["source"] == source or (e["source"] == "unplaced_timestamp" and any(e["path"].startswith(str(p)) for p in paths)) for e in self.errors)
            self.coverage[source]["status"] = "partial" if source_errors else "local_inventory_scanned"
        atomic_json(self.output / "session-index.json", self.sessions)
        atomic_json(self.output / "meeting-index.json", self.meetings)
        atomic_json(self.output / "manifest.json", self.manifest)
        return self.manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Local YYYY-MM-DD; defaults to today")
    parser.add_argument("--timezone", default="America/Los_Angeles")
    parser.add_argument("--as-of", help="Frozen ISO cutoff with timezone")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--shadow-root", type=Path)
    parser.add_argument("--output", type=Path, help="New directory; existing directories are never overwritten")
    parser.add_argument("--exclude-session", action="append", default=[])
    args = parser.parse_args()
    try:
        frozen = args.as_of or dt.datetime.now(UTC).isoformat()
        day, _, _ = window(args.date, args.timezone, frozen)
        output = args.output or args.home / ".codex/daily-recap/runs" / day / dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        collector = Collector(args.home.expanduser().resolve(), (args.shadow_root or args.home / "Documents/Shadow").expanduser().resolve(), output.expanduser().resolve(), day, args.timezone, frozen, args.exclude_session)
        manifest = collector.run()
        print(json.dumps({"output": str(collector.output), "date": day, "start": manifest["start"], "end_exclusive": manifest["end_exclusive"], "sessions": len(collector.sessions), "meetings": len(collector.meetings), "coverage": {k: v["status"] for k, v in manifest["sources"].items()}, "errors": len(collector.errors)}, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
