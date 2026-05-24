Focus session log viewer and summary generator for time tracking.

Arguments: $ARGUMENTS

## Commands

### `log` - Show today's sessions
Read ~/time-tracking/logs/{today's date in YYYY-MM-DD}.md and display the sessions table.

### `summary today` - Daily summary
Parse today's log file, count sessions per category, and generate a summary table with:
- Session count per category
- Estimated time (assume 25min per session if no duration)
- Percentage breakdown

### `summary week` - Weekly summary
Read all log files from the current week (Monday to Sunday), aggregate by category and day, generate a weekly summary showing:
- Sessions per category per day
- Daily totals
- Weekly totals

### `add <category> [notes]` - Manually add a session
Append a session entry to today's log with current time as end time.
Categories: coding, reviewing, meeting, learning, admin, break

## Log File Location
~/time-tracking/logs/YYYY-MM-DD.md

## Log Format
```markdown
# YYYY-MM-DD Focus Log

## Sessions
| End | Category | Notes |
|-----|----------|-------|
| HH:MM | category | notes |
```

When creating a new daily log file, include the header. When appending, just add the row.
