# Investar

A local stock research app for **S&P 500 and Nasdaq-100** companies:

- **Screener:** filter by sector and then industry; sort by market cap or by the biggest moves since the last trading
  day, over the trading week, and year to date (% or $); top movers per sector; SPY/QQQ benchmarks; watchlists.
- **Company research:** live quote, candlestick chart compared with SPY, profile and leadership, CEO performance
  scorecard, news with sentiment, global presence (subsidiary map, revenue by region), and patents (granted and
  pending).

Everything is stored in a local SQLite database. Research only; not financial advice.

## Stack

FastAPI + SQLAlchemy + Alembic + APScheduler (Python 3.13, `uv`) and a Next.js 16 App Router UI with TanStack
Query/Table, shadcn/ui, lightweight-charts, Recharts and react-simple-maps (`pnpm`).

## Setup

```bash
cp .env.example .env            # add FINNHUB_API_KEY (news + live quotes), SEC_USER_AGENT (your name + email)

cd backend
uv sync                         # add `--extra sentiment` for FinBERT (PyTorch, about 500 MB); otherwise VADER is used
uv run investar bootstrap       # migrate, load the stock list, profiles, 5 years of daily prices (about 10 minutes)
uv run uvicorn app.main:app --port 8010    # API + scheduler (15-min intraday, end-of-day, weekly research refresh)

cd ../frontend
pnpm install
pnpm dev                        # http://localhost:3010 (proxies /api to http://127.0.0.1:8010)
```

Offline demo data instead of live sources: `uv run investar seed-demo`.

### One command for both services

```bash
./dev.sh restart    # (re)start API on :8010 and UI on :3010, waits until both respond
./dev.sh start | stop | status | logs
```

Override ports with `API_PORT=... WEB_PORT=... ./dev.sh start`. Logs and PIDs are in `.run/`.

### Other commands

| Command | Purpose |
| --- | --- |
| `uv run investar refresh-prices` | Refresh the latest prices and swing metrics now |
| `uv run investar refresh-research AAPL MSFT` | Refresh CEO scorecard, global presence and patents |
| `uv run investar import-patents-bulk <dir>` | Import PatentsView bulk TSVs (fallback while the PatentsView API is migrating) |
| `uv run investar profiles [TICKERS]` / `backfill [TICKERS]` | Re-fetch profiles / price history |

## Tests

```bash
cd backend && uv run pytest              # unit + API tests (offline; recorded SEC/Wikidata fixtures)
cd frontend && pnpm test                 # Vitest + React Testing Library
cd frontend && pnpm e2e                  # Playwright against a seeded backend on ports 8100/3100
./scripts/test_dev.sh                    # dev.sh start/restart/stop smoke test on ports 18010/13010
```

## Feature documentation

- [Screener and market data](docs/features/FEATURE_screener_and_market_data.md)
- [Company research: profile, chart, CEO performance, news](docs/features/FEATURE_company_research_profile_ceo_news.md)
- [Global presence and patents](docs/features/FEATURE_global_presence_and_patents.md)
- [Dev service runner (`dev.sh`)](docs/features/FEATURE_dev_service_runner.md)
