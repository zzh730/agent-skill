# Options snapshot

Official doc: [options snapshot](https://cvforge.convexvalue.com/docs/data/options-snapshot).

Live snapshot of every listed US option contract. Refresh is about once a minute. Source is Massive's options snapshot feed.

**Pricing boundary:** cvforge does not provide option bid/ask, quote sizes, midpoint, NBBO, or last-trade data. `fair_market_value` is the only current per-contract valuation. It is a proprietary estimate. Do not present it as an executable quote.

## Coverage

- Every optionable US stock and ETF (universe refreshes daily).
- Index options: `I:SPX`, `I:VIX`, `I:NDX`, `I:RUT`, `I:XSP`.
- Open interest updates once daily after the close. FMV, Greeks, IV, and session data update with the snapshot.

## Call

MCP: `get_chain({ symbol, fields? })`
REST POST: `{ "symbol": "SPY", "params": ["expiration_date", "strike_price", "implied_volatility"] }`
REST GET: `/chains/SPY?params=expiration_date,strike_price,implied_volatility`
cvApi: `cvApi.chain('SPY')` or `cvApi.chain('I:SPX', ['expiration_date', 'strike_price'])`

Rules:

- `symbol`: 1–24 characters; letters, digits, `. - / :`; uppercased by the server.
- `params`: 1–32 supported field names. Duplicates dropped. `cvApi.chain()` may omit this and use the default set. REST POST `/chains` requires `params`; send the default set below when the user does not name fields.
- Responses may include `x-cv-cache: hit|miss`. GET sets `Cache-Control: private, max-age=15`.

## Response shape

Contracts group by expiration, then strike. Each strike is `[strike, callValues, putValues]`. Value arrays follow the requested `params` order. Either side can be `null`.

```json
{
  "symbol": "SPY",
  "params": ["implied_volatility", "delta", "fair_market_value"],
  "chain": [
    {
      "expiration": "2026-07-17",
      "strikes": [
        [640.0, [0.22, 0.71, 18.42], [0.24, -0.29, 5.11]]
      ]
    }
  ],
  "contract_count": 12488,
  "elapsed_ms": 41
}
```

Use the chain's `ticker` field (`O:SPY260116C00400000`) as the contract id for historical bars.

## Default fields

Used when `fields` / `params` is omitted:

`contract_type`, `expiration_date`, `strike_price`, `implied_volatility`, `open_interest`, `delta`, `gamma`, `theta`, `vega`, `day_volume`, `underlying_price`

## All 31 supported fields

### Identity

| Field | Type | Description |
|---|---|---|
| `underlying_ticker` | text | Underlying, e.g. `AAPL` or `I:SPX` |
| `ticker` | text | OCC-style contract, e.g. `O:SPY260116C00400000` |

### Contract terms

| Field | Type | Description |
|---|---|---|
| `contract_type` | text | `call` or `put`. Default. |
| `expiration_date` | text | `YYYY-MM-DD`. Default. |
| `strike_price` | number | Strike. Default. |
| `exercise_style` | text | `american` or `european` |
| `shares_per_contract` | number | Usually 100 |

### Pricing and valuation

| Field | Type | Description |
|---|---|---|
| `implied_volatility` | number | Decimal fraction (`0.25` = 25%). Default. |
| `open_interest` | number | Open contracts as of last close. Default. |
| `break_even_price` | number | Strike + premium (calls) or strike − premium (puts) |
| `fair_market_value` | number | Massive FMV estimate. Not a quote. |

### Greeks

| Field | Type | Description |
|---|---|---|
| `delta` | number | Default |
| `gamma` | number | Default |
| `theta` | number | Default |
| `vega` | number | Default |

### Session (day)

| Field | Type | Description |
|---|---|---|
| `day_open` | number | |
| `day_high` | number | |
| `day_low` | number | |
| `day_close` | number | Session close or latest |
| `day_previous_close` | number | |
| `day_change` | number | |
| `day_change_percent` | number | |
| `day_volume` | number | Contracts traded today. Default. |
| `day_vwap` | number | |
| `day_last_updated` | timestamp (ns) | Epoch nanoseconds |

### Underlying

| Field | Type | Description |
|---|---|---|
| `underlying_price` | number | Current underlying price. Default. |
| `underlying_symbol` | text | Snapshot's underlying symbol |
| `underlying_change_to_break_even` | number | |
| `underlying_last_updated` | timestamp (ns) | |
| `underlying_timeframe` | text | `REAL-TIME` or `DELAYED` |

### Metadata

| Field | Type | Description |
|---|---|---|
| `fetched_at` | timestamp | Ingest time |

## Errors

- `400` — unknown field, empty/too-long params, or invalid symbol
- `401` — missing or revoked key
- `429` — hourly limit
