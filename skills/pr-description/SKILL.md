---
name: pr-description
description: Write or update a GitHub pull request description in the problem / solution / verification format, with before-and-after architecture diagrams rendered by Pele when the change moves a component, a boundary, or a data flow. Use when opening a PR, when refreshing a PR body after new commits, or when the user asks for a PR description, PR summary, or architecture diagram for a PR.
---

# PR description

Write a short PR body that a reviewer who has not seen the conversation can act on. When the change alters the architecture, show it as two diagrams: before and after.

`<skill-dir>` below is the folder that holds this `SKILL.md`. This skill needs the `pele-diagram` skill installed next to it.

## 1. Collect facts

- Rules first. A repository PR template (`.github/pull_request_template.md`) or `AGENTS.md` / `CLAUDE.md` rules about PR text override this skill where they conflict. On a machine with `~/.codex/LESSONS.md` and `~/.codex/references/pr-acceptance.md`, read them: they set what counts as verification evidence.
- PR state: `gh pr view --json number,url,title,baseRefName,headRefOid`. Save the body with `gh pr view <pr> --json body --jq .body > baseline.md`: it is the baseline for the edit check in step 5.
- Change: `git log --oneline <base>..HEAD`, `git diff <base>...HEAD --stat`, then read the hunks that carry the behavior change. Find the linked issue and earlier PRs.

## 2. Decide whether the PR needs diagrams

Draw before and after when the PR changes any of these:

- a component, service, process, queue, store, or external dependency (added, removed, split, or merged);
- who calls whom, the protocol, sync versus async, or the order of steps on a request path;
- where data lives, or which component owns it;
- a trust, network, tenancy, or process boundary.

Skip the diagrams for a fix inside one component, a refactor that keeps the same calls, tests, docs, configuration values, and dependency bumps. Do not add a placeholder section. If you are not sure, draw them: a wrong "no change" hides risk from the reviewer.

## 3. Build the two diagrams from the code

1. List the components on the changed path. For each one, find the code that implements it at the base (`git show <base>:<path>`) and at the head. Every node and edge must map to code you read, not to memory or to the PR title.
2. Write `before.mmd` from the base and `after.mmd` from the head, in a scratch directory outside the repository. Use the same node IDs, labels, direction, and declaration order in both, so the two layouts line up.
3. Mark only what changes. In before: `removed` for what goes away, `changed` for what keeps its place but changes behavior. In after: `added` and `changed`. See the `pele-diagram` skill for syntax and the `classDef` lines.
4. Show the changed components and one hop of neighbors, 12 nodes or fewer. Label each edge with the call or protocol.
5. Use a `sequenceDiagram` pair instead when the PR changes the order or timing of calls (retries, async handoff, locking).
6. Render with `pele-render --png`, look at the light and dark PNGs, and fix every problem you see. Follow the `pele-diagram` workflow.

## 4. Publish the images and write the body

Inside the PR checkout, run:

```bash
<skill-dir>/scripts/pr-arch-section \
  --before <dir>/before.mmd --before-alt "<old flow in one sentence>" \
  --after <dir>/after.mmd --after-alt "<new flow in one sentence>"
```

It renders both files, pushes the SVGs to the image branch of the same repository with `pele-publish`, and prints the Markdown: the images (side by side when both are narrow, stacked otherwise), a legend for the classes you used, and the Mermaid source as text in a collapsed block. Omit `--before` when the PR adds a new system. Write alt text that states the change, because email notifications and readers without image access see only the text.

When you must not upload images (for example, the user says no), skip `pr-arch-section`. Put each diagram in a `mermaid` code block under **Before** and **After**, and keep the legend. GitHub draws it with the viewer's theme. Run `pele-render --check` on the files first, and fix every `classDef` warning. A `fill` or `color` in a class makes edges into colored wedges and makes text hard to read in dark mode.

Put that block at the end of `## solution`:

````markdown
## problem

- Current behavior, then the risk. Link the issue or evidence next to the claim.

## solution

- What changed, and how it fixes the problem. Name limits and follow-ups.

**Before**

![Before: the API keeps sessions in a per-process cache](https://github.com/<owner>/<repo>/raw/<sha>/<key>/before.svg)

**After**

![After: the API reads sessions from Redis; a worker expires them](https://github.com/<owner>/<repo>/raw/<sha>/<key>/after.svg)

<sub>Green: added. Red, dashed: removed. Amber: changed.</sub>

<details>
<summary>Diagram source</summary>

(Mermaid source of both diagrams)

</details>

## verification

- Tests run and their results. For a bug fix, the test that fails on the base and its message.
- E2E: the scenario, the runner, the head SHA, the result, and the proof. Or `E2E: not applicable (<reason>)`.
- Checks not run, and why.
````

Writing rules:

- Title: short and specific; it names the resulting behavior.
- Lowercase section headings, bullets, plain words, active voice. Write facts the reader can check, not verdicts.
- `## problem`: what happens today, then what can go wrong. Stop there.
- `## verification`: distinguish local tests, CI on the current head SHA, E2E, and deployment. One does not prove another.
- Scale the body to the change. A small PR gets a small description.

## 5. Publish the body safely

New PR:

```bash
gh pr create --draft --title "<title>" --body-file body.md
```

Existing PR: other people and agents edit PR bodies. Compare the live body with the baseline from step 1, and stop if they differ:

```bash
gh pr view <pr> --json body --jq .body > live.md
diff -q live.md baseline.md || { echo "PR body changed since you read it; merge the edits into body.md first"; exit 1; }
gh pr edit <pr> --body-file body.md
gh pr view <pr> --json body --jq .body > baseline.md
```

Always write `baseline.md` with the same `gh pr view` command as `live.md`, never by copying `body.md`: `--jq` adds a newline, so a copy never matches. The last line also reads the body back; confirm that each image URL is in it.

## 6. Keep the diagrams current

When new commits change the architecture again, update the `.mmd` files, run `pr-arch-section` again, and replace the old section. Each publish has a new commit URL, so old comments keep their old images. Do not leave diagrams that describe an older head.

## Privacy

`pele-publish` stores images in the same repository as the PR, so only people with read access can see them. Never upload a diagram of a private system to a public repository, a gist, or an image host.

`pele-publish` refuses a repository that is not private or internal, so `pr-arch-section` fails there. In a public repository, pass `--allow-public` to `pr-arch-section` only when every diagram may be public. Otherwise use the `mermaid` blocks from step 4.
