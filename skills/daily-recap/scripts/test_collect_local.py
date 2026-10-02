"""Behavior checks for date boundaries, copied history, provenance, and gaps."""
import datetime as dt
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from collect_local import Collector, timestamp, visible_text, window


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.shadow = self.home / "Documents/Shadow"

    def write_jsonl(self, relative, rows):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return path

    def collect(self, **kwargs):
        collector = Collector(self.home, self.shadow, self.home / "run", "2026-09-18", "America/Los_Angeles", "2026-09-19T08:00:00Z", **kwargs)
        collector.run()
        return collector

    def evidence(self, collector):
        return [json.loads(line) for session in collector.sessions if session["evidence_path"] for line in Path(session["evidence_path"]).read_text().splitlines()]

    def test_dst_and_cutoff(self):
        _, start, end = window("2026-03-08", "America/Los_Angeles", "2026-03-10T00:00:00Z")
        self.assertEqual(end - start, dt.timedelta(hours=23))
        _, start, end = window("2026-11-01", "America/Los_Angeles", "2026-11-03T00:00:00Z")
        self.assertEqual(end - start, dt.timedelta(hours=25))
        _, _, end = window("2026-09-18", "America/Los_Angeles", "2026-09-18T18:12:00Z")
        self.assertEqual(end, timestamp("2026-09-18T18:12:00Z"))

    def test_old_directory_resumed_and_mirrored_codex(self):
        rows = [
            {"timestamp": "2026-09-01T09:00:00Z", "type": "session_meta", "payload": {"id": "resumed", "cwd": "/project"}},
            {"timestamp": "2026-09-01T09:01:00Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Original problem"}]}},
            {"timestamp": "2026-09-18T07:00:00Z", "type": "event_msg", "payload": {"type": "user_message", "message": "Check actual auth"}},
            {"timestamp": "2026-09-18T07:00:00Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Check actual auth"}]}},
            {"timestamp": "2026-09-18T07:01:00Z", "type": "response_item", "payload": {"type": "message", "role": "assistant", "channel": "analysis", "content": [{"type": "text", "text": "PRIVATE_THOUGHT"}]}},
            {"timestamp": "2026-09-19T07:00:00Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Tomorrow"}]}},
        ]
        self.write_jsonl(".codex/sessions/2026/09/01/old.jsonl", rows)
        self.write_jsonl(".codex/archived_sessions/copy.jsonl", rows)
        c = self.collect()
        self.assertEqual(len(c.sessions), 1)
        self.assertEqual(c.sessions[0]["events_today"], 1)
        self.assertEqual(c.sessions[0]["prior_context_events"], 1)
        self.assertNotIn("PRIVATE_THOUGHT", str(self.evidence(c)))
        self.assertNotIn("Tomorrow", str(self.evidence(c)))
        self.assertEqual(len(c.sessions[0]["raw_paths"]), 2)

    def test_claude_tool_result_is_not_human_feedback(self):
        self.write_jsonl(".claude/projects/project/session.jsonl", [
            {"timestamp": "2026-09-18T10:00:00Z", "sessionId": "claude-session", "uuid": "result", "type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call", "content": "Tests failed"}]}},
            {"timestamp": "2026-09-18T10:01:00Z", "sessionId": "claude-session", "uuid": "reply", "type": "assistant", "message": {"role": "assistant", "content": [{"type": "thinking", "thinking": "PRIVATE"}, {"type": "text", "text": "I will fix the failure"}]}},
        ])
        e = self.evidence(self.collect())
        self.assertEqual([x["role"] for x in e], ["tool", "assistant"])
        self.assertNotIn("PRIVATE", str(e))

    def test_devin_native_time_tools_and_synthetic_input(self):
        path = self.home / ".local/share/devin/cli/sessions.db"
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE sessions(id TEXT, title TEXT, working_directory TEXT, main_chain_id INTEGER)")
            db.execute("CREATE TABLE message_nodes(row_id INTEGER,session_id TEXT,node_id INTEGER,parent_node_id INTEGER,created_at INTEGER,chat_message TEXT)")
            db.execute("INSERT INTO sessions VALUES ('local-session','Problem','/project',3)")
            messages = [
                {"message_id": "old", "role": "user", "content": "Old requirement", "metadata": {"created_at": "2026-09-17T10:00:00Z"}},
                {"message_id": "synthetic", "role": "user", "content": "continue", "metadata": {"created_at": "2026-09-18T10:00:00Z", "telemetry": {"source": "cache_keepalive"}}},
                {"message_id": "action", "role": "assistant", "content": "Testing", "thinking": "PRIVATE", "tool_calls": [{"id": "check", "name": "exec", "arguments": {"cmd": "pytest"}}], "metadata": {"created_at": "2026-09-18T10:01:00Z"}},
            ]
            for n, msg in enumerate(messages, 1):
                db.execute("INSERT INTO message_nodes VALUES (?,?,?,?,?,?)", (n, "local-session", n, n-1 if n>1 else None, 1789761600, json.dumps(msg)))
        c = self.collect()
        e = self.evidence(c)
        self.assertEqual(c.sessions[0]["prior_context_events"], 1)
        self.assertFalse(next(x for x in e if x["text"] == "continue")["human_input"])
        self.assertTrue(any(x["role"] == "action" and "pytest" in x["text"] for x in e))
        self.assertNotIn("PRIVATE", str(e))

    def test_antigravity_missing_export_and_thought_omission(self):
        self.write_jsonl(".gemini/antigravity-cli/brain/visible/.system_generated/logs/transcript_full.jsonl", [
            {"created_at": "2026-09-18T10:00:00Z", "step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "<USER_REQUEST>Fix bug</USER_REQUEST><ADDITIONAL_METADATA>Injected instructions</ADDITIONAL_METADATA>"},
            {"created_at": "2026-09-18T10:01:00Z", "step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "Fixed", "thinking": "PRIVATE"},
        ])
        missing = self.home / ".gemini/antigravity-cli/conversations/missing.db"
        missing.parent.mkdir(parents=True)
        missing.touch()
        c = self.collect()
        self.assertEqual(c.coverage["antigravity"]["status"], "partial")
        self.assertEqual(c.sessions[0]["session_id"], "visible")
        self.assertNotIn("PRIVATE", str(self.evidence(c)))
        self.assertNotIn("Injected instructions", str(self.evidence(c)))

    def test_shadow_utc_date_and_cross_midnight(self):
        folder = self.shadow / "Meetings/2026/09/2026-09-19 Evening Sync"
        folder.mkdir(parents=True)
        (folder / "Evening Sync.md").write_text('---\ntype: meeting\ntitle: "Evening Sync"\ndate: 2026-09-19\nstartedAt: "2026-09-19 01:00:00 UTC"\nendedAt: "2026-09-19 02:00:00 UTC"\n---\n')
        (folder / "Transcript.md").write_text("[00:01] Speaker 2: Check it.")
        c = self.collect()
        self.assertEqual(len(c.meetings), 1)
        self.assertEqual(c.meetings[0]["date_basis"], "startedAt/endedAt")
        self.assertEqual(c.meetings[0]["speaker_attribution"], "requires_review")

    def test_unavailable_malformed_and_private_output(self):
        p = self.write_jsonl(".codex/sessions/broken.jsonl", [])
        p.write_text("{broken\n")
        c = self.collect()
        self.assertEqual(c.coverage["codex"]["status"], "partial")
        self.assertEqual(c.coverage["devin"]["status"], "unavailable")
        self.assertEqual((c.output.stat().st_mode & 0o777), 0o700)
        self.assertEqual(((c.output / "manifest.json").stat().st_mode & 0o777), 0o600)
        self.assertEqual(c.manifest["semantic_review"], "not_started")

    def test_visible_text_never_includes_reasoning(self):
        self.assertEqual(visible_text([{"type": "reasoning", "text": "secret"}, {"type": "text", "text": "Visible"}]).strip(), "Visible")


if __name__ == "__main__":
    unittest.main()
