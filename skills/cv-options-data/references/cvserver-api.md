# cvserver Options API Reference

## Endpoints

The MCP tools map to the same runtime endpoints:

- `get_chain(symbol, fields?)` -> `POST /chains` with `{ "symbol": "SPY", "params": [...] }`
- `screen({ columns, filters, sort?, limit? })` -> `POST /screen`
- `query_sql({ sql, max_rows? })` -> `POST /query`
- `list_chain_fields()` is design-time only; the CLI keeps a static field list.

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
