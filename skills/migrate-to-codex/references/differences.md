# Migration Differences

## Summary

This reference only lists migration differences, partial mappings, and unsupported behavior. Direct 1:1 mappings are intentionally omitted. When the converter preserves source-only semantics as prompt guidance, it also emits a `manual_fix_required` report row and writes a `## MANUAL MIGRATION REQUIRED` block into the generated file.

Docs last checked: 2026-04-06. If today's date is later, re-open the official Codex docs below and the source docs map before trusting these mappings.

## Instructions

| Claude | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| Neutral instruction files: `.claude/CLAUDE.md`, `CLAUDE.md`, `claude.md`, `agents.md`, `AGENT.md`, `.agents/AGENTS.md`, `GEMINI.md`, `.config/opencode/AGENTS.md`, `.pi/agent/AGENTS.md`, `CURSOR.md`, `.cursorrules`, `AIDER.md` | `AGENTS.md` symlink | Linked automatically | This keeps one shared instruction body instead of duplicating docs. OpenCode and PI-CODE instructions are already covered through `AGENTS.md` / `CLAUDE.md`. |
| Root `AGENTS.md` | Root `AGENTS.md` | Reported as active | The converter does not overwrite or symlink the target file to itself. |
| Instruction content with `/hooks`, Claude subagent routing, or permission-mode assumptions | Generated `AGENTS.md` copy | Manual rewrite pass | The converter intentionally breaks the symlink when obvious source-only semantics need a Codex-specific edit. |

## OpenCode and PI-CODE source checks

| Source | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| OpenCode `AGENTS.md` / `CLAUDE.md` | `AGENTS.md` | Handled by the instruction pass | OpenCode docs use root `AGENTS.md` first and `CLAUDE.md` as a compatibility fallback. |
| OpenCode `opencode.json` / `opencode.jsonc` / `~/.config/opencode/opencode.json` fields such as `instructions`, `mcp`, `agent`, `command`, `plugin`, and `permission` | Mixed Codex config files | Reported as `manual_fix_required` | The schemas are not equivalent; translate instructions, MCP, agents, plugins, commands, and permissions manually. |
| OpenCode `.opencode/agents` / `~/.config/opencode/agents` | `.codex/agents/*.toml` | Reported as `manual_fix_required` | OpenCode markdown agents have different frontmatter and permission semantics. |
| OpenCode `.opencode/commands` / `~/.config/opencode/commands` | Prompt guidance or custom workflow | Reported as `manual_fix_required` | Codex does not have a direct slash-command directory migration in this tool. |
| OpenCode `.opencode/plugins` / `.opencode/tools` / matching global resource dirs | Codex plugin, MCP, hook, or prompt guidance | Reported as `manual_fix_required` | OpenCode plugins can contain event hooks and custom tools; do not import them as Claude plugin marketplaces. |
| OpenCode `.opencode/skills` / `~/.config/opencode/skills` | `.agents/skills` | Reported as `manual_fix_required` | Verify skill structure before copying; OpenCode also supports Claude skills separately through compatibility. |
| PI-CODE `AGENTS.md` / `CLAUDE.md` | `AGENTS.md` | Handled by the instruction pass | PI-CODE concatenates context files from global and project locations, so check whether multiple files need to be merged. |
| PI-CODE `.pi/settings.json` / `~/.pi/agent/settings.json` | Codex config files | Reported as `manual_fix_required` | PI-CODE settings can include packages and runtime preferences that are not Codex TOML. |
| PI-CODE `.pi/SYSTEM.md` / `.pi/APPEND_SYSTEM.md` / matching global files | `AGENTS.md` or subagent instructions | Reported as `manual_fix_required` | These replace or append to PI-CODE's system prompt and need a manual rewrite. |
| PI-CODE `.pi/extensions` / `~/.pi/agent/extensions` | Codex plugin, MCP, hook, or manual workflow | Reported as `manual_fix_required` | PI-CODE extensions can add tools, commands, UI, hooks, MCP-like behavior, and subagent-like behavior. |
| PI-CODE `.pi/skills` / `~/.pi/agent/skills` | `.agents/skills` | Reported as `manual_fix_required` | PI-CODE follows the Agent Skills standard but can also load package-filtered skills; verify structure before copying. |
| PI-CODE `.pi/prompts` / `~/.pi/agent/prompts` | Prompt library or manual docs | Reported as `manual_fix_required` | Codex does not currently have a direct prompt-template directory migration in this tool. |
| PI-CODE `.pi/git` / `.pi/npm` / matching global package installs | Codex plugins or manual install steps | Reported as `manual_fix_required` | Installed packages can contain extensions, skills, prompts, and themes. Review source before migration. |

## Skills

| Claude | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| `allowed-tools` | No strict skill allowlist | Preserved as prompt guidance in `SKILL.md` | `agents/openai.yaml` can declare tool dependencies, but that is not a permission boundary. |
| `user-invocable` | `policy.allow_implicit_invocation` | Manual review only | Similar intent, not equivalent semantics. |
| `model` / `effort` | No skill-level model pin | Unsupported | Codex model selection is session/agent scoped in this converter. |
| `disable-model-invocation` | No direct equivalent | Unsupported | Requires a manual rewrite if the Claude skill depends on this behavior. |
| `argument-hint` / `context` / `agent` / `hooks` / `paths` / `shell` | No direct equivalent | Unsupported | Keep only if the behavior can be rewritten into prompt guidance or config. |

## MCP and config

| Claude | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| `type: sse` | No SSE support | Unsupported | Codex supports stdio and streamable HTTP in current docs. |
| `headers.Authorization: Bearer ${VAR}` | `bearer_token_env_var` | Direct auth rewrite | Only the bearer-token shape is rewritten this way; `${VAR:-default}` fallbacks are not preserved. |
| `headers` with `${VAR}` | `env_http_headers` | Partial mapping | Static headers map to `http_headers`; `${VAR:-default}` fallbacks are not preserved. |
| `env` with `${VAR}` | `env_vars` | Partial mapping | Literal values stay in `env`; self-references become `env_vars`, and `${VAR:-default}` fallbacks are not preserved. |
| `oauth.callbackPort` | `mcp_oauth_callback_port` | Partial mapping | `oauth.clientId`, `oauth.authServerMetadataUrl`, and `headersHelper` are unsupported. |
| `enabledMcpjsonServers` / `disabledMcpjsonServers` | Per-server `enabled` | Partial mapping | `enableAllProjectMcpServers` has no direct equivalent in this converter. |
| `allowedMcpServers` / `deniedMcpServers` | `requirements.toml` | Manual policy mapping | Not written by this converter. |
| `.claude/settings.local.json` | No local-only Codex equivalent | Unsupported | Codex project config is tied to trusted project behavior. |

## Subagents

| Claude | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| `tools` / `disallowedTools` | No Claude-style fine-grained agent permissions | Preserved as prompt guidance in `developer_instructions` | Use `sandbox_mode`, `[permissions]`, MCP tool filters, or app tool filters manually when intent is clear. |
| `skills` | No spawn-time preload equivalent | Preserved as prompt guidance in `developer_instructions` | `skills.config` is enable/disable config, not preload behavior. |
| `mcpServers` | No inline subagent MCP config | Unsupported | Use shared Codex MCP config plus manual agent hardening instead. |
| `permissionMode` | `sandbox_mode` | Partial mapping | Only `acceptEdits` and `readOnly` are mapped; `default`, `dontAsk`, `bypassPermissions`, and `plan` are preserved as manual-review prompt guidance. |
| `model` + `effort` | `model` + `model_reasoning_effort` | Partial mapping by model family | Sonnet effort is biased one tier higher for coding-agent behavior; Claude `max` maps to Codex `xhigh`. |
| `hooks` / `memory` / `background` / `isolation` / `maxTurns` | No direct equivalent | Unsupported | Foreground/background and resume behavior do not map cleanly to Codex custom-agent files. |
| `initialPrompt` | No direct equivalent | Unsupported | Only applies when the agent runs as the main Claude session agent. |
| Auto-delegation by `description` | Automatic or explicit Codex sub-agent spawning | Behavior change | Not a 1:1 match; verify generated agent descriptions manually. |
| Independent agent permissions | Parent sandbox inheritance + runtime overrides | Behavior change | Codex custom-agent files set defaults, not hard isolation from the parent turn. |
| Plugin `agents/` | `.codex/agents/*.toml` | Imported as Codex subagents | Keep plugin agents as agents instead of flattening them into skills. |

## Plugin marketplaces

| Claude | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| `.claude-plugin/marketplace.json` with safe relative `source` | `.agents/skills` + `.codex/agents` | Imported when `--plugins` is passed | External, absolute, and parent-traversal sources are skipped. Plugins are experimental and are not imported by the default migration. |
| `metadata.pluginRoot` | No direct equivalent | Unsupported | Shorthand plugin sources that depend on `metadata.pluginRoot` are skipped unless the source is already a relative path. |
| Marketplace or `plugin.json` custom `skills` / `agents` paths | No direct equivalent | Unsupported | The converter only scans default `skills/` and `agents/` directories in local plugin sources. |
| `strict`, `commands`, `hooks`, `mcpServers`, `lspServers`, `outputStyles` | No direct equivalent | Unsupported | The converter imports plugin skills and agents only. |
| External `github` / `url` / `git-subdir` / `npm` sources | No package fetch in this converter | Skipped with summary counts | Offer manual install help instead of silently dropping them. |

## Hooks

| Claude | Codex | Migration behavior | Caveat |
| --- | --- | --- | --- |
| `hooks` in `~/.claude/settings.json`, `.claude/settings.json`, or `.claude/settings.local.json` | `.codex/hooks.json` + `[features].codex_hooks = true` | Partial conversion when `--hooks` is passed | Codex discovers `hooks.json` from active config-layer folders only when `features.codex_hooks` is enabled. Hooks are experimental and are not converted by the default migration. |
| `Notification` | `notify` | Manual rewrite only | `notify` is a turn-complete notification command, not a general lifecycle hook or approval-prompt hook. |
| `PreToolUse` | `PreToolUse` in `.codex/hooks.json` | Partial conversion | Codex currently runs PreToolUse for shell commands only and blocks only `permissionDecision: "deny"`, legacy `decision: "block"`, or exit code `2`. |
| `PostToolUse` | `PostToolUse` in `.codex/hooks.json` | Partial conversion | Codex currently runs PostToolUse for shell commands only; `decision: "block"` becomes model feedback, and `continue: false` stops execution. |
| `UserPromptSubmit` | `UserPromptSubmit` in `.codex/hooks.json` | Partial conversion | Codex can inject context or block a prompt, but it ignores `matcher` for this event and does not support Claude `if` filters. |
| `SessionStart` | `SessionStart` in `.codex/hooks.json` | Partial conversion | Codex matches `startup` and `resume`; Claude also documents `clear`, `compact`, and `CLAUDE_ENV_FILE` flows. |
| `Stop` | `Stop` in `.codex/hooks.json` | Partial conversion | Codex ignores `matcher` for Stop, can request a continuation prompt, and does not expose Claude's wider subagent/teammate stop lifecycle. |
| `PermissionRequest` / `SubagentStart` / `SubagentStop` / `TaskCreated` / `TaskCompleted` / `StopFailure` / `TeammateIdle` / `ConfigChange` / `CwdChanged` / `FileChanged` / `WorktreeCreate` / `WorktreeRemove` / `PreCompact` / `PostCompact` / `SessionEnd` / `Elicitation` / `ElicitationResult` / `InstructionsLoaded` | No direct equivalent | Unsupported | Keep as manual follow-up items; Codex does not expose matching lifecycle coverage today. |
| `type: "command"` | `type: "command"` | Partial conversion | `command`, `timeout` / `timeoutSec`, and `statusMessage` map. Empty commands are skipped by Codex. |
| `type: "prompt"` / `type: "agent"` / `type: "http"` / `async: true` | No direct equivalent | Unsupported | Codex parses `prompt` / `agent` but skips them, and async hooks are skipped. HTTP hooks need a wrapper command. |
| Hook `matcher` + `if` filters | Regex `matcher` only | Partial conversion | Codex keeps regex `matcher` for PreToolUse, PostToolUse, and SessionStart only. `UserPromptSubmit` and `Stop` matchers are ignored, and Claude `if` filters do not map. |
| Hooks in skills, agents, and plugins | No direct equivalent | Unsupported | Codex discovers hooks from config layers, not from skill or subagent manifests. |

## Minimal examples

Claude skill metadata becomes prompt guidance:

```md
allowed-tools:
  - Read
  - Bash
```

```md
## MANUAL MIGRATION REQUIRED

Claude `allowed-tools` was preserved as prompt guidance, not a Codex permission boundary.

You're allowed to use these tools:

- Read
- Bash
```

Claude subagent metadata becomes TOML plus prompt guidance:

```md
skills:
  - release-notes
tools:
  - Read
disallowedTools:
  - Bash
```

```toml
sandbox_mode = "workspace-write"
developer_instructions = """
## Skills
- $release-notes

## Tools
You're allowed to use these tools:
- Read

Don't use these tools:
- Bash
"""
```

## Sources

- https://docs.claude.com/en/docs/claude-code/claude_code_docs_map
- https://developers.openai.com/codex/config-reference
- https://developers.openai.com/codex/mcp
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/hooks
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/hooks-guide
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/plugin-marketplaces
- https://opencode.ai/docs/config/
- https://opencode.ai/docs/rules
- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/commands/
- https://opencode.ai/docs/plugins/
- https://opencode.ai/docs/skills/
- https://opencode.ai/docs/custom-tools/
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/README.md
- https://raw.githubusercontent.com/badlogic/pi-mono/main/packages/coding-agent/docs/packages.md
