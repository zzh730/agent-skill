# Council report template

The judge reads every answer first, then writes the report. Verdict first, evidence after.

## Writing rules (apply to every section)

- Expand every point into 2–4 full sentences: state the claim, then explain the mechanism or reason in plain language. One-line compressed bullets are forbidden — the reader may not hold the technical context the panelists assumed.
- Define a term of art the first time it appears (one clause is enough: "ISN — the initial sequence number each side picks").
- Table cells stay short (choice + keyword), but every table gets a prose paragraph below it that walks through the rows for a reader who skipped the panelists' answers.
- Write for a smart reader outside the niche, not for the panelists.

## Chat reply structure

1. **Verdict** — which option the judge picks and why, in full sentences. Name each losing option and the single strongest argument against it.
2. **Consensus vs split** — what the panelists agree on (state it once, expanded per the writing rules) and where they diverge (name who holds which position and what hinges on it).
3. **Horizontal comparison** — a table: one row per decision axis, one column per panelist, cells = choice + key argument. Follow with the explanatory prose paragraph.
4. **Unique contributions** — per panelist, the points worth keeping regardless of the verdict, each explained in a sentence or two. Skip a panelist that added nothing unique and say so.
5. **Pointers** — the council tab id, pane ids, the HTML report path, and answer-file paths.

## HTML report (the annotation surface)

Render the full report to `<scratchpad>/council-report-<n>.html`, one file per round, previous versions kept:

- Self-contained single file: inline CSS, no external assets, no JS required. Readable typography (max-width ~46rem, system font stack, borders on tables).
- Theme-aware, never transparent: the annotation viewer renders the file inside its own (often dark) chrome, so hard-coded dark text with no background becomes invisible. Always set an explicit `background` on `html, body`, define colors as CSS variables with a light default, and override the variables under `@media (prefers-color-scheme: dark)`.
- Same section order as the chat reply, followed by one section per panelist: `<h2><agent> (<kind>, <model>, <effort>, worked <duration>)</h2>` and the answer converted to HTML, unedited in content.
- This file is what `plannotator annotate` opens; write it so a comment can anchor anywhere — keep paragraphs short and headings frequent.

## Annotation follow-up loop

- Each Plannotator annotation is a follow-up question. Build the follow-up prompt as: the quoted annotated passage + the user's comment, sent to the panel via the standard PROMPT.md template (agents keep their context; answer files get the next index).
- Judge the new answers, render `council-report-<n+1>.html` containing the follow-up Q&A appended as a new section, and open it with `plannotator annotate` again.
- Approved or dismissed ends the loop.

## `--out` archive

With `--out <file>`: write the same full content as the HTML report in markdown to that path; the chat reply stays summary-only and links both files.

## Judging rules

- Judge only: never author an independent answer before reading the panelists; the verdict must cite panelist arguments, not introduce new ones (pointing out a flaw all panelists missed is allowed, flagged as the judge's own note).
- If panelists converge, say so plainly — a unanimous council is a result, not a failure to compare.
- If an agent is still working at report time, publish without it and say which pane to check later; never fabricate or predict its answer.
