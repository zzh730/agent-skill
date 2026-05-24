---
name: migrate_to_codex
description: Migrate supported instruction files, skills, agents, and MCP config into Codex project and global files.
---

# Migrate To Codex

## Procedure

1. Read `references/differences.md` first. Use it as the checklist for non-1:1 mappings. If today is later than the `Docs last checked` date below, reopen the official Codex docs and the source docs map before editing migrated files.
2. Check the source before running experimental migrations. Only pass `--plugins` when `.claude-plugin/marketplace.json` exists. Only pass `--hooks` when `~/.claude/settings.json`, `.claude/settings.json`, or `.claude/settings.local.json` contains `hooks`.
3. Run a default dry-run for each scope. Default migration covers instruction files, skills, subagents, and MCP config:

```bash
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ~/.claude/ --target ~/.codex/ --dry-run
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ./.claude/ --target ./.codex/ --dry-run
```

4. Read the summary, the `Migration surfaces:` active/inactive checklist, stderr warnings, and the `Migration report:` punch list. On real runs, reopen `.codex/migrate-to-codex-report.txt` from the target root so the review checklist survives terminal scrollback. Treat every `manual_fix_required` and `skipped` row as review work. Choose `--merge` to keep orphaned generated skills/subagents or `--replace` to remove them.
5. Run the real default migration once per scope:

```bash
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ~/.claude/ --target ~/.codex/ --mcp --skills --subagents --merge
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ./.claude/ --target ./.codex/ --mcp --skills --subagents --merge
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ./.claude/ --target ./.codex/ --skills --replace
```

6. Run experimental migrations only when the source files exist:

```bash
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ./.claude/ --target ./.codex/ --plugins --merge
python3 .codex/skills/migrate-to-codex/scripts/migrate-to-codex.py --source ./.claude/ --target ./.codex/ --hooks --merge
```

7. Verify `AGENTS.md` first. Keep the symlink if the source instruction file is neutral. If `AGENTS.md` is a generated copy, remove source-specific hooks, slash commands, and delegation assumptions before relying on it.
8. Send verifier sub-agents over migrated artifacts in this order: `AGENTS.md`, skills, MCP config, subagents, plugins, hooks.
9. Manually fix every partial or unsupported mapping they flag, in that same order. Start with files containing `## MANUAL MIGRATION REQUIRED` blocks.
10. Re-run verifier sub-agents and a targeted `--dry-run`, then record any intentional unmapped behavior or product gaps.

## Script Behavior

- `--source`: Source scope root, or a glob containing `global/` and `project/` fixture directories.
- `--target`: Codex scope root to write into.
- `--mcp`: Convert settings and MCP config into `config.toml`.
- `--skills`: Convert skills into `.agents/skills`.
- `--subagents`: Convert subagents into `.codex/agents`.
- `--plugins`: Experimental. Import local plugin marketplace skills and agents from `.claude-plugin/marketplace.json`.
- `--hooks`: Experimental. Convert settings hooks into `.codex/hooks.json` and enable `[features].codex_hooks = true`.
- `--merge`: Keep orphaned generated skills and subagents in the target (default).
- `--replace`: Remove orphaned generated skills and subagents only for the selected surfaces.
- `--dry-run`: Stage conversion in a temporary directory and print a summary plus a per-file migration report without writing files.

The CLI prints `Migration surfaces:` before the per-file report so reviewers can see which surfaces were active, inactive because no source files were found, or inactive because flags skipped them. Plugins and hooks are always listed explicitly and remain inactive unless `--plugins` or `--hooks` is selected.

The CLI prints `Migration report:` in manual-repair priority order (`AGENTS.md`, skills, MCP, subagents, plugins, hooks) and writes the surfaces plus report to `.codex/migrate-to-codex-report.txt` on non-`--dry-run` runs:

- `symlinked`: Shared `AGENTS.md` points at the selected source instruction file.
- `rewritten`: Generated Codex file has no known manual caveat.
- `manual_fix_required`: Generated file needs a human rewrite or hardening pass; the report row names the source fields.
- `skipped`: Plugin source could not be imported safely.
- `overwritten`: Existing generated Codex artifact was replaced.
- `deleted` / `would_delete`: Orphaned generated artifact removed or scheduled for removal in `--dry-run`.

## Default Migration

- Instruction candidates are checked in this order: `.claude/CLAUDE.md`, `CLAUDE.md`, `claude.md`, `AGENTS.md`, `agents.md`, `AGENT.md`, `agent.md`, `.agents.md`, `.agents/AGENTS.md`, `.agents/agents.md`, `GEMINI.md`, `gemini.md`, `.config/opencode/AGENTS.md`, `.pi/agent/AGENTS.md`, `CURSOR.md`, `.cursorrules`, and `AIDER.md`.
- Root `AGENTS.md` is treated as already active and is not overwritten or symlinked to itself.
- Neutral instruction files become an `AGENTS.md` symlink. Files with source-specific semantics become a generated `AGENTS.md` copy with a manual-warning block.
- MCP config is read from `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, `.claude.json`, and `.mcp.json`, then written to `~/.codex/config.toml` or trusted-project `.codex/config.toml`.
- Skills are written to `.agents/skills/<name>/`.
- Subagents are written to `.codex/agents/<name>.toml`.
- OpenCode `AGENTS.md` / `CLAUDE.md` instructions are covered by the instruction pass. OpenCode `opencode.json` / `opencode.jsonc`, `~/.config/opencode/opencode.json`, `.opencode/agents`, `.opencode/commands`, `.opencode/plugins`, `.opencode/skills`, `.opencode/tools`, and matching global `~/.config/opencode/` resource dirs are reported as `manual_fix_required`; the tool does not translate OpenCode config, plugins, hooks, or custom tools.
- PI-CODE `AGENTS.md` / `CLAUDE.md` instructions are covered by the instruction pass. PI-CODE `.pi/settings.json`, `.pi/SYSTEM.md`, `.pi/APPEND_SYSTEM.md`, `.pi/extensions`, `.pi/skills`, `.pi/prompts`, `.pi/git`, `.pi/npm`, and matching global `~/.pi/agent/` files and resource dirs are reported as `manual_fix_required`; the tool does not translate PI-CODE settings, package installs, extensions, or hook-like behavior.

## Experimental Migration

- Plugins: local `.claude-plugin/marketplace.json` entries are imported only when `--plugins` is passed. Safe relative `source` paths are scanned for default `skills/` and `agents/` directories. External, absolute, parent-traversal, missing, custom path, and `metadata.pluginRoot`-dependent sources are skipped and reported.
- Hooks: settings `hooks` are converted only when `--hooks` is passed. The converter writes `.codex/hooks.json`, enables `[features].codex_hooks = true`, and marks the hook output `manual_fix_required`.
- Codex hooks are experimental. Recheck `~/.codex/hooks.json`, project `.codex/hooks.json`, and the active config layer before treating a hook migration as complete.

## Manual Repair Priorities

1. `AGENTS.md`
2. Skills
3. MCP config
4. Subagents
5. Plugins
6. Hooks

## Key Caveats

- Preserve skill `allowed-tools` and subagent `skills` / `tools` / `disallowedTools` as prompt guidance unless a stricter Codex config mapping is obvious.
- Generated files with lossy mappings include a `## MANUAL MIGRATION REQUIRED` block. Resolve those warnings before treating the migration as complete.
- Harden generated subagents with `sandbox_mode`, `[permissions]`, `[mcp_servers.<id>].enabled_tools`, `[mcp_servers.<id>].disabled_tools`, or `[apps.<id>.tools.<tool>]` when source intent is unambiguous.
- Map model families by prefix: `claude-opus*` -> `gpt-5.4`, `claude-sonnet*` -> `gpt-5.4-mini`, and `claude-haiku*` -> `gpt-5.4-mini`; `effort: max` maps to Codex `xhigh`.
- Rewrite hooks as Codex `notify` or `.codex/hooks.json` only when the lifecycle and enforcement behavior still match.
- Verify MCP auth, headers, transport, OAuth, and env handling against current Codex docs.
- Plugin agents should remain Codex subagents instead of being flattened into skills.
- The converter only supports simple YAML frontmatter with scalar values and top-level lists.

## Reference

Docs last checked: 2026-04-06

- `references/differences.md`
- `https://docs.claude.com/en/docs/claude-code/claude_code_docs_map`
- `https://developers.openai.com/codex/config-reference`
- `https://developers.openai.com/codex/mcp`
- `https://developers.openai.com/codex/skills`
- `https://developers.openai.com/codex/subagents`
- `https://developers.openai.com/codex/hooks`
- `https://code.claude.com/docs/en/skills`
- `https://code.claude.com/docs/en/sub-agents`
- `https://code.claude.com/docs/en/hooks`
- `https://code.claude.com/docs/en/hooks-guide`
- `https://code.claude.com/docs/en/mcp`
- `https://code.claude.com/docs/en/settings`
- `https://code.claude.com/docs/en/plugins`
- `https://code.claude.com/docs/en/plugin-marketplaces`
- `https://code.claude.com/docs/en/plugins-reference`
- `https://opencode.ai/docs/config/`
- `https://opencode.ai/docs/rules`
- `https://opencode.ai/docs/agents/`
- `https://opencode.ai/docs/commands/`
- `https://opencode.ai/docs/plugins/`
- `https://opencode.ai/docs/skills/`
- `https://opencode.ai/docs/custom-tools/`
- `https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/README.md`
- `https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/packages.md`
