# SQL

Official doc: [SQL](https://cvforge.convexvalue.com/docs/data/sql).

Read-only DuckDB against the live snapshot. Use this for `GROUP BY`, window functions, joins, and anything chain or screen cannot express.

## Call

MCP: `query_sql({ sql, max_rows? })`
REST: `POST /query` with `{ "sql": "..." }`
cvApi: `cvApi.query(sql, maxRows?)`

- One statement. Must start with `SELECT` or `WITH`. One trailing semicolon is allowed.
- `max_rows` defaults to 10,000 and is clamped to that. Response sets `truncated: true` if more rows matched.
- DDL, DML, `PRAGMA`, and multiple statements return `400`.
- The database swaps atomically about once a minute. These tables have no history.

Rows come back as objects keyed by column name.

## Tables

### `options_snapshots`

One row per live contract. Columns are the [supported snapshot fields](options-snapshot.md). Raw storage names are not a product promise.

Indexed by `underlying_ticker`, by `ticker`, and by `(underlying_ticker, expiration_date, strike_price, contract_type)`. Filter on those for speed.

### `option_symbols`

| Column | Type | Description |
|---|---|---|
| `ticker` | text | Stock/ETF symbol from the daily universe refresh |
| `has_options` | boolean | Only optionable symbols enter the snapshot |
| `updated_at` | timestamp | Last universe refresh |

## Official recipes

Put/call volume ratio, top names:

```sql
SELECT underlying_ticker,
       SUM(CASE WHEN contract_type = 'put'  THEN day_volume ELSE 0 END) /
       NULLIF(SUM(CASE WHEN contract_type = 'call' THEN day_volume ELSE 0 END), 0) AS pc_ratio,
       SUM(day_volume) AS total_volume
FROM options_snapshots
GROUP BY underlying_ticker
HAVING total_volume > 10000
ORDER BY total_volume DESC
LIMIT 25
```

ATM IV term structure (50-delta band):

```sql
SELECT expiration_date,
       AVG(implied_volatility) FILTER (WHERE ABS(delta) BETWEEN 0.45 AND 0.55) AS atm_iv
FROM options_snapshots
WHERE underlying_ticker = 'AAPL'
GROUP BY expiration_date
ORDER BY expiration_date
```

Net gamma by strike:

```sql
SELECT strike_price,
       SUM(gamma * open_interest * shares_per_contract *
           CASE WHEN contract_type = 'call' THEN 1 ELSE -1 END) AS net_gamma
FROM options_snapshots
WHERE underlying_ticker = 'SPY'
GROUP BY strike_price
ORDER BY strike_price
```

More formula notes: [analysis.md](analysis.md).
