---
name: cv-financial-market-data
description: Query and analyze cvserver financial market data for stocks, ETFs, indexes, options, macro, fundamentals, and FMP /stable endpoints. Use when the user asks to fetch stock or ETF quotes and price bars, option chains, option contract history, option screens, read-only options SQL, CSV/JSON market-data exports, available fields or endpoints, gamma/vol/vanna/charm/max-pain/expected-move analysis, or FMP data such as financial statements, ratios, key metrics, analyst estimates, calendars, treasury rates, economic data, ETF holdings, SEC filings, insider or congressional trades, news, forex, crypto, commodities, and sector or industry data.
---

# CV Financial Market Data

## Overview

Use this skill to retrieve cvserver market and financial data, then run repeatable command-line analyses. Prefer the provided MCP tools when they are available in the current session; use the bundled CLI when the user wants a shell workflow, CSV/JSON output, raw API calls, or repeatable local verification.

## Data Access

- Start CLI sessions with `python3 scripts/cv_options.py doctor --symbol SPY` to verify that data access works before running heavier chain or exposure commands.
- Use `mcp__cvserver__get_chain` for one underlying's full chain.
- Use `mcp__cvserver__screen` for cross-contract filters.
- Use `mcp__cvserver__query_sql` only for read-only `SELECT` or `WITH` queries.
- Use `mcp__cvserver__list_chain_fields` to refresh available fields.
- Use `mcp__cvserver__get_option_bars` and `mcp__cvserver__get_option_daily` for one option contract's historical OHLCV data.
- Use `mcp__cvserver__list_fmp_endpoints` before `mcp__cvserver__fmp_request` when selecting FMP `/stable` endpoints.
- For CLI work, run `scripts/cv_options.py`; it first tries to find a running local cvforge preview proxy at `http://127.0.0.1:<port>/api/data`.
- If no local proxy is available, the CLI can use `CVSERVER_DATA_BASE`, `CV_OPTIONS_BASE`, or `CVFORGE_DATA_BASE` to point at a data proxy.
- For direct non-local endpoints, the CLI reads auth from `CVSERVER_API_TOKEN`, `CV_API_TOKEN`, `CONVEXVALUE_API_TOKEN`, or a local cvforge `.mcp.json` / `.codex/config.toml` found from the current directory upward.
- Never print, commit, or copy the API token. Treat `.mcp.json` and `.codex/config.toml` as local credentials.

Index underlyings use the `I:` prefix: `I:SPX`, `I:NDX`, `I:RUT`, `I:VIX`. Stocks and ETFs use ordinary tickers such as `SPY`, `QQQ`, `NVDA`, `TSLA`, `AAPL`.

## API Surface

Use these endpoint families through MCP tools, `window.cvApi.call(...)` in cvforge pages, or the CLI wrapper commands below:

- `/chains`: option chain for one underlying. Use for IV surfaces, greeks ladders, gamma levels, skew, max pain, expected move, and expiration/strike analysis.
- `/screen`: cross-contract option screen. Use for high OI, high volume, high IV, unusual volume, expiry/type filters, and cross-symbol scans.
- `/query`: read-only SQL against `options_snapshots`. Use only `SELECT` or `WITH`.
- `/mas/aggs`: historical OHLCV bars for one option contract ticker, such as `O:SPY260731P00550000`.
- `/mas/open-close`: one trading date of OHLCV data for one option contract ticker.
- `/fmp/stable/<endpoint>`: FMP stock, ETF, index, macro, fundamental, calendar, and news data.
- Design-time only: `list_chain_fields` and `list_fmp_endpoints` are MCP helpers; they are not runtime data endpoints.

Common FMP `/stable` categories and examples:

- Quotes and market data: `quote`, `quote-short`, `batch-quote`, `batch-index-quotes`, `stock-price-change`.
- Price charts: `historical-chart/1min`, `historical-chart/5min`, `historical-chart/15min`, `historical-chart/1hour`, `historical-price-eod/light`, `historical-price-eod/full`.
- Fundamentals: `income-statement`, `balance-sheet-statement`, `cash-flow-statement`, `ratios`, `key-metrics`, `enterprise-values`, `financial-growth`.
- Company data: `profile`, `market-capitalization`, `shares-float`, `stock-peers`, `key-executives`.
- Analyst data: `analyst-estimates`, `grades`, `grades-historical`, `price-target-consensus`, `ratings-snapshot`.
- Calendars and transcripts: `earnings-calendar`, `earnings`, `dividends-calendar`, `splits-calendar`, `ipos-calendar`, `earning-call-transcript`.
- Macro and rates: `treasury-rates`, `economic-calendar`, `economic-indicators`, `market-risk-premium`.
- Funds and ownership: `etf/holdings`, `etf/info`, `etf/sector-weightings`, `institutional-ownership/latest`.
- Filings and events: `sec-filings-search/symbol`, `sec-profile`, `insider-trading/latest`, `senate-trades`, `house-trades`.
- News and broad markets: `news/stock`, `news/stock-latest`, `news/general-latest`, `biggest-gainers`, `most-actives`, `sector-performance-snapshot`.
- Other covered sets: search/directories, technical indicators, commodities, forex, crypto, commitment of traders, ESG, DCF, and fundraising endpoints.

Read `references/cvserver-api.md` for response shapes, field lists, endpoint mappings, and formula notes.

## CLI Quick Start

Run the script directly:

```bash
python3 /path/to/cv-financial-market-data/scripts/cv_options.py doctor --symbol SPY
python3 /path/to/cv-financial-market-data/scripts/cv_options.py fields
python3 /path/to/cv-financial-market-data/scripts/cv_options.py chain SPY --limit 10
python3 /path/to/cv-financial-market-data/scripts/cv_options.py screen --symbol SPY --min-oi 5000 --min-volume 1000 --limit 10
python3 /path/to/cv-financial-market-data/scripts/cv_options.py query "SELECT underlying_ticker, COUNT(*) AS contracts FROM options_snapshots GROUP BY underlying_ticker ORDER BY contracts DESC LIMIT 20"
python3 /path/to/cv-financial-market-data/scripts/cv_options.py fmp quote --param symbol=SPY
python3 /path/to/cv-financial-market-data/scripts/cv_options.py option-bars O:SPY260731P00550000 --from 2026-07-01 --to 2026-07-03 --timespan day
python3 /path/to/cv-financial-market-data/scripts/cv_options.py api-help
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

## Raw API Wrapper Commands

Use `call` when you want direct access to the same runtime API exposed in cvforge:

```bash
python3 scripts/cv_options.py call /chains --body '{"symbol":"SPY","params":["expiration_date","strike_price","delta"]}' --format json
python3 scripts/cv_options.py call /screen --body '{"columns":["ticker","open_interest"],"filters":[{"field":"underlying_ticker","op":"eq","value":"SPY"}],"limit":5}'
python3 scripts/cv_options.py call /query --body '{"sql":"SELECT underlying_ticker, COUNT(*) AS contracts FROM options_snapshots GROUP BY 1 LIMIT 10"}'
python3 scripts/cv_options.py call /mas/aggs --body '{"ticker":"O:SPY260731P00550000","multiplier":1,"timespan":"day","from":"2026-07-01","to":"2026-07-03","sort":"asc"}' --rows-key results
python3 scripts/cv_options.py call /mas/open-close --body '{"ticker":"O:SPY260731P00550000","date":"2026-07-02"}'
python3 scripts/cv_options.py call /fmp/stable/quote --body '{"symbol":"SPY"}'
python3 scripts/cv_options.py call /fmp/stable/historical-chart/5min --param symbol=SPY --param from=2026-07-02 --param to=2026-07-03
```

Use `fmp` for Financial Modeling Prep `/stable` endpoints through the same data proxy:

```bash
python3 scripts/cv_options.py fmp quote --param symbol=SPY
python3 scripts/cv_options.py fmp historical-chart/5min --param symbol=SPY --param from=2026-07-02 --param to=2026-07-03
python3 scripts/cv_options.py fmp treasury-rates --format json
python3 scripts/cv_options.py fmp earnings-calendar --param from=2026-07-05 --param to=2026-07-12
python3 scripts/cv_options.py fmp income-statement --param symbol=AAPL --param period=annual --param limit=5
python3 scripts/cv_options.py fmp etf/holdings --param symbol=SPY
python3 scripts/cv_options.py fmp news/stock-latest --param limit=20
```

Use option-history helpers for one concrete option ticker:

```bash
python3 scripts/cv_options.py option-bars O:SPY260731P00550000 --from 2026-07-01 --to 2026-07-03 --timespan day
python3 scripts/cv_options.py option-daily O:SPY260731P00550000 --date 2026-07-02
```

Use wrapper conveniences:

```bash
python3 scripts/cv_options.py call /screen --body-file screen.json --format csv
echo '{"symbol":"SPY"}' | python3 scripts/cv_options.py fmp quote --body -
python3 scripts/cv_options.py fmp quote --param symbol=SPY --dry-run --format json
python3 scripts/cv_options.py call /screen --body '{"columns":["ticker"],"filters":[],"limit":1}' --base-url http://127.0.0.1:53903/api/data
```
