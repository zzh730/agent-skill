# Agent Skill Source Of Truth

Personal source of truth for agent skills, selected Claude slash commands, and third-party skill dependency references.

## Common Commands

```bash
./scripts/bootstrap --targets claude,codex
./scripts/add-third-party-skill --name <name> --upstream <git-url> --ref <branch-or-tag> --skill-path <path> --targets claude,codex
./scripts/sync-third-party-skills --update-lock
./scripts/import-local-skill --from claude --name <skill-name>
./scripts/doctor
```

See `docs/agent-skill-source-of-truth-plan.md` for the operating model.
