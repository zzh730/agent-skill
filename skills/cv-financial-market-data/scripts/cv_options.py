#!/usr/bin/env python3
"""CLI helpers for cvserver financial market data."""

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


DEFAULT_BASE_URL = "https://tap.convexvalue.com/api/data"

FIELDS = [
    "underlying_ticker",
    "ticker",
    "break_even_price",
    "implied_volatility",
    "open_interest",
    "fair_market_value",
    "day_change",
    "day_change_percent",
    "day_close",
    "day_high",
    "day_last_updated",
    "day_low",
    "day_open",
    "day_previous_close",
    "day_volume",
    "day_vwap",
    "contract_type",
    "exercise_style",
    "expiration_date",
    "shares_per_contract",
    "strike_price",
    "delta",
    "gamma",
    "theta",
    "vega",
    "ask",
    "ask_size",
    "bid",
    "bid_size",
    "quote_last_updated",
    "midpoint",
    "quote_timeframe",
    "trade_conditions",
    "trade_exchange",
    "trade_price",
    "trade_sip_timestamp",
    "trade_size",
    "trade_timeframe",
    "underlying_change_to_break_even",
    "underlying_last_updated",
    "underlying_price",
    "underlying_symbol",
    "underlying_timeframe",
    "fetched_at",
]

DEFAULT_FIELDS = [
    "expiration_date",
    "strike_price",
    "contract_type",
    "implied_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "bid",
    "ask",
    "midpoint",
    "open_interest",
    "day_volume",
    "underlying_price",
]

ANALYSIS_FIELDS = [
    "expiration_date",
    "strike_price",
    "contract_type",
    "implied_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "open_interest",
    "day_volume",
    "underlying_price",
    "shares_per_contract",
    "ticker",
    "fetched_at",
]

DOCTOR_COLUMNS = [
    "underlying_ticker",
    "ticker",
    "expiration_date",
    "strike_price",
    "contract_type",
]

API_HELP = """cvserver financial market data API wrapper examples

Generic data API call:
  cv-options call /chains --body '{"symbol":"SPY","params":["expiration_date","strike_price","delta"]}' --format json
  cv-options call /screen --body '{"columns":["ticker","open_interest"],"filters":[{"field":"underlying_ticker","op":"eq","value":"SPY"}],"limit":5}'
  cv-options call /query --body '{"sql":"SELECT underlying_ticker, COUNT(*) AS contracts FROM options_snapshots GROUP BY 1 LIMIT 10"}'
  cv-options call /fmp/stable/quote --body '{"symbol":"SPY"}'
  cv-options call /mas/aggs --body '{"ticker":"O:SPY260731P00550000","multiplier":1,"timespan":"day","from":"2026-07-01","to":"2026-07-03"}' --rows-key results

FMP stable endpoints:
  cv-options fmp quote --param symbol=SPY
  cv-options fmp historical-chart/5min --param symbol=SPY --param from=2026-07-02 --param to=2026-07-03
  cv-options fmp treasury-rates
  cv-options fmp earnings-calendar --param from=2026-07-05 --param to=2026-07-12
  cv-options fmp income-statement --param symbol=AAPL --param period=annual --param limit=5
  cv-options fmp etf/holdings --param symbol=SPY
  cv-options fmp news/stock-latest --param limit=20

Option contract history:
  cv-options option-bars O:SPY260731P00550000 --from 2026-07-01 --to 2026-07-03 --timespan day
  cv-options option-daily O:SPY260731P00550000 --date 2026-07-02

Wrapper conveniences:
  cv-options call /screen --body-file screen.json --format csv
  echo '{"symbol":"SPY"}' | cv-options fmp quote --body -
  cv-options fmp quote --param symbol=SPY --dry-run --format json

Configuration:
  Prefer a running cvforge preview proxy, or set CVSERVER_DATA_BASE / CV_OPTIONS_BASE / CVFORGE_DATA_BASE.
  For non-local endpoints, set CVSERVER_API_TOKEN / CV_API_TOKEN / CONVEXVALUE_API_TOKEN, or run from a repo with .mcp.json.
"""


def parse_csv(value):
    if value is None or value == "":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_symbol(symbol):
    symbol = symbol.strip()
    if symbol.upper().startswith("I:"):
        return "I:" + symbol.split(":", 1)[1].upper()
    return symbol.upper()


def to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def dte_years(expiration_date, as_of=None):
    today = parse_date(as_of) if as_of else date.today()
    days = (parse_date(expiration_date) - today).days
    return max(days, 0) / 365.0


def find_auth_header_from_json(path):
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    servers = data.get("mcpServers", {})
    cvserver = servers.get("cvserver", {})
    headers = cvserver.get("headers", {})
    auth = headers.get("Authorization")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        return auth
    return None


def find_auth_header_from_toml(path):
    try:
        text = path.read_text()
    except OSError:
        return None
    match = re.search(r'Authorization\s*=\s*"([^"]+)"', text)
    if match and match.group(1).lower().startswith("bearer "):
        return match.group(1)
    return None


def iter_parent_dirs(start):
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent
    while True:
        yield current
        if current.parent == current:
            break
        current = current.parent


def resolve_auth_header(search_start=None):
    token = (
        os.environ.get("CVSERVER_API_TOKEN")
        or os.environ.get("CV_API_TOKEN")
        or os.environ.get("CONVEXVALUE_API_TOKEN")
    )
    if token:
        return token if token.lower().startswith("bearer ") else "Bearer " + token

    start = search_start or os.getcwd()
    for folder in iter_parent_dirs(start):
        auth = find_auth_header_from_json(folder / ".mcp.json")
        if auth:
            return auth
        auth = find_auth_header_from_toml(folder / ".codex" / "config.toml")
        if auth:
            return auth
    return None


def discover_cvforge_proxy():
    try:
        output = subprocess.check_output(
            ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    for line in output.splitlines():
        if not line.lower().startswith("cvforge"):
            continue
        match = re.search(r"127\.0\.0\.1:(\d+)", line)
        if match:
            return f"http://127.0.0.1:{match.group(1)}/api/data"
    return None


def api_base_url():
    return (
        os.environ.get("CVSERVER_DATA_BASE")
        or os.environ.get("CV_OPTIONS_BASE")
        or os.environ.get("CVFORGE_DATA_BASE")
        or discover_cvforge_proxy()
        or DEFAULT_BASE_URL
    )


def base_needs_auth(base_url):
    lowered = (base_url or "").lower()
    return not (
        lowered.startswith("http://127.0.0.1:")
        or lowered.startswith("http://localhost:")
        or lowered.startswith("http://[::1]:")
    )


def post_json(path, body, base_url=None, auth_header=None):
    base = (base_url or api_base_url()).rstrip("/")
    endpoint = path if path.startswith("/") else "/" + path
    auth = auth_header or (resolve_auth_header() if base_needs_auth(base) else None)
    if base_needs_auth(base) and not auth:
        raise RuntimeError(
            "Missing cvserver auth. Set CVSERVER_API_TOKEN or run from a cvforge repo with .mcp.json."
        )
    headers = {"content-type": "application/json"}
    if auth:
        headers["authorization"] = auth
    req = urllib.request.Request(
        base + endpoint,
        data=json.dumps(body or {}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"cvserver {endpoint} failed with HTTP {exc.code}: {detail}") from exc


def call_endpoint(endpoint, body=None, base_url=None):
    return post_json(endpoint, body or {}, base_url=base_url)


def get_chain(symbol, fields=None):
    return post_json("/chains", {"symbol": normalize_symbol(symbol), "params": fields or DEFAULT_FIELDS})


def screen_contracts(columns, filters, sort=None, limit=None):
    body = {"columns": columns or DEFAULT_FIELDS, "filters": filters or []}
    if sort:
        body["sort"] = sort
    if limit is not None:
        body["limit"] = limit
    return post_json("/screen", body)


def query_sql(sql, max_rows=None):
    body = {"sql": sql}
    if max_rows is not None:
        body["max_rows"] = max_rows
    return post_json("/query", body)


def run_doctor(symbol="SPY", base_url=None, screen_func=None):
    symbol = normalize_symbol(symbol)
    base = (base_url or api_base_url()).rstrip("/")
    filters = [{"field": "underlying_ticker", "op": "eq", "value": symbol}]
    if screen_func:
        result = screen_func(DOCTOR_COLUMNS, filters, sort=None, limit=1)
    else:
        result = post_json(
            "/screen",
            {"columns": DOCTOR_COLUMNS, "filters": filters, "limit": 1},
            base_url=base,
        )
    rows = rows_from_screen(result)
    first = rows[0] if rows else {}
    return {
        "status": "ok" if rows else "empty",
        "symbol": symbol,
        "base_url": base,
        "auth_required": base_needs_auth(base),
        "row_count": result.get("row_count", len(rows)),
        "sample_ticker": first.get("ticker"),
        "sample_expiration": first.get("expiration_date"),
        "sample_strike": first.get("strike_price"),
        "sample_contract_type": first.get("contract_type"),
    }


def flatten_chain(chain_response):
    params = chain_response.get("params") or []
    symbol = chain_response.get("symbol")
    rows = []
    for expiration_group in chain_response.get("chain") or []:
        expiration = expiration_group.get("expiration")
        for strike_entry in expiration_group.get("strikes") or []:
            if not isinstance(strike_entry, list) or len(strike_entry) < 3:
                continue
            strike = strike_entry[0]
            for side_name, values in (("call", strike_entry[1]), ("put", strike_entry[2])):
                if not isinstance(values, list):
                    continue
                row = dict(zip(params, values))
                row.setdefault("symbol", symbol)
                row["symbol"] = symbol
                row["expiration_date"] = row.get("expiration_date") or expiration
                row["strike_price"] = to_float(row.get("strike_price"))
                if row["strike_price"] is None:
                    row["strike_price"] = to_float(strike)
                row["contract_type"] = (row.get("contract_type") or side_name).lower()
                rows.append(row)
    return rows


def filter_rows(rows, expiration=None, min_open_interest=None):
    filtered = []
    for row in rows:
        if expiration and row.get("expiration_date") != expiration:
            continue
        if min_open_interest is not None:
            oi = to_float(row.get("open_interest")) or 0.0
            if oi < min_open_interest:
                continue
        filtered.append(row)
    return filtered


def row_spot(row):
    return to_float(row.get("underlying_price"))


def row_shares(row):
    return to_float(row.get("shares_per_contract")) or 100.0


def contract_sign(row):
    return 1.0 if str(row.get("contract_type", "")).lower() == "call" else -1.0


def compute_gamma_levels(rows):
    grouped = {}
    for row in rows:
        strike = to_float(row.get("strike_price"))
        gamma = to_float(row.get("gamma"))
        oi = to_float(row.get("open_interest")) or 0.0
        spot = row_spot(row)
        if strike is None or gamma is None or spot is None:
            continue
        shares = row_shares(row)
        exposure = gamma * oi * shares * spot * spot * 0.01
        bucket = grouped.setdefault(
            strike,
            {
                "strike_price": strike,
                "net_gamma_exposure_1pct": 0.0,
                "call_gamma_exposure_1pct": 0.0,
                "put_gamma_exposure_1pct": 0.0,
                "total_abs_gamma_exposure_1pct": 0.0,
                "call_open_interest": 0.0,
                "put_open_interest": 0.0,
                "underlying_price": spot,
            },
        )
        bucket["total_abs_gamma_exposure_1pct"] += abs(exposure)
        if contract_sign(row) > 0:
            bucket["call_gamma_exposure_1pct"] += exposure
            bucket["call_open_interest"] += oi
            bucket["net_gamma_exposure_1pct"] += exposure
        else:
            bucket["put_gamma_exposure_1pct"] -= exposure
            bucket["put_open_interest"] += oi
            bucket["net_gamma_exposure_1pct"] -= exposure
    return sorted(grouped.values(), key=lambda item: item["strike_price"])


def nearest_atm_rows(rows):
    by_expiration = defaultdict(list)
    for row in rows:
        if row.get("expiration_date"):
            by_expiration[row.get("expiration_date")].append(row)

    selected = {}
    for expiration, items in by_expiration.items():
        with_spot = [row for row in items if row_spot(row) is not None and to_float(row.get("strike_price")) is not None]
        if with_spot:
            spot = row_spot(with_spot[0])
            strike = min(
                {to_float(row.get("strike_price")) for row in with_spot},
                key=lambda value: abs(value - spot),
            )
            selected[expiration] = [row for row in with_spot if to_float(row.get("strike_price")) == strike]
            continue
        with_delta = [row for row in items if to_float(row.get("delta")) is not None]
        if with_delta:
            chosen = min(with_delta, key=lambda row: abs(abs(to_float(row.get("delta"))) - 0.5))
            strike = to_float(chosen.get("strike_price"))
            selected[expiration] = [row for row in with_delta if to_float(row.get("strike_price")) == strike]
    return selected


def compute_vol_structure(rows, as_of=None):
    structure = []
    for expiration, items in nearest_atm_rows(rows).items():
        ivs = [to_float(row.get("implied_volatility")) for row in items]
        ivs = [iv for iv in ivs if iv is not None]
        strikes = [to_float(row.get("strike_price")) for row in items if to_float(row.get("strike_price")) is not None]
        if not ivs or not strikes:
            continue
        calls = [to_float(row.get("implied_volatility")) for row in items if row.get("contract_type") == "call"]
        puts = [to_float(row.get("implied_volatility")) for row in items if row.get("contract_type") == "put"]
        calls = [iv for iv in calls if iv is not None]
        puts = [iv for iv in puts if iv is not None]
        structure.append(
            {
                "expiration_date": expiration,
                "dte": round(dte_years(expiration, as_of) * 365),
                "atm_strike": strikes[0],
                "atm_iv": sum(ivs) / len(ivs),
                "call_iv": sum(calls) / len(calls) if calls else None,
                "put_iv": sum(puts) / len(puts) if puts else None,
                "underlying_price": next((row_spot(row) for row in items if row_spot(row) is not None), None),
            }
        )
    return sorted(structure, key=lambda item: item["expiration_date"])


def norm_cdf(value):
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def norm_pdf(value):
    return math.exp(-0.5 * value * value) / math.sqrt(2.0 * math.pi)


def bs_d1(spot, strike, years, volatility, rate, dividend_yield):
    if spot <= 0 or strike <= 0 or years <= 0 or volatility <= 0:
        return None
    numerator = math.log(spot / strike) + (rate - dividend_yield + 0.5 * volatility * volatility) * years
    return numerator / (volatility * math.sqrt(years))


def bs_delta(contract_type, spot, strike, years, volatility, rate=0.045, dividend_yield=0.0):
    d1 = bs_d1(spot, strike, years, volatility, rate, dividend_yield)
    if d1 is None:
        return None
    discount = math.exp(-dividend_yield * years)
    if contract_type == "call":
        return discount * norm_cdf(d1)
    return discount * (norm_cdf(d1) - 1.0)


def bs_vanna(contract_type, spot, strike, years, volatility, rate=0.045, dividend_yield=0.0):
    d1 = bs_d1(spot, strike, years, volatility, rate, dividend_yield)
    if d1 is None:
        return None
    d2 = d1 - volatility * math.sqrt(years)
    return -math.exp(-dividend_yield * years) * norm_pdf(d1) * d2 / volatility


def bs_delta_decay_one_day(contract_type, spot, strike, years, volatility, rate=0.045, dividend_yield=0.0):
    today_delta = bs_delta(contract_type, spot, strike, years, volatility, rate, dividend_yield)
    if today_delta is None:
        return None
    tomorrow_years = max(years - (1.0 / 365.0), 1.0 / (365.0 * 24.0))
    tomorrow_delta = bs_delta(contract_type, spot, strike, tomorrow_years, volatility, rate, dividend_yield)
    if tomorrow_delta is None:
        return None
    return tomorrow_delta - today_delta


def compute_vanna_exposure(rows, as_of=None, rate=0.045, dividend_yield=0.0):
    grouped = {}
    for row in rows:
        spot = row_spot(row)
        strike = to_float(row.get("strike_price"))
        volatility = to_float(row.get("implied_volatility"))
        expiration = row.get("expiration_date")
        oi = to_float(row.get("open_interest")) or 0.0
        if spot is None or strike is None or volatility is None or not expiration:
            continue
        years = max(dte_years(expiration, as_of), 1.0 / (365.0 * 24.0))
        vanna = bs_vanna(row.get("contract_type"), spot, strike, years, volatility, rate, dividend_yield)
        if vanna is None:
            continue
        exposure = vanna * oi * row_shares(row) * contract_sign(row)
        bucket = grouped.setdefault(
            strike,
            {
                "strike_price": strike,
                "net_vanna_exposure": 0.0,
                "call_vanna_exposure": 0.0,
                "put_vanna_exposure": 0.0,
                "call_open_interest": 0.0,
                "put_open_interest": 0.0,
                "underlying_price": spot,
            },
        )
        bucket["net_vanna_exposure"] += exposure
        if contract_sign(row) > 0:
            bucket["call_vanna_exposure"] += exposure
            bucket["call_open_interest"] += oi
        else:
            bucket["put_vanna_exposure"] += exposure
            bucket["put_open_interest"] += oi
    return sorted(grouped.values(), key=lambda item: item["strike_price"])


def compute_charm_exposure(rows, as_of=None, rate=0.045, dividend_yield=0.0):
    grouped = {}
    for row in rows:
        spot = row_spot(row)
        strike = to_float(row.get("strike_price"))
        volatility = to_float(row.get("implied_volatility"))
        expiration = row.get("expiration_date")
        oi = to_float(row.get("open_interest")) or 0.0
        if spot is None or strike is None or volatility is None or not expiration:
            continue
        years = max(dte_years(expiration, as_of), 1.0 / (365.0 * 24.0))
        decay = bs_delta_decay_one_day(row.get("contract_type"), spot, strike, years, volatility, rate, dividend_yield)
        if decay is None:
            continue
        exposure = decay * oi * row_shares(row) * contract_sign(row)
        bucket = grouped.setdefault(
            strike,
            {
                "strike_price": strike,
                "net_charm_exposure": 0.0,
                "call_charm_exposure": 0.0,
                "put_charm_exposure": 0.0,
                "call_open_interest": 0.0,
                "put_open_interest": 0.0,
                "underlying_price": spot,
            },
        )
        bucket["net_charm_exposure"] += exposure
        if contract_sign(row) > 0:
            bucket["call_charm_exposure"] += exposure
            bucket["call_open_interest"] += oi
        else:
            bucket["put_charm_exposure"] += exposure
            bucket["put_open_interest"] += oi
    return sorted(grouped.values(), key=lambda item: item["strike_price"])


def rows_from_screen(result):
    columns = result.get("columns") or []
    return [dict(zip(columns, row)) for row in result.get("rows") or []]


def ordered_columns(rows):
    columns = []
    seen = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)
    return columns


def rows_from_any_result(result, rows_key=None):
    if rows_key:
        if not isinstance(result, dict):
            raise RuntimeError("--rows-key can only be used when the API response is an object")
        rows = result.get(rows_key) or []
        return normalize_result_rows(rows), None

    if isinstance(result, list):
        return normalize_result_rows(result), None

    if isinstance(result, dict):
        if isinstance(result.get("columns"), list) and isinstance(result.get("rows"), list):
            return rows_from_screen(result), result.get("columns")
        for key in ("rows", "results", "data"):
            if isinstance(result.get(key), list):
                return normalize_result_rows(result.get(key)), None
        return [result], list(result.keys())

    return [{"value": result}], ["value"]


def normalize_result_rows(rows):
    rows = rows or []
    if all(isinstance(row, dict) for row in rows):
        return rows
    return [{"value": row} for row in rows]


def format_value(value):
    if value is None:
        return ""
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.2f}"
        return f"{value:.6g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def output_rows(rows, fmt="table", columns=None):
    rows = rows or []
    columns = columns or (list(rows[0].keys()) if rows else [])
    if fmt == "json":
        print(json.dumps(rows, indent=2, sort_keys=True))
        return
    if fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return
    if not rows:
        print("(no rows)")
        return
    widths = {}
    for column in columns:
        values = [format_value(row.get(column)) for row in rows]
        widths[column] = max(len(column), *(len(value) for value in values))
    header = "  ".join(column.ljust(widths[column]) for column in columns)
    print(header)
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print("  ".join(format_value(row.get(column)).ljust(widths[column]) for column in columns))


def limit_rows(rows, limit, key=None):
    if key:
        rows = sorted(rows, key=lambda row: abs(to_float(row.get(key)) or 0.0), reverse=True)
    if limit is None:
        return rows
    return rows[:limit]


def build_screen_filters(args):
    filters = []
    if args.symbol:
        filters.append({"field": "underlying_ticker", "op": "eq", "value": normalize_symbol(args.symbol)})
    if args.min_oi is not None:
        filters.append({"field": "open_interest", "op": "gte", "value": args.min_oi})
    if args.min_volume is not None:
        filters.append({"field": "day_volume", "op": "gte", "value": args.min_volume})
    if args.min_iv is not None:
        filters.append({"field": "implied_volatility", "op": "gte", "value": args.min_iv})
    if args.max_iv is not None:
        filters.append({"field": "implied_volatility", "op": "lte", "value": args.max_iv})
    if args.expiration:
        filters.append({"field": "expiration_date", "op": "eq", "value": args.expiration})
    if args.contract_type:
        filters.append({"field": "contract_type", "op": "eq", "value": args.contract_type})
    return filters


def add_common_output_args(parser):
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table")


def add_model_args(parser):
    parser.add_argument("--rate", type=float, default=0.045)
    parser.add_argument("--dividend-yield", type=float, default=0.0)
    parser.add_argument("--as-of", default=None)


def parse_json_object(text, label):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return data


def parse_param_value(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def read_json_arg(value, label):
    if value is None:
        return {}
    if value == "-":
        return parse_json_object(sys.stdin.read(), label)
    return parse_json_object(value, label)


def read_json_file(path, label):
    if path is None:
        return {}
    if path == "-":
        return parse_json_object(sys.stdin.read(), label)
    try:
        text = Path(path).read_text()
    except OSError as exc:
        raise RuntimeError(f"could not read {label} {path}: {exc}") from exc
    return parse_json_object(text, label)


def build_body(body_text=None, body_file=None, params=None):
    if body_text and body_file:
        raise RuntimeError("use either --body or --body-file, not both")
    body = {}
    if body_text:
        body.update(read_json_arg(body_text, "--body"))
    if body_file:
        body.update(read_json_file(body_file, "--body-file"))
    for item in params or []:
        key, sep, raw = item.partition("=")
        key = key.strip()
        if not sep or not key:
            raise RuntimeError(f"--param must look like key=value, got {item!r}")
        body[key] = parse_param_value(raw.strip())
    return body


def output_api_result(result, fmt="table", rows_key=None):
    if fmt == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    rows, columns = rows_from_any_result(result, rows_key=rows_key)
    output_rows(rows, fmt, columns or ordered_columns(rows))


def maybe_print_dry_run(endpoint, body, args):
    if not getattr(args, "dry_run", False):
        return False
    base = (args.base_url or api_base_url()).rstrip("/")
    result = {
        "endpoint": endpoint if endpoint.startswith("/") else "/" + endpoint,
        "base_url": base,
        "auth_required": base_needs_auth(base),
        "body": body,
    }
    output_api_result(result, args.format)
    return True


def command_fields(args):
    rows = [{"field": field, "default": field in DEFAULT_FIELDS} for field in FIELDS]
    output_rows(rows, args.format, ["field", "default"])


def command_doctor(args):
    result = run_doctor(args.symbol, args.base_url)
    columns = [
        "status",
        "symbol",
        "base_url",
        "auth_required",
        "row_count",
        "sample_ticker",
        "sample_expiration",
        "sample_strike",
        "sample_contract_type",
    ]
    output_rows([result], args.format, columns)
    if result["status"] != "ok":
        raise RuntimeError(f"doctor found no sample contracts for {result['symbol']}")


def command_chain(args):
    fields = parse_csv(args.fields) or DEFAULT_FIELDS
    result = get_chain(args.symbol, fields)
    rows = flatten_chain(result)
    rows = filter_rows(rows, args.expiration, args.min_oi)
    rows = rows[: args.limit] if args.limit is not None else rows
    output_rows(rows, args.format)


def command_screen(args):
    columns = parse_csv(args.columns) or [
        "underlying_ticker",
        "ticker",
        "expiration_date",
        "strike_price",
        "contract_type",
        "implied_volatility",
        "delta",
        "gamma",
        "open_interest",
        "day_volume",
        "underlying_price",
    ]
    sort = [{"field": args.sort, "direction": args.direction}] if args.sort else None
    result = screen_contracts(columns, build_screen_filters(args), sort=sort, limit=args.limit)
    output_rows(rows_from_screen(result), args.format, columns)


def command_query(args):
    result = query_sql(args.sql, args.max_rows)
    rows = result.get("rows") or []
    output_rows(rows, args.format)


def command_call(args):
    body = build_body(args.body, args.body_file, args.param)
    if maybe_print_dry_run(args.endpoint, body, args):
        return
    result = call_endpoint(args.endpoint, body, base_url=args.base_url)
    output_api_result(result, args.format, rows_key=args.rows_key)


def command_fmp(args):
    body = build_body(args.params_json, args.params_file, args.param)
    endpoint = "/fmp/stable/" + args.endpoint.strip("/")
    if maybe_print_dry_run(endpoint, body, args):
        return
    result = call_endpoint(endpoint, body, base_url=args.base_url)
    output_api_result(result, args.format, rows_key=args.rows_key)


def command_option_bars(args):
    body = {
        "ticker": args.ticker,
        "multiplier": args.multiplier,
        "timespan": args.timespan,
        "from": args.from_date,
        "to": args.to_date,
    }
    if args.unadjusted:
        body["adjusted"] = False
    if args.sort:
        body["sort"] = args.sort
    if args.limit is not None:
        body["limit"] = args.limit
    if maybe_print_dry_run("/mas/aggs", body, args):
        return
    result = call_endpoint("/mas/aggs", body, base_url=args.base_url)
    output_api_result(result, args.format, rows_key="results")


def command_option_daily(args):
    body = {"ticker": args.ticker, "date": args.date}
    if args.unadjusted:
        body["adjusted"] = False
    if maybe_print_dry_run("/mas/open-close", body, args):
        return
    result = call_endpoint("/mas/open-close", body, base_url=args.base_url)
    output_api_result(result, args.format)


def command_api_help(_args):
    print(API_HELP.rstrip())


def load_analysis_rows(symbol, expiration=None, min_oi=None):
    result = get_chain(symbol, ANALYSIS_FIELDS)
    rows = flatten_chain(result)
    return filter_rows(rows, expiration=expiration, min_open_interest=min_oi)


def command_gamma_levels(args):
    rows = load_analysis_rows(args.symbol, args.expiration, args.min_oi)
    levels = compute_gamma_levels(rows)
    levels = limit_rows(levels, args.top, "net_gamma_exposure_1pct")
    output_rows(
        levels,
        args.format,
        [
            "strike_price",
            "net_gamma_exposure_1pct",
            "call_gamma_exposure_1pct",
            "put_gamma_exposure_1pct",
            "total_abs_gamma_exposure_1pct",
            "call_open_interest",
            "put_open_interest",
            "underlying_price",
        ],
    )


def command_vol_structure(args):
    rows = load_analysis_rows(args.symbol, args.expiration, args.min_oi)
    structure = compute_vol_structure(rows, as_of=args.as_of)
    output_rows(
        structure,
        args.format,
        ["expiration_date", "dte", "atm_strike", "atm_iv", "call_iv", "put_iv", "underlying_price"],
    )


def command_vanna_exposure(args):
    rows = load_analysis_rows(args.symbol, args.expiration, args.min_oi)
    exposure = compute_vanna_exposure(rows, as_of=args.as_of, rate=args.rate, dividend_yield=args.dividend_yield)
    exposure = limit_rows(exposure, args.top, "net_vanna_exposure")
    output_rows(
        exposure,
        args.format,
        [
            "strike_price",
            "net_vanna_exposure",
            "call_vanna_exposure",
            "put_vanna_exposure",
            "call_open_interest",
            "put_open_interest",
            "underlying_price",
        ],
    )


def command_charm_exposure(args):
    rows = load_analysis_rows(args.symbol, args.expiration, args.min_oi)
    exposure = compute_charm_exposure(rows, as_of=args.as_of, rate=args.rate, dividend_yield=args.dividend_yield)
    exposure = limit_rows(exposure, args.top, "net_charm_exposure")
    output_rows(
        exposure,
        args.format,
        [
            "strike_price",
            "net_charm_exposure",
            "call_charm_exposure",
            "put_charm_exposure",
            "call_open_interest",
            "put_open_interest",
            "underlying_price",
        ],
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cv-options",
        description="Query and analyze cvserver stock, options, and financial market data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run 'cv-options api-help' for raw API wrapper examples.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fields = subparsers.add_parser("fields", help="List supported fields.")
    add_common_output_args(fields)
    fields.set_defaults(func=command_fields)

    doctor = subparsers.add_parser("doctor", help="Verify that the cvserver data path works.")
    doctor.add_argument("--symbol", default="SPY")
    doctor.add_argument("--base-url")
    add_common_output_args(doctor)
    doctor.set_defaults(func=command_doctor)

    chain = subparsers.add_parser("chain", help="Fetch and flatten an option chain.")
    chain.add_argument("symbol")
    chain.add_argument("--fields", default="")
    chain.add_argument("--expiration")
    chain.add_argument("--min-oi", type=float)
    chain.add_argument("--limit", type=int, default=25)
    add_common_output_args(chain)
    chain.set_defaults(func=command_chain)

    screen = subparsers.add_parser("screen", help="Screen option contracts.")
    screen.add_argument("--symbol")
    screen.add_argument("--columns", default="")
    screen.add_argument("--min-oi", type=float)
    screen.add_argument("--min-volume", type=float)
    screen.add_argument("--min-iv", type=float)
    screen.add_argument("--max-iv", type=float)
    screen.add_argument("--expiration")
    screen.add_argument("--contract-type", choices=["call", "put"])
    screen.add_argument("--sort", default="day_volume")
    screen.add_argument("--direction", choices=["asc", "desc"], default="desc")
    screen.add_argument("--limit", type=int, default=25)
    add_common_output_args(screen)
    screen.set_defaults(func=command_screen)

    query = subparsers.add_parser("query", help="Run a read-only SELECT/WITH SQL query.")
    query.add_argument("sql")
    query.add_argument("--max-rows", type=int)
    add_common_output_args(query)
    query.set_defaults(func=command_query)

    call = subparsers.add_parser(
        "call",
        help="POST any /api/data endpoint with a JSON body.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  cv-options call /chains --body '{"symbol":"SPY","params":["delta","gamma"]}'
  cv-options call /screen --body-file screen.json --format csv
  echo '{"sql":"SELECT COUNT(*) AS n FROM options_snapshots"}' | cv-options call /query --body - --format json
""",
    )
    call.add_argument("endpoint", help='Endpoint path, e.g. "/chains", "/screen", "/query", "/fmp/stable/quote".')
    call.add_argument("--body", help='JSON request body. Use "-" to read JSON from stdin.')
    call.add_argument("--body-file", help='File containing a JSON request body. Use "-" to read JSON from stdin.')
    call.add_argument("--param", action="append", default=[], help="Merge one key=value into the JSON body. Value may be JSON.")
    call.add_argument("--rows-key", help="For table/csv output, render a list nested under this response key.")
    call.add_argument("--base-url", help="Override data API base URL, e.g. http://127.0.0.1:53903/api/data.")
    call.add_argument("--dry-run", action="store_true", help="Print the endpoint/body/base URL without sending the request.")
    add_common_output_args(call)
    call.set_defaults(func=command_call)

    fmp = subparsers.add_parser(
        "fmp",
        help="Call an FMP /stable endpoint through the cvserver proxy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  cv-options fmp quote --param symbol=SPY
  cv-options fmp historical-chart/5min --param symbol=SPY --param from=2026-07-02 --param to=2026-07-03
  cv-options fmp treasury-rates --format json
""",
    )
    fmp.add_argument("endpoint", help='FMP stable endpoint, e.g. "quote", "historical-chart/5min", "treasury-rates".')
    fmp.add_argument("--params-json", "--body", dest="params_json", help='JSON params object. Use "-" to read JSON from stdin.')
    fmp.add_argument("--params-file", "--body-file", dest="params_file", help='File containing JSON params. Use "-" for stdin.')
    fmp.add_argument("--param", action="append", default=[], help="Merge one key=value into the params. Value may be JSON.")
    fmp.add_argument("--rows-key", help="For table/csv output, render a list nested under this response key.")
    fmp.add_argument("--base-url", help="Override data API base URL.")
    fmp.add_argument("--dry-run", action="store_true", help="Print the endpoint/body/base URL without sending the request.")
    add_common_output_args(fmp)
    fmp.set_defaults(func=command_fmp)

    option_bars = subparsers.add_parser("option-bars", help="Fetch historical OHLCV bars for one option contract.")
    option_bars.add_argument("ticker", help='Option ticker, e.g. "O:SPY260731P00550000".')
    option_bars.add_argument("--from", dest="from_date", required=True, help="Window start: YYYY-MM-DD or epoch milliseconds.")
    option_bars.add_argument("--to", dest="to_date", required=True, help="Window end: YYYY-MM-DD or epoch milliseconds.")
    option_bars.add_argument("--multiplier", type=int, default=1)
    option_bars.add_argument(
        "--timespan",
        choices=["second", "minute", "hour", "day", "week", "month", "quarter", "year"],
        default="day",
    )
    option_bars.add_argument("--sort", choices=["asc", "desc"], default="asc")
    option_bars.add_argument("--limit", type=int)
    option_bars.add_argument("--unadjusted", action="store_true", help="Request unadjusted bars.")
    option_bars.add_argument("--base-url", help="Override data API base URL.")
    option_bars.add_argument("--dry-run", action="store_true", help="Print the endpoint/body/base URL without sending the request.")
    add_common_output_args(option_bars)
    option_bars.set_defaults(func=command_option_bars)

    option_daily = subparsers.add_parser("option-daily", help="Fetch one date of OHLCV data for one option contract.")
    option_daily.add_argument("ticker", help='Option ticker, e.g. "O:SPY260731P00550000".')
    option_daily.add_argument("--date", required=True, help="Trading date: YYYY-MM-DD.")
    option_daily.add_argument("--unadjusted", action="store_true", help="Request unadjusted data.")
    option_daily.add_argument("--base-url", help="Override data API base URL.")
    option_daily.add_argument("--dry-run", action="store_true", help="Print the endpoint/body/base URL without sending the request.")
    add_common_output_args(option_daily)
    option_daily.set_defaults(func=command_option_daily)

    api_help = subparsers.add_parser("api-help", help="Show raw API wrapper examples.")
    api_help.set_defaults(func=command_api_help)

    gamma = subparsers.add_parser("gamma-levels", help="Compute signed gamma levels by strike.")
    gamma.add_argument("symbol")
    gamma.add_argument("--expiration")
    gamma.add_argument("--min-oi", type=float)
    gamma.add_argument("--top", type=int, default=20)
    add_common_output_args(gamma)
    gamma.set_defaults(func=command_gamma_levels)

    vol = subparsers.add_parser("vol-structure", help="Compute ATM IV term structure.")
    vol.add_argument("symbol")
    vol.add_argument("--expiration")
    vol.add_argument("--min-oi", type=float)
    add_model_args(vol)
    add_common_output_args(vol)
    vol.set_defaults(func=command_vol_structure)

    vanna = subparsers.add_parser("vanna-exposure", help="Compute Black-Scholes vanna exposure by strike.")
    vanna.add_argument("symbol")
    vanna.add_argument("--expiration")
    vanna.add_argument("--min-oi", type=float)
    vanna.add_argument("--top", type=int, default=20)
    add_model_args(vanna)
    add_common_output_args(vanna)
    vanna.set_defaults(func=command_vanna_exposure)

    charm = subparsers.add_parser("charm-exposure", help="Compute one-day delta-decay exposure by strike.")
    charm.add_argument("symbol")
    charm.add_argument("--expiration")
    charm.add_argument("--min-oi", type=float)
    charm.add_argument("--top", type=int, default=20)
    add_model_args(charm)
    add_common_output_args(charm)
    charm.set_defaults(func=command_charm_exposure)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except BrokenPipeError:
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
