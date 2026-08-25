---
name: cv-financial-market-data
description: Query ConvexValue (cvforge) market data — live US option snapshots, cross-contract screens, read-only SQL, Research-plan option history, and 157 FMP fundamentals endpoints. Use when the user asks for option chains, IV, Greeks, fair market value, open interest, unusual volume, gamma or ATM IV, option contract bars, stock/ETF/index quotes, price charts, financial statements, ratios, analyst estimates, earnings dates, company profiles, SEC filings, 13F, insider or congressional trades, transcripts, news, treasury rates, economic data, ETF holdings, technical indicators, or DCF.
---

# CV Financial Market Data

Prefer MCP tools when they exist in the session. Use REST or `scripts/cv_data.py` for shell, CSV/JSON, or local checks.

## Access

- MCP: `https://tap.convexvalue.com/api/data/mcp`
- REST: `https://tap.convexvalue.com/api/data`
- Tools: `get_chain`, `screen`, `query_sql`, `get_option_bars`, `get_option_daily`, `fmp_request`, `list_fmp_endpoints`, `list_chain_fields`
- Auth: At authorization time, read `CVSERVER_API_TOKEN` from the current terminal/process environment and send it as `Authorization: Bearer <CVSERVER_API_TOKEN>`. Do not ask the user to paste it. Never print, log, or copy the token. The CLI may use its documented legacy fallbacks only when this variable is unset.
- `cvApi.chain` / `screen` / `query` / `call` exist only inside a cvforge app page. Do not fetch `tap.convexvalue.com` from that page.

Details: [api-access.md](references/api-access.md)

## Hard rules

1. Current option value is `fair_market_value` only. It is an estimate, not an executable quote.
2. Do not request option bid, ask, size, midpoint, NBBO, or last-trade fields. They are not provided.
3. Use only the 31 supported snapshot fields. Default set: [options-snapshot.md](references/options-snapshot.md).
4. Index underlyings: `I:SPX`, `I:VIX`, `I:NDX`, `I:RUT`, `I:XSP`.
5. Snapshot refreshes about once a minute. Open interest updates after the close. SQL tables have no history.
6. `/mas/*` (`get_option_bars`, `get_option_daily`) needs the Research plan. Other plans return `402`.
7. Every data call counts against one hourly budget: Free 20, Go 1,000, Research 50,000.
8. Do not invent FMP paths. If the path is unknown, call `list_fmp_endpoints` first.
9. `list_chain_fields` is discovery only. A raw field name is not a product promise.

## Route the question

| Question | Family | Call |
|---|---|---|
| One underlying chain, IV surface, skew, OI wall, payoff | Snapshot | `get_chain` / `POST /chains` |
| Cross-name scan: high IV, unusual volume, high OI | Screener | `screen` / `POST /screen` |
| GROUP BY, PCR, GEX, ATM IV, custom aggregate | SQL | `query_sql` / `POST /query` |
| One option contract's history | Historical | `get_option_bars` or `get_option_daily` |
| Stock / ETF snapshot or price | FMP company | `profile` |
| Index quote | FMP indexes | `quote` or `quote-short` |
| Equity intraday or EOD bars | FMP chart | `historical-chart/*` or `historical-price-eod/*` |
| Statements, ratios, metrics, scores | FMP statements | `income-statement`, `ratios`, `key-metrics`, … |
| Analyst consensus | FMP analyst | `analyst-estimates` only |
| Earnings date | FMP calendar | `earnings` or `earnings-calendar` |
| Macro / rates | FMP economics | `treasury-rates`, `economic-indicators`, `economic-calendar` |
| ETF holdings / weights | FMP ETF | `etf/holdings`, `etf/info`, `etf/sector-weightings` |
| 13F / institutional | FMP 13F | `institutional-ownership/*` |
| Insider / Congress | FMP insider or senate | `insider-trading/*`, `senate-trades`, `house-trades` |
| SEC filings / 8-K | FMP SEC | `sec-filings-search/*`, `sec-filings-8k` |
| Transcript | FMP transcript | `earning-call-transcript` |
| News | FMP news | `news/stock`, `news/stock-latest` |
| Technical series | FMP technicals | `technical-indicators/{sma,ema,rsi,…}` |
| DCF | FMP DCF | `discounted-cash-flow` |
| Find a ticker | FMP search | `search-symbol`, `search-name` |

Catalog and required params: [fmp-catalog.md](references/fmp-catalog.md)

## CLI

```bash
python3 scripts/cv_data.py doctor --symbol SPY
python3 scripts/cv_data.py chain SPY --limit 10
python3 scripts/cv_data.py screen --symbol SPY --min-oi 5000 --limit 10
python3 scripts/cv_data.py query "SELECT expiration_date, AVG(implied_volatility) FILTER (WHERE ABS(delta) BETWEEN 0.45 AND 0.55) AS atm_iv FROM options_snapshots WHERE underlying_ticker = 'SPY' GROUP BY 1 ORDER BY 1"
python3 scripts/cv_data.py fmp profile --param symbol=AAPL
python3 scripts/cv_data.py gamma-levels SPY --top 20
```

`--format table|json|csv`. Run `api-help` for more.

## References

- [options-snapshot.md](references/options-snapshot.md) — fields, chain shape, pricing boundary
- [screener.md](references/screener.md) — operators and limits
- [sql.md](references/sql.md) — tables and official recipes
- [historical-options.md](references/historical-options.md) — `/mas/*`
- [fmp-catalog.md](references/fmp-catalog.md) — 157 allowlisted endpoints
- [analysis.md](references/analysis.md) — GEX, ATM IV, local vanna/charm
