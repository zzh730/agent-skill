---
name: council
description: Dispatch one question to a configurable panel of AI coding agents (default codex + grok + claude; also pi or any Herdr-supported kind, each with optional model and thinking-effort) in Herdr panes, collect their answers, and return a judged comparison — per-agent positions, a horizontal option table, and a verdict on which option to pick. Use when the user invokes /council, asks to "问一下/征集 Codex 和 Grok 的意见", wants the same question cross-checked by multiple models, or asks for an agent panel/council.
---

# Council

Orchestrate a cross-model answer comparison. The invoking Claude session is the **judge, not a contestant**: it dispatches the question, reads every panelist's answer, and delivers a verdict. It does not author its own answer first.

## Arguments

`/council [--agents <spec>,<spec>,...] [--context <file> ...] [--out <file>] <question>`

- Agent spec = `kind[:model[:effort]]`, e.g. `codex:gpt-5.6-sol:high,grok,claude:opus,pi:openai/gpt-4o`. Default: `codex,grok,claude` (each CLI's own default model/effort when unspecified).
- `--context`: files the panelists must read; pass them as absolute paths inside the prompt (agents read them themselves). Quote paths with spaces.
- `--out`: write the full report (including each agent's answer verbatim) to this file; the chat reply stays the judged summary. Without it, chat only.
- Model/effort/auto-approve map to native flags, appended after `--` in `herdr agent start`. Auto-approve is always on — panelists must never wait for a human to approve a dialog:

| kind | model flag | effort flag | auto-approve (always appended) |
|---|---|---|---|
| codex | `-m <model>` | `-c model_reasoning_effort=<effort>` | `--approve-for-me` |
| grok | `-m <model>` | `--effort <effort>` | `--always-approve` |
| claude | `--model <model>` | `--effort <effort>` | `--permission-mode acceptEdits --add-dir <scratchpad-dir>` (without `--add-dir`, creating the answer file outside cwd still prompts; `--dangerously-skip-permissions` only on explicit user request) |
| pi | `--model <model>` (supports `provider/id`) | `--thinking <level>` | n/a (no approval prompts) |

Unknown kinds: start bare. If the user asked for a model/effort on an unknown kind, check that CLI's `--help` first and skip the flag when unsupported — and say so in the report.

A `claude` panelist is a fresh Claude Code instance in its own pane. It competes; the invoking session stays judge.

## Process

1. Preflight: require `HERDR_ENV=1`; if unset, say this session is not inside Herdr and stop. Invoke the `herdr` skill for command discipline if not already loaded.
2. Reuse before create: `herdr agent list`. Reuse a live `council-<kind>` agent when the requested model/effort matches what it was started with — live agents retain conversation context, which is what makes follow-up questions work. A changed spec restarts that agent. Otherwise create:
   - `herdr pane layout` to pick the split direction (wide → right, tall → down).
   - `herdr pane split --current --direction <d> --cwd <dir> --no-focus` (cwd = directory of the context files, else $PWD); parse `pane_id` from the JSON.
   - `herdr agent start council-<kind> --kind <kind> --pane <pane_id> --timeout 60000 -- <native flags from the table>`.
3. Build each panelist's prompt from [PROMPT.md](PROMPT.md). Identical question and context for everyone; only the answer-file path differs. The file dump is requested up front for all panelists (this deliberately overrides the herdr skill's read-first-fallback-later rule — grok's TUI provably loses scrollback, and uniform files make collection reliable).
4. Prompt all panelists in parallel: `herdr agent prompt <name> "<text>" --wait --timeout 180000`, using background Bash for the slower agents. On timeout, extend once with `herdr agent wait <name> --timeout 120000` (5 min total). Still unsettled → report that agent as still working, check `herdr agent get`, and read its pane. A `--wait` timeout is NOT failure; never re-prompt on it.
5. Blocked handling: rare with auto-approve on (first-launch trust prompts are the main leftover). On `agent_status=blocked`: `herdr pane read <pane_id> --source visible`, approve routine dialogs via `herdr agent send-keys` (digit + Enter) without waiting for the user, and surface anything unusual.
6. Collect: read each panelist's answer file from the scratchpad. Fallback for agents that ignored the instruction: `herdr agent read <name> --source recent-unwrapped --lines 500`; if truncated by the alt screen, ask that agent to dump its answer to the file and read it.
7. Judge and report per [REPORT.md](REPORT.md). Leave panes open and name them in the reply so the user can inspect.
8. Follow-ups: later `/council` questions in the same session reuse the same agents and their accumulated context.

## Report

Follow [REPORT.md](REPORT.md) for the chat reply and the `--out` archive structure.

## Gotchas

- Codex TUI can crash on exit errors (e.g. "Failed to branch"); it prints `codex resume <session-id>` on the way out. Restart with `herdr agent start council-codex --kind codex --pane <id> -- resume <session-id>` to keep its context.
- If a requested kind fails to start (not installed), report it and continue with the remaining panelists.
- Agent names must match `[a-z][a-z0-9_-]{0,31}`; `council-<kind>` complies.
- Codex typically needs 4–6 minutes on a substantial question; that is what the extend-once wait policy is for.
- The harness permission classifier may deny starting codex with `--approve-for-me`. Fall back to a bare `codex` start — its default sandbox rarely prompts, and step 5 handles any blocked dialog.
- A freshly started agent TUI can swallow the first prompt while it initializes: the call may return `agent_prompt_stalled`, or worse, return success while the transcript shows no submitted question. After the first prompt to a new agent, verify the question appears in the pane (`herdr agent read`); re-prompt if absent.
