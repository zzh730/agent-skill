# Source adapters and coverage

These paths and formats were inspected on 2026-09-20. Recheck after schema changes.
The collector requires Python 3.9+ and the standard library. Outputs default to
`~/.codex/daily-recap/runs/<local-date>/<UTC-run-time>/`, with private permissions.

## Local histories

| Source | Verified path | Reading rules |
| --- | --- | --- |
| Codex | `~/.codex/sessions/**/*.jsonl`, `~/.codex/archived_sessions/**/*.jsonl` | `session_meta` identifies session/cwd; `response_item` carries messages/calls/results; `event_msg` can carry user/assistant messages. Filter event timestamps, not folder date or mtime. |
| Claude Code | `~/.claude/projects/**/*.jsonl` | Include `subagents/`. Preserve session ID, UUID, parent UUID, sidechain status. User-role tool results are tools. Titles/compaction context do not prove new work. |
| Devin local CLI/Desktop | `~/.local/share/devin/cli/sessions.db` | SQLite `mode=ro`; tables `sessions`, `message_nodes`, `prompt_history`, `subagent_heads`. Prefer message `metadata.created_at`: old nodes may be reinserted with today's row time. Deduplicate message IDs, preserve branch provenance. `cache_keepalive` is synthetic. |
| Antigravity CLI | `~/.gemini/antigravity-cli/brain/<id>/.system_generated/logs/transcript_full.jsonl` | Use `created_at`, `step_index`, `type`, `source`, `content`. Do not count transcript/chunk copies again. Exclude `thinking`. Compare IDs with `conversations/*.db` for missing exports. |

Clipped tool evidence retains a raw line/row locator; read it when validation or a
key decision depends on the result. The collector excludes private model reasoning.
Prior dialogue for active sessions is tagged `prior_context`, not today's work.

Antigravity SQLite could not be opened read-only during setup; all nine discovered
conversation IDs had full text exports, which are the verified adapter. An IDE
cache or summary DB alone is not a full transcript.

Cloud-only Devin, remote Codex hosts, Claude web, and other Antigravity profiles
need authenticated read tools or exports. Discover applicable access. Codex
`list_threads` reports unavailable hosts/sources; inspect remote and archived tasks
as needed and paginate. A top-50 task list alone is not complete. Do not launch or
resume agents to export history. No extra cloud connector was available during
setup; keep that limitation visible until verified.

To inspect a raw Devin locator, open SQLite read-only and select the referenced
`message_nodes.row_id`/`session_id`. Do not dump credentials/unrelated tables. A
failed read is unavailable/partial, not empty. Never use immutable reads against a
live WAL DB to bypass locking: recent messages may be silently omitted.

## Slack Digest and original threads

Use `~/.config/daily-recap/context.md` for local identity, workspace, digest
configuration, and task-ID seeds. If absent, discover the user's Slack identity
and existing digest from available tools. Keep account IDs, internal channels,
and private task links in local context rather than this shared skill.

Read the digest through available task-history tools such as Codex
`list_threads`/`read_thread`, paging through turns covering the requested window.
When those tools are unavailable, use the collector's local Codex evidence and
raw references for the configured digest session. Preserve the source title.
Refresh seeds if moved. Its coverage dates, not last-updated time, determine
relevance. An older digest is a link index/context, never today's evidence.

Verify identity if ambiguous using `slack_read_user_profile`/`slack_search_users`.
Search originals through available Slack tools:

1. Messages **from** the user during the precise window.
2. Messages **mentioning** `<@USER_ID>` in the window, including replies inside old
   threads. Use literal mention query/keywords and verify mention tokens; `with:`
   alone is not proof of a direct tag.
3. Full threads discovered by these searches or digest links; also participated/
   open threads with new replies today. Use the previous recap's open-thread
   ledger and, initially, a bounded lookback such as seven days of the user's posts.
   Fetch those threads for today's replies. Disclose any older-participation gap.

Run author and mention searches separately; exhaust every `next_cursor`/`has_more`.
Date modifiers select candidates; use epoch bounds when supported and enforce
exact `[start, end)` timestamps locally. Slack upper bounds may be inclusive.
Keep the original cutoff even when collection takes several minutes.

Read parent context and paginate replies; do not fetch only post-midnight replies.
Canonical key: `(workspace, channel_id, root_thread_ts)`. Link actual asks/answers
as well as parents. Assess latest actionable ask, completeness of response, owner
changes, and explicit deadlines. FYI mentions are not missed replies.

Use public-channel search with current access. Private/DM search requires the
active tool's authorization and the existing user request/session; do not repeat
permission already given. Skill creation alone does not authorize unrelated
private-channel exploration. If unavailable, disclose the gap and complete public
coverage. Never send messages or mutate Slack for this recap.

## Shadow meetings

Root: `~/Documents/Shadow`; override with `--shadow-root`. Layout:
`Meetings/YYYY/MM/YYYY-MM-DD <title>/` containing:

- `<title>.md`: frontmatter date/startedAt/endedAt, attendees, speaker assignments.
- `Meeting Notes.md`, `Meeting Outline.md`: summaries/decisions.
- `Transcript.md`: timed speaker turns, often generic speaker labels.
- `Screenshots.md`, `Screenshots/`: optional visual evidence.

Prefer startedAt/endedAt for timezone conversion and cross-midnight meetings.
Otherwise use frontmatter date or dated folder, recording the fallback. Inspect
conflicts/unknown times. Mtime is never the meeting date. Open screenshots only
when needed; never edit Shadow-managed files.

Attribute the manager via explicit assignments, named notes, or an unambiguous introduction.
An attendee list, title, or `Speaker 2` alone is insufficient. If notes name the manager
but the transcript cannot confirm it, label it as attribution in meeting notes.
