# Options screener

Official doc: [screener](https://cvforge.convexvalue.com/docs/data/screener).

`/screen` queries every contract on every underlying. Columns, filters, and sorts use the same 31 fields as the [snapshot](options-snapshot.md). Option quotes are not available; use `fair_market_value` for a current valuation estimate.

## Call

MCP: `screen({ columns, filters, sort?, limit? })`
REST: `POST /screen`
cvApi: `cvApi.screen({ ... })`

`filters` is required (may be `[]`).

```json
{
  "columns": ["underlying_ticker", "ticker", "day_volume", "open_interest", "implied_volatility", "fair_market_value"],
  "filters": [
    { "field": "day_volume", "op": "gt_field", "field_ref": "open_interest" },
    { "field": "open_interest", "op": "gt", "value": 1000 }
  ],
  "sort": [{ "field": "day_volume", "direction": "desc" }],
  "limit": 100
}
```

## Request

| Parameter | Limit |
|---|---|
| `columns` | 1–32 supported fields. Duplicates dropped. cvApi fills a default set if omitted. |
| `filters` | Required. Up to 16 predicates, ANDed. Empty array matches all. |
| `sort` | Up to 4 of `{ field, direction: "asc"\|"desc" }`. Direction defaults to `asc`. |
| `limit` | Default 100, max 500. Response sets `truncated: true` when more rows matched. |

Need more than 500 rows or `GROUP BY`? Use [SQL](sql.md).

## Operators

Value operators take `value` (number or string) and must not include `field_ref`:

`eq` `ne` `gt` `gte` `lt` `lte`

Field operators take `field_ref` and must not include `value`:

`eq_field` `ne_field` `gt_field` `gte_field` `lt_field` `lte_field`

Anything else is `400`.

## Response

Rows are arrays in `columns` order:

```json
{
  "columns": ["underlying_ticker", "strike_price", "implied_volatility"],
  "rows": [["GME", 20.0, 2.41]],
  "row_count": 2,
  "truncated": false,
  "elapsed_ms": 87
}
```
