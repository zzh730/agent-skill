# Access, errors, and plans

Official docs: [REST](https://cvforge.convexvalue.com/docs/api/), [MCP](https://cvforge.convexvalue.com/docs/api/mcp), [cvApi](https://cvforge.convexvalue.com/docs/api/cvapi), [plans](https://cvforge.convexvalue.com/docs/plans).

## Surfaces

| Surface | When | How |
|---|---|---|
| MCP | Agent session with `cvserver` tools | Streamable HTTP JSON-RPC at `https://tap.convexvalue.com/api/data/mcp` |
| REST | Shell, notebooks, CLI | `POST` JSON to `https://tap.convexvalue.com/api/data/<path>` |
| `cvApi` | Page built inside cvforge | `cvApi.chain`, `cvApi.screen`, `cvApi.query`, `cvApi.call` |

`chain` / `screen` / `query` are sugar over `cvApi.call`. New backend paths are reachable with `call` the day they ship.

Override the REST base with `CVSERVER_DATA_BASE` (or `CV_API_TOKEN` family for auth). Do not scrape a local preview port unless the user set that base URL.

## MCP tools

| Tool | REST twin | Notes |
|---|---|---|
| `get_chain` | `POST /chains` | `{ symbol, fields? }` |
| `screen` | `POST /screen` | `{ columns?, filters, sort?, limit? }` |
| `query_sql` | `POST /query` | `{ sql, max_rows? }` |
| `get_option_bars` | `POST /mas/aggs` | Research plan |
| `get_option_daily` | `POST /mas/open-close` | Research plan |
| `fmp_request` | `POST /fmp/stable/<endpoint>` | `{ endpoint, params? }` |
| `list_fmp_endpoints` | — | Design-time. No data quota. |
| `list_chain_fields` | — | Design-time. Not the product contract. |

Trust live `tools/list` over this table if they differ.

## REST endpoints

| Method | Path | Access |
|---|---|---|
| POST | `/chains` | all plans |
| GET | `/chains/{symbol}?params=a,b,c` | all plans |
| POST | `/screen` | all plans |
| POST | `/query` | all plans |
| GET/POST | `/mas/v2/aggs/...` and `/mas/aggs` | Research |
| GET/POST | `/mas/v1/open-close/...` and `/mas/open-close` | Research |
| GET/POST | `/fmp/stable/{endpoint}` | all plans |
| POST | `/mcp` | all plans |

`/ai/*` routes are prepaid AI credits, not this skill.

## Auth

Bearer token `cv_live_…`. Personal keys are a Go and Research feature. Usage is per user, not per key.

At authorization time, the CLI first reads `CVSERVER_API_TOKEN` from the current terminal/process environment and sends `Authorization: Bearer <CVSERVER_API_TOKEN>`. Do not ask the user to paste the value. If it is unset, the CLI reads the legacy fallbacks in order: `CV_API_TOKEN`, `CONVEXVALUE_API_TOKEN`, then `.mcp.json` / `.codex/config.toml` walking up from the working directory.

Never print, commit, or copy the token.

## Errors

| Status | Meaning |
|---|---|
| 400 | Bad field, SQL, or body |
| 401 | Missing or revoked key |
| 402 | Plan lacks the feature, or AI credits empty |
| 404 | Unknown contract or date on `/mas/*` |
| 429 | Hourly limit reached. Resets on the hour. |
| 502 | Upstream provider error |
| 503 | Snapshot or source unavailable |

Feature gates run before the limiter. A `402` does not consume quota.

## Plans

| | Free | Go | Research |
|---|---|---|---|
| Requests / hour | 20 | 1,000 | 50,000 |
| Snapshot, screen, SQL, MCP, 157 FMP | yes | yes | yes |
| Personal API key | no | yes | yes |
| Historical option bars | no | no | yes |

One request can return a full chain, 500 screen rows, or 10,000 SQL rows.
