# Agent Skill Source Of Truth V1

## Summary

This repository is the source of truth for personal agent assets. It owns self-written skills, selected personal Claude slash commands, dependency manifests, and sync scripts. Local Claude Code and Codex skill directories are install targets, not authoritative state.

## Repository Layout

- `skills/`: self-owned skills copied into Git.
- `skill-variants/<target>/`: target-specific versions used when one agent needs different skill instructions.
- `commands/claude/`: selected personal Claude slash commands.
- `sources/third-party-skills.yaml`: third-party dependency manifest.
- `sources/third-party-skills.lock`: resolved upstream commits.
- `sources/personal-skills.yaml`: imported self-owned local skills.
- `sources/excluded-skills.yaml`: internal or company-bound skills that drift checks should ignore.
- `scripts/bootstrap`: install repo assets into local Claude, Codex, and Grok Build targets using the lockfile.
- `scripts/add-third-party-skill`: add a new third-party skill reference and resolve its initial lock entry.
- `scripts/sync-third-party-skills`: fetch/update third-party dependencies and optionally refresh the lockfile.
- `scripts/import-local-skill`: import newly created local skills from Claude, Codex, Agents, or Grok Build directories.
- `scripts/doctor`: detect drift between repo, local installs, and third-party locks.

## Operating Model

Git repo state is authoritative. Local `~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`, and `~/.grok/skills` are generated installs.

Third-party skills are dependencies. Their source of truth stays in the upstream repository; this repo records the upstream URL, tracked ref, skill path, install targets, and resolved commit.

New skills created by Claude Code Skill Creator are local drafts until imported:

```bash
./scripts/import-local-skill --from claude --name <skill-name>
```

## Commands

Bootstrap a machine from the current repo state:

```bash
./scripts/bootstrap --targets claude,codex,grok
```

Add a third-party dependency:

```bash
./scripts/add-third-party-skill \
  --name planning-with-files \
  --upstream https://github.com/OthmanAdi/planning-with-files.git \
  --ref main \
  --skill-path planning-with-files \
  --targets claude,codex,grok
```

Import a user-created Grok Build skill:

```bash
./scripts/import-local-skill --from grok --name <skill-name>
```

Import a Grok Build bundled skill when it should also be available to other agents:

```bash
./scripts/import-local-skill --from grok-bundled --name <skill-name>
```

Grok Build's bundled directory is import-only. Bootstrap always installs managed skills into `~/.grok/skills`.

When a skill has a target-specific version, import the common version first, then the override:

```bash
./scripts/import-local-skill --from agents --name <skill-name>
./scripts/import-local-skill --from claude --name <skill-name> --variant-for claude
```

Bootstrap automatically selects `skill-variants/<target>/<skill-name>` when present and otherwise uses the common copy under `skills/`.

Refresh third-party locks:

```bash
./scripts/sync-third-party-skills --update-lock
```

Check drift:

```bash
./scripts/doctor
```

## Migration Policy

Include personal and public third-party skills. Exclude DoorDash/internal/company-service-bound skills by default, even if they were personally authored, unless explicitly whitelisted later.

Local edits to installed third-party copies are not preserved automatically. Convert them into a fork, an override, or a self-owned skill before relying on them.
