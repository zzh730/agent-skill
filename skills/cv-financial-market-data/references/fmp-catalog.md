# FMP catalog

Official index: [FMP reference](https://cvforge.convexvalue.com/docs/data/fmp). 157 allowlisted `/stable` endpoints. Every plan. Responses pass through from FMP unmodified.

Call:

- MCP: `fmp_request({ "endpoint": "profile", "params": { "symbol": "AAPL" } })`
- REST: `GET/POST /fmp/stable/profile`
- cvApi: `cvApi.call('/fmp/stable/profile', { symbol: 'AAPL' })`
- CLI: `python3 scripts/cv_data.py fmp profile --param symbol=AAPL`

If a path is not in this file, call `list_fmp_endpoints` before guessing. The allowlist excludes FMP bulk downloads and TipRanks partner routes.

Not in the allowlist: `grades`, `price-target-consensus`, `ratings-snapshot`, `dividends-calendar`, `splits-calendar`, `ipos-calendar`, `biggest-gainers`, `most-actives`, `sector-performance-snapshot`, commodities, forex prices, crypto prices, COT, ESG, fundraising.

Required params are marked. Others are optional.

## Search (7)

| Endpoint | Required | Use |
|---|---|---|
| `company-screener` | — | Fundamental screen (`marketCapMoreThan`, `sector`, `exchange`, …) |
| `search-symbol` | `query` | Ticker search |
| `search-name` | `query` | Name search |
| `search-cik` | `cik` | CIK → symbol |
| `search-cusip` | `cusip` | CUSIP → symbol |
| `search-isin` | `isin` | ISIN → symbol |
| `search-exchange-variants` | `symbol` | Same name on other exchanges |

## Directory (11)

| Endpoint | Required | Use |
|---|---|---|
| `stock-list` | — | All symbols |
| `etf-list` | — | ETF symbols |
| `actively-trading-list` | — | Actively traded |
| `financial-statement-symbol-list` | — | Names with statements |
| `earnings-transcript-list` | — | Names with transcripts |
| `available-exchanges` | — | Exchange list |
| `available-sectors` | — | Sector list |
| `available-industries` | — | Industry list |
| `available-countries` | — | Country list |
| `cik-list` | — | CIK directory |
| `symbol-change` | — | Ticker changes |

## Chart (10)

Equity/index history. Not option-contract history.

| Endpoint | Required | Use |
|---|---|---|
| `historical-chart/1min` | `symbol` | Intraday. Also `5min`, `15min`, `30min`, `1hour`, `4hour` |
| `historical-price-eod/light` | `symbol` | Date, price, volume |
| `historical-price-eod/full` | `symbol` | OHLC, change, VWAP |
| `historical-price-eod/dividend-adjusted` | `symbol` | Dividend-adjusted EOD |
| `historical-price-eod/non-split-adjusted` | `symbol` | Unadjusted for splits |

Optional on charts: `from`, `to`, `nonadjusted`.

## Statements (27)

Typical extras: `limit`, `period` = `annual` or `quarter` (some also accept `Q1`–`Q4`, `FY`).

| Endpoint | Required | Use |
|---|---|---|
| `income-statement` | `symbol` | Income |
| `income-statement-as-reported` | `symbol` | Filing-native income |
| `income-statement-growth` | `symbol` | Income growth |
| `income-statement-ttm` | `symbol` | TTM income |
| `balance-sheet-statement` | `symbol` | Balance |
| `balance-sheet-statement-as-reported` | `symbol` | Filing-native balance |
| `balance-sheet-statement-growth` | `symbol` | Balance growth |
| `balance-sheet-statement-ttm` | `symbol` | TTM balance |
| `cash-flow-statement` | `symbol` | Cash flow |
| `cash-flow-statement-as-reported` | `symbol` | Filing-native cash flow |
| `cash-flow-statement-growth` | `symbol` | Cash-flow growth |
| `cash-flow-statement-ttm` | `symbol` | TTM cash flow |
| `ratios` | `symbol` | Profitability, liquidity, leverage |
| `ratios-ttm` | `symbol` | TTM ratios |
| `key-metrics` | `symbol` | EV, yield, ROIC, … |
| `key-metrics-ttm` | `symbol` | TTM metrics |
| `enterprise-values` | `symbol` | EV build |
| `financial-growth` | `symbol` | Cross-statement growth |
| `financial-scores` | `symbol` | Altman Z, Piotroski |
| `owner-earnings` | `symbol` | Owner earnings |
| `revenue-geographic-segmentation` | `symbol` | Geo revenue |
| `revenue-product-segmentation` | `symbol` | Product revenue |
| `financial-reports-dates` | `symbol` | 10-K/10-Q date index |
| `financial-reports-json` | `symbol`, `year`, `period` | Full 10-K JSON |
| `financial-reports-xlsx` | `symbol`, `year`, `period` | Full 10-K XLSX |
| `financial-statement-full-as-reported` | `symbol` | Combined as-reported |
| `latest-financial-statements` | — | Recent filers (`page`, `limit`) |

## Analyst (1)

| Endpoint | Required | Use |
|---|---|---|
| `analyst-estimates` | `symbol`, `period` | Consensus revenue / EPS / EBITDA. `period` = `annual` or `quarter` |

## Calendar (2)

| Endpoint | Required | Use |
|---|---|---|
| `earnings` | `symbol` | One name's earnings history and next print |
| `earnings-calendar` | — | Cross-name calendar (`from`, `to`, `page`) |

## Company (17)

| Endpoint | Required | Use |
|---|---|---|
| `profile` | `symbol` | Company snapshot, including price |
| `profile-cik` | `cik` | Profile by CIK |
| `market-capitalization` | `symbol` | Latest market cap |
| `market-capitalization-batch` | `symbols` | Comma-separated caps |
| `historical-market-capitalization` | `symbol` | Cap history |
| `shares-float` | `symbol` | Float |
| `shares-float-all` | — | All floats (`page`, `limit`) |
| `stock-peers` | `symbol` | Peers |
| `key-executives` | `symbol` | Executives |
| `governance-executive-compensation` | `symbol` | Exec pay |
| `executive-compensation-benchmark` | — | Industry pay |
| `employee-count` | `symbol` | Headcount |
| `historical-employee-count` | `symbol` | Headcount history |
| `company-notes` | `symbol` | Issued notes |
| `delisted-companies` | — | Delistings |
| `mergers-acquisitions-latest` | — | Latest M&A |
| `mergers-acquisitions-search` | `name` | M&A by name |

## SEC filings (12)

Date-range searches require `from` and `to`.

| Endpoint | Required | Use |
|---|---|---|
| `sec-filings-search/symbol` | `symbol`, `from`, `to` | Filings by ticker |
| `sec-filings-search/cik` | `cik`, `from`, `to` | Filings by CIK |
| `sec-filings-search/form-type` | `formType`, `from`, `to` | e.g. `8-K`, `10-K` |
| `sec-filings-8k` | `from`, `to` | Latest 8-Ks |
| `sec-filings-financials` | `from`, `to` | Latest financial filings |
| `sec-filings-company-search/symbol` | `symbol` | Company record |
| `sec-filings-company-search/cik` | `cik` | Company record |
| `sec-filings-company-search/name` | `company` | Company record |
| `sec-profile` | `symbol` | Full SEC profile |
| `all-industry-classification` | — | SIC directory |
| `industry-classification-search` | — | SIC by symbol/CIK/code |
| `standard-industrial-classification-list` | — | SIC list |

## Institutional 13F (8)

Holder routes usually need `cik` + `year` + `quarter`.

| Endpoint | Required | Use |
|---|---|---|
| `institutional-ownership/latest` | — | Latest 13F filings |
| `institutional-ownership/dates` | `cik` | Filing dates for a holder |
| `institutional-ownership/extract` | `cik`, `year`, `quarter` | Holder positions |
| `institutional-ownership/extract-analytics/holder` | `symbol`, `year`, `quarter` | Holders of a symbol |
| `institutional-ownership/symbol-positions-summary` | `symbol`, `year`, `quarter` | Position summary |
| `institutional-ownership/holder-industry-breakdown` | `cik`, `year`, `quarter` | Holder sector mix |
| `institutional-ownership/holder-performance-summary` | `cik` | Holder performance |
| `institutional-ownership/industry-summary` | `year`, `quarter` | Industry aggregates |

## Insider (6)

| Endpoint | Required | Use |
|---|---|---|
| `insider-trading/latest` | — | Latest Form 4s |
| `insider-trading/search` | — | By `symbol`, `reportingCik`, or `companyCik` |
| `insider-trading/statistics` | `symbol` | Buy/sell stats |
| `insider-trading/reporting-name` | `name` | Search by insider name |
| `insider-trading-transaction-type` | — | Type list |
| `acquisition-of-beneficial-ownership` | `symbol` | Schedule 13D/G |

## Congress (4)

| Endpoint | Required | Use |
|---|---|---|
| `senate-trades` | `symbol` | Senate trades in a name |
| `senate-latest` | — | Latest Senate disclosures |
| `house-trades` | `symbol` | House trades in a name |
| `house-latest` | — | Latest House disclosures |

## Transcripts (3)

| Endpoint | Required | Use |
|---|---|---|
| `earning-call-transcript` | `symbol`, `year`, `quarter` | Full transcript |
| `earning-call-transcript-dates` | `symbol` | Available year/quarter |
| `earning-call-transcript-latest` | — | Latest transcripts |

## Market hours (3)

| Endpoint | Required | Use |
|---|---|---|
| `all-exchange-market-hours` | — | All venues |
| `exchange-market-hours` | `exchange` | One venue, e.g. `NASDAQ` |
| `holidays-by-exchange` | `exchange` | Holidays |

## Indexes (10)

`quote` / `quote-short` are documented for index symbols such as `^VIX`. For a stock or ETF snapshot use `profile`.

| Endpoint | Required | Use |
|---|---|---|
| `quote` | `symbol` | Index quote |
| `quote-short` | `symbol` | Short index quote |
| `batch-index-quotes` | — | All index quotes |
| `index-list` | — | Index directory |
| `sp500-constituent` | — | Current S&P 500 |
| `nasdaq-constituent` | — | Current Nasdaq-100 |
| `dowjones-constituent` | — | Current DJIA |
| `historical-sp500-constituent` | — | S&P 500 changes |
| `historical-nasdaq-constituent` | — | Nasdaq-100 changes |
| `historical-dowjones-constituent` | — | DJIA changes |

## News (10)

News only. No crypto or forex prices.

| Endpoint | Required | Use |
|---|---|---|
| `news/stock` | `symbols` | Search stock news |
| `news/stock-latest` | — | Latest stock news |
| `news/general-latest` | — | General news |
| `news/press-releases` | `symbols` | Search press releases |
| `news/press-releases-latest` | — | Latest press releases |
| `news/crypto` | `symbols` | Search crypto news |
| `news/crypto-latest` | — | Latest crypto news |
| `news/forex` | `symbols` | Search FX news |
| `news/forex-latest` | — | Latest FX news |
| `fmp-articles` | — | FMP-authored articles |

## Economics (4)

| Endpoint | Required | Use |
|---|---|---|
| `treasury-rates` | — | Full curve (`from`, `to`) |
| `economic-indicators` | `name` | `GDP`, `CPI`, `federalFunds`, `unemploymentRate`, … |
| `economic-calendar` | — | Releases (`country`, `from`, `to`) |
| `market-risk-premium` | — | Country ERP |

## Technicals (9)

All require `symbol`, `periodLength`, `timeframe` (`1min`, `5min`, `15min`, `30min`, `1hour`, `4hour`, `1day`).

`technical-indicators/sma` `ema` `wma` `dema` `tema` `rsi` `adx` `williams` `standarddeviation`

## ETF and funds (9)

| Endpoint | Required | Use |
|---|---|---|
| `etf/holdings` | `symbol` | Holdings |
| `etf/info` | `symbol` | Fund facts |
| `etf/sector-weightings` | `symbol` | Sector weights |
| `etf/country-weightings` | `symbol` | Country weights |
| `etf/asset-exposure` | `symbol` | Which ETFs hold this stock |
| `funds/disclosure` | `symbol`, `year`, `quarter` | Mutual-fund disclosure |
| `funds/disclosure-dates` | `symbol` | Disclosure dates |
| `funds/disclosure-holders-latest` | `symbol` | Latest holders of a stock |
| `funds/disclosure-holders-search` | `name` | Holder search |

## DCF (4)

| Endpoint | Required | Use |
|---|---|---|
| `discounted-cash-flow` | `symbol` | Standard DCF |
| `levered-discounted-cash-flow` | `symbol` | Levered DCF |
| `custom-discounted-cash-flow` | `symbol` | Custom assumptions |
| `custom-levered-discounted-cash-flow` | `symbol` | Custom levered |
