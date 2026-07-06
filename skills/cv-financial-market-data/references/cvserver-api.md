# cvserver Financial Market Data API Reference

## Endpoints

The MCP tools map to the same runtime endpoints:

- `get_chain(symbol, fields?)` -> `POST /chains` with `{ "symbol": "SPY", "params": [...] }`
- `screen({ columns, filters, sort?, limit? })` -> `POST /screen`
- `query_sql({ sql, max_rows? })` -> `POST /query`
- `get_option_bars({ ticker, multiplier, timespan, from, to, adjusted?, sort?, limit? })` -> `POST /mas/aggs`
- `get_option_daily({ ticker, date, adjusted? })` -> `POST /mas/open-close`
- `fmp_request({ endpoint, params? })` -> `POST /fmp/stable/<endpoint>` with the params object as the request body
- `list_chain_fields()` is design-time only; the CLI keeps a static field list.
- `list_fmp_endpoints()` is design-time only; the CLI calls FMP endpoints by path.

For CLI calls, prefer the local cvforge proxy when available:

```text
http://127.0.0.1:<cvforge-port>/api/data
```

Direct calls to `https://tap.convexvalue.com/api/data` may be blocked by edge protections even when MCP access works. The bundled CLI therefore auto-discovers a running `cvforge` listener with `lsof` and falls back to direct configuration only when necessary.

Always verify the data path before heavier pulls:

```bash
python3 scripts/cv_options.py doctor --symbol SPY
```

`doctor` sends a one-row `/screen` request. It reports the base URL, whether auth is required, and a sample option contract. Treat a successful `doctor` as the gate before running full-chain commands such as `gamma-levels`, `vol-structure`, `vanna-exposure`, and `charm-exposure`.

## Main SQL Table

`options_snapshots` is the main read-only table. The SQL endpoint accepts only `SELECT` and `WITH` queries.

## API Families

### Options snapshot data

- `/chains`: full option chain for one underlying, grouped by expiration and strike. Use for per-strike and per-expiration analysis.
- `/screen`: row-oriented option-contract screener across underlyings. Use for filters, sorting, and compact exports.
- `/query`: read-only SQL against `options_snapshots`. Use for custom aggregates and one-off research.

### Option contract history

- `/mas/aggs`: historical OHLCV bars for one option contract ticker, not an underlying. Requires aggregate entitlement.
- `/mas/open-close`: one trading date of OHLCV data for one option contract ticker. Requires aggregate entitlement.

### FMP stable financial data

Call any supported Financial Modeling Prep `/stable` path at `/fmp/stable/<endpoint>`. Discover endpoints with `list_fmp_endpoints`.

Common categories:

- Quote: `quote`, `quote-short`, `batch-quote`, `batch-index-quotes`, `stock-price-change`.
- Chart: `historical-chart/1min`, `historical-chart/5min`, `historical-chart/15min`, `historical-chart/1hour`, `historical-price-eod/light`, `historical-price-eod/full`.
- Statements: `income-statement`, `balance-sheet-statement`, `cash-flow-statement`, `ratios`, `key-metrics`, `enterprise-values`, `financial-growth`.
- Company: `profile`, `market-capitalization`, `shares-float`, `stock-peers`, `key-executives`.
- Analyst: `analyst-estimates`, `grades`, `grades-historical`, `price-target-consensus`, `ratings-snapshot`.
- Calendar: `earnings-calendar`, `earnings`, `dividends-calendar`, `splits-calendar`, `ipos-calendar`.
- Economics: `treasury-rates`, `economic-calendar`, `economic-indicators`, `market-risk-premium`.
- Funds/ownership: `etf/holdings`, `etf/info`, `etf/sector-weightings`, `institutional-ownership/latest`.
- Filings/trades: `sec-filings-search/symbol`, `sec-profile`, `insider-trading/latest`, `senate-trades`, `house-trades`.
- News/market performance: `news/stock`, `news/stock-latest`, `news/general-latest`, `biggest-gainers`, `most-actives`, `sector-performance-snapshot`.
- Other supported families include search/directories, technical indicators, commodities, forex, crypto, commitment of traders, ESG, DCF, fundraising, and earnings transcripts.

## Common Fields

Default chain fields:

```text
expiration_date
strike_price
contract_type
implied_volatility
delta
gamma
theta
vega
bid
ask
midpoint
open_interest
day_volume
underlying_price
```

Full field set:

```text
underlying_ticker
ticker
break_even_price
implied_volatility
open_interest
fair_market_value
day_change
day_change_percent
day_close
day_high
day_last_updated
day_low
day_open
day_previous_close
day_volume
day_vwap
contract_type
exercise_style
expiration_date
shares_per_contract
strike_price
delta
gamma
theta
vega
ask
ask_size
bid
bid_size
quote_last_updated
midpoint
quote_timeframe
trade_conditions
trade_exchange
trade_price
trade_sip_timestamp
trade_size
trade_timeframe
underlying_change_to_break_even
underlying_last_updated
underlying_price
underlying_symbol
underlying_timeframe
fetched_at
```

## Response Shapes

`/chains` returns expirations grouped by strike:

```json
{
  "symbol": "SPY",
  "params": ["expiration_date", "strike_price", "contract_type", "gamma"],
  "chain": [
    {
      "expiration": "2026-06-19",
      "strikes": [
        [450.0, ["2026-06-19", 450.0, "call", 0.01], ["2026-06-19", 450.0, "put", 0.02]]
      ]
    }
  ]
}
```

`/screen` returns:

```json
{
  "columns": ["underlying_ticker", "ticker", "open_interest"],
  "rows": [["SPY", "O:SPY260619C00750000", 1000]],
  "row_count": 1
}
```

`/query` returns:

```json
{
  "rows": [{"underlying_ticker": "SPY", "contracts": 14360}],
  "row_count": 1,
  "truncated": false
}
```

`/mas/aggs` returns:

```json
{
  "ticker": "O:SPY260731P00550000",
  "results": [
    {"t": 1782878400000, "o": 0.2, "h": 0.22, "l": 0.17, "c": 0.19, "v": 101, "vw": 0.1949}
  ],
  "resultsCount": 1,
  "status": "OK"
}
```

`/mas/open-close` returns one object for the requested option contract and date. Fields vary by entitlement/source, but generally include open, high, low, close, volume, and status fields.

FMP `/stable` responses are usually arrays of objects:

```json
[
  {
    "symbol": "SPY",
    "price": 744.78,
    "changePercentage": -0.13141,
    "volume": 46819316
  }
]
```

FMP chart endpoints return arrays of OHLCV bars:

```json
[
  {"date": "2026-07-02 15:55:00", "open": 744.49, "high": 745.58, "low": 744.31, "close": 745.2, "volume": 853883}
]
```

## Formula Notes

Gamma dollar exposure per 1 percent spot move:

```text
gamma * open_interest * shares_per_contract * spot^2 * 0.01
```

The CLI's signed gamma convention is:

```text
call exposure = positive
put exposure = negative
```

ATM IV term structure:

```text
For each expiration, choose the strike nearest underlying_price and average available call/put IV.
```

Black-Scholes vanna:

```text
vanna = -exp(-qT) * normal_pdf(d1) * d2 / volatility
```

Charm proxy:

```text
one-day delta decay = delta(T - 1/365) - delta(T)
```

These are open-interest proxies and do not reveal actual dealer inventory.
