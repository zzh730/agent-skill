# Historical options

Official doc: [historical options](https://cvforge.convexvalue.com/docs/data/historical-options).

OHLC bars for **one option contract**, not an underlying. This is the time dimension the live snapshot does not have.

**Requires the Research plan** (`aggregates`). Other plans return `402`.

## Endpoints

| Route | MCP | Returns |
|---|---|---|
| `POST /mas/aggs` (or GET Massive v2 path) | `get_option_bars` | OHLC bars over a date range |
| `POST /mas/open-close` (or GET Massive v1 path) | `get_option_daily` | One trading day's OHLC + volume |

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `ticker` | yes | Contract ticker from the chain, e.g. `O:SPY260116C00400000`. Stock/ETF tickers also work for equity bars. |
| `multiplier` | yes (aggs) | Window size in timespan units |
| `timespan` | yes (aggs) | `second` `minute` `hour` `day` `week` `month` `quarter` `year` |
| `from` / `to` | yes (aggs) | `YYYY-MM-DD` or epoch milliseconds, inclusive |
| `date` | yes (open-close) | Trading date `YYYY-MM-DD` |
| `adjusted` | no | Split-adjusted. Default true. |
| `sort` | no | `asc` or `desc` by timestamp |
| `limit` | no | Max base aggregates. Default 5,000, max 50,000. |

## Response

Upstream JSON passes through. Each bar: `o` `h` `l` `c` `v` `vw` `n` `t` (window start, epoch ms).

```json
{
  "ticker": "O:SPY260116C00400000",
  "resultsCount": 124,
  "adjusted": true,
  "results": [
    { "o": 210.1, "h": 214.9, "l": 209.0, "c": 213.4, "v": 182, "vw": 212.33, "t": 1767330000000, "n": 24 }
  ],
  "status": "OK"
}
```

## Notes

- Latest day's bar mutates intraday. Older bars are effectively immutable.
- Unknown or never-traded contract/date → `404`. Other upstream failures → `502`.
- Illiquid strikes have gaps. Plot against time, not bar index.

Equity (stock/ETF) history on every plan is FMP `historical-chart/*` and `historical-price-eod/*`, not `/mas/*`.
