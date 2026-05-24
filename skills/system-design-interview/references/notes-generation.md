# Post-Interview Notes Generation

After the debrief (or when the candidate requests notes), generate **Q&A-style interview preparation notes**. The notes preserve the interview as a learning artifact — not a polished summary.

## Why Q&A Format

The Q&A format forces the candidate to confront their actual gaps rather than reading a clean summary that feels like they already knew the material. The original (wrong) answers are the most valuable part — they reveal thinking patterns to fix.

## Format

Structure the notes as a sequence of Q&A blocks, one per interviewer question or topic:

```markdown
### Q: [The interviewer's question, as asked]

**My answer:** [What the candidate actually said — include mistakes, vagueness, and gaps faithfully]

**Correction / Feedback:** [What was wrong, what was missing, what the interviewer pushed back on]

**Corrected answer:** [The improved version — what the candidate should say next time]

**Gap identified:** [One-sentence summary of what was missed and why it matters]
```

## Content Rules

1. **Preserve the candidate's original answers honestly** — including errors, vague statements, and incomplete reasoning. Do NOT clean up or polish their answers. The value is in seeing where they went wrong.
2. **Preserve every interviewer question** that led to meaningful feedback. Skip only trivial back-and-forth.
3. **Include corrected versions** with enough detail that the candidate can study them standalone.
4. **Mark corrections explicitly** — use labels like "Correction:", "Problem raised:", "Follow-up I missed:" so the candidate can scan for their gaps.
5. **Include diagrams, schemas, tables, and code blocks** in corrected answers where the interviewer provided or expected them.

## Gaps Summary Table (Required at the End)

Always end the notes with a summary table:

```markdown
## Gaps Summary

| Area | Gap | What I Should Have Said |
|---|---|---|
| **[Topic]** | [What I said or missed] | [Corrected version in one sentence] |
```

This table serves as a rapid-review checklist before real interviews.
