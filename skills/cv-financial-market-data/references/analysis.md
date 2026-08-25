# Derived analysis

Use SQL on `options_snapshots` for official aggregates. Vanna and charm are local model estimates, not cvforge fields and not dealer positioning.

## Official net gamma (GEX)

From the [SQL reference](https://cvforge.convexvalue.com/docs/data/sql):

```text
net_gamma = SUM(
  gamma * open_interest * shares_per_contract
  * (1 if call else -1)
)
GROUP BY strike_price
```

Calls are positive. Puts are negative. This is an open-interest proxy, not dollar gamma and not dealer inventory.

The CLI `gamma-levels` command runs this query.

## Official ATM IV term structure

```text
AVG(implied_volatility) FILTER (WHERE ABS(delta) BETWEEN 0.45 AND 0.55)
GROUP BY expiration_date
```

The CLI `vol-structure` command runs this query.

## Put/call volume ratio

```text
put_volume / NULLIF(call_volume, 0)
```

See [sql.md](sql.md) for the full statement.

## Local vanna and charm

These are **not** snapshot fields. The CLI computes them from chain IV, spot, strike, and tenor.

Black-Scholes vanna:

```text
vanna = -exp(-qT) * N'(d1) * d2 / volatility
exposure = vanna * open_interest * shares_per_contract * sign(call=+1, put=-1)
```

Charm proxy (one calendar day of delta decay):

```text
charm = delta(T - 1/365) - delta(T)
exposure = charm * open_interest * shares_per_contract * sign
```

Skip a row when `underlying_price`, strike, IV, or expiration is missing. Label output as a model estimate.

## Missing values

Tolerate missing `fair_market_value`, `day_volume`, Greeks, and `underlying_price`. Do not invent quotes to fill them.
