# Panelist prompt template

Fill the placeholders and send the result as ONE prompt via `herdr agent prompt`. Every panelist receives the identical question and context; only `{{ANSWER_FILE}}` differs. Do not add per-agent hints or extra instructions — identical input is what makes the comparison fair.

Placeholders:
- `{{QUESTION}}` — the user's question, verbatim (translate nothing, trim nothing).
- `{{CONTEXT_FILES}}` — absolute paths, one per line, single-quoted (paths may contain spaces). Omit the whole context block when there are no files.
- `{{ANSWER_FILE}}` — `<scratchpad>/council-<agent-name>-<n>.md`, where `<n>` is the question index in this session.

## Template

```
{{QUESTION}}

先阅读这些文件作为 context:
{{CONTEXT_FILES}}

要求:
- 给出明确的结论和取舍理由,不要只罗列选项。
- 回答完成后,把完整回答原样写入文件: {{ANSWER_FILE}}
```

## Notes for iteration

- Keep the answer-file instruction last; agents follow trailing instructions most reliably.
- The template asks for a definitive position ("明确的结论") because the judge compares options; hedged answers make the comparison table empty.
- If a future panelist CLI cannot write files, drop the file line for that agent and rely on terminal read.
