---
name: cv-options-data
description: Query and analyze live US equity/index options data from cvserver. Use when the user asks to fetch option chains, screen contracts, run read-only options SQL, inspect available fields, export options data, or compute gamma levels, ATM IV term structure, vanna exposure, or charm exposure for tickers such as SPY, QQQ, NVDA, TSLA, AAPL, I:SPX, I:NDX, I:RUT, or I:VIX.
---

# CV Options Data

## Overview

Use this skill to retrieve cvserver options data and run repeatable command-line analyses. Prefer the provided MCP tools when they are available in the current session; use the bundled CLI when the user wants a shell workflow, CSV/JSON output, or repeatable local verification.

## Data Access

- Start CLI sessions with `python3 scripts/cv_options.py doctor --symbol SPY` to verify that data access works before running heavier chain or exposure commands.
- Use `mcp__cvserver__get_chain` for one underlying's full chain.
- Use `mcp__cvserver__screen` for cross-contract filters.
- Use `mcp__cvserver__query_sql` only for read-only `SELECT` or `WITH` queries.
- Use `mcp__cvserver__list_chain_fields` to refresh available fields.
- For CLI work, run `scripts/cv_options.py`; it first tries to find a running local cvforge preview proxy at `http://127.0.0.1:<port>/api/data`.
- If no local proxy is available, the CLI can use `CVSERVER_DATA_BASE`, `CV_OPTIONS_BASE`, or `CVFORGE_DATA_BASE` to point at a data proxy.
- For direct non-local endpoints, the CLI reads auth from `CVSERVER_API_TOKEN`, `CV_API_TOKEN`, `CONVEXVALUE_API_TOKEN`, or a local cvforge `.mcp.json` / `.codex/config.toml` found from the current directory upward.
- Never print, commit, or copy the API token. Treat `.mcp.json` and `.codex/config.toml` as local credentials.

Index underlyings use the `I:` prefix: `I:SPX`, `I:NDX`, `I:RUT`, `I:VIX`. Stocks and ETFs use ordinary tickers such as `SPY`, `QQQ`, `NVDA`, `TSLA`, `AAPL`.

## CLI Quick Start

Run the script directly:

```bash
python3 /path/to/cv-options-data/scripts/cv_options.py doctor --symbol SPY
python3 /path/to/cv-options-data/scripts/cv_options.py fields
python3 /path/to/cv-options-data/scripts/cv_options.py chain SPY --limit 10
python3 /path/to/cv-options-data/scripts/cv_options.py screen --symbol SPY --min-oi 5000 --min-volume 1000 --limit 10
python3 /path/to/cv-options-data/scripts/cv_options.py query "SELECT underlying_ticker, COUNT(*) AS contracts FROM options_snapshots GROUP BY underlying_ticker ORDER BY contracts DESC LIMIT 20"
```

Supported output formats:

```bash
--format table
--format json
--format csv
```

## Analysis Commands

Use these commands for derived structure views:

```bash
python3 scripts/cv_options.py gamma-levels SPY --top 20
python3 scripts/cv_options.py vol-structure SPY
python3 scripts/cv_options.py vanna-exposure SPY --top 20 --rate 0.045 --dividend-yield 0
python3 scripts/cv_options.py charm-exposure SPY --top 20 --rate 0.045 --dividend-yield 0
```

Optional filters:

```bash
--expiration 2026-06-19
--min-oi 100
--as-of 2026-06-15
```

## Interpretation Rules

- `gamma-levels` computes a signed open-interest proxy by strike. Calls are treated as positive and puts as negative by default.
- `vol-structure` selects the nearest-ATM strike per expiration and averages available call/put IV.
- `vanna-exposure` uses Black-Scholes vanna, then multiplies by open interest and contract size.
- `charm-exposure` uses one-calendar-day Black-Scholes delta decay, then multiplies by open interest and contract size.
- Vanna and charm are model estimates, not reported exchange fields and not true dealer positioning.
- All calculations must tolerate missing `bid`, `ask`, `midpoint`, `day_volume`, `underlying_price`, and Greek values.
- If `underlying_price` is missing, gamma/vanna/charm rows for that contract are skipped; for vol structure, the CLI falls back to nearest 50-delta when possible.

Read `references/cvserver-api.md` before changing formulas, field assumptions, or endpoint behavior.

## Verification

For local verification, run from a cvforge repo with `.mcp.json` available or set `CVSERVER_API_TOKEN`.
If cvforge is running, the CLI should use the local proxy automatically. You can also set `CVSERVER_DATA_BASE`, for example `http://127.0.0.1:53903/api/data`.

```bash
python3 scripts/cv_options.py doctor --symbol SPY
python3 scripts/cv_options.py fields
python3 scripts/cv_options.py chain SPY --limit 5
python3 scripts/cv_options.py screen --symbol SPY --min-oi 5000 --limit 5
python3 scripts/cv_options.py gamma-levels SPY --top 5
python3 scripts/cv_options.py vol-structure SPY
```
