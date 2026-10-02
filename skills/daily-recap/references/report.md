# Report and evidence contract

Use Chinese by default and put evidence links beside material claims. Scale detail
to the day, with a concise front page and complete coverage ledger; empty sections
need no generic advice.

Suggested order:

1. **Date/coverage:** date, timezone, exact cutoff, source coverage/counts for all
   four agents, Slack Digest/original threads, and Shadow. Separate inventory,
   semantic review, and cloud completeness; expose unread/failed/truncated sources.
2. **What mattered:** consequential outcomes, decisions, and open loops with
   accurate attribution of human and agent contributions.
3. **Coding work:** problem, method, key decision/why, known alternatives, result/
   validation, human guidance and changed approach. Group linked work but account
   for every session in an appendix. Label noncoding or excluded sessions.
4. **Slack:** thread, latest ask, my reply, status, next action, and source. Add
   grounded communication coaching and improved reply drafts for useful examples.
5. **Meetings:** decisions/commitments by meeting. For the manager separate explicit ask,
   interpretation, follow-through, next action, and attribution confidence.
6. **Reflection:** what worked, what to improve, what the agent learned from human
   correction, one behavior to try. Connect technical decisions to expectations
   and communication. Output volume is not a measure of impact or seniority.
7. **Workflows:** observed repetition → trigger/inputs → steps/human checkpoint →
   artifact → implementation shape → success metric. Label estimated savings and
   distinguish proposed, available, and tested workflows.
8. **Next actions:** a few priorities with owner, dependency, evidence, explicit
   due date if known or clearly labeled suggested timing. Date older commitments.

Evidence labels: observed, reported_by_agent, attributed_in_meeting_notes,
inferred, proposed, unknown. Use natural Chinese equivalents in prose.

`evidence-ledger.json` is a compact source index, not duplicated transcripts or a
memory update. Include date, timezone, start, end_exclusive, coverage, sessions,
meetings, slack_threads, decisions, human_interventions, manager_expectations,
workflow_candidates, and open_actions.

Each claim/action needs stable ID, date, label, references, owner when known, and
status. Interventions need before/correction/after references and whether benefit
was observed. Slack records need workspace/channel/root timestamp, latest ask/
answer times, status as of cutoff, pagination completion, and permalinks. Session
records need provider/session ID/topic/evidence read/classification. Meeting
records need date basis/files/speaker confidence/commitments.

Every discovered active session/meeting must be reviewed, excluded with reason,
or unread with reason. Never label a source fully reviewed with unread items or
truncated evidence. A partial recap is useful if its uncertainty is visible.

Prior ledgers can seed open threads/commitments; recheck original evidence. Retain
each run/cutoff. Do not update other work trackers or Codex memory without an ask.
