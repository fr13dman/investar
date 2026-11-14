"""Command line entry point: `uv run investar <command>`."""

import argparse
import logging

from app import db
from app.migrate import upgrade_head

log = logging.getLogger("investar")


def _session():
    return db.SessionLocal()


def cmd_migrate(_args):
    upgrade_head()
    print("database migrated")


def cmd_load_universe(_args):
    from app.services.ingest import load_universe

    with _session() as s:
        print(f"loaded {load_universe(s)} companies")


def cmd_backfill(args):
    from app.services.ingest import backfill_prices

    with _session() as s:
        print(f"stored {backfill_prices(s, period=args.period, tickers=args.tickers or None)} price bars")


def cmd_profiles(args):
    from app.services.ingest import enrich_profiles

    with _session() as s:
        print(f"enriched {enrich_profiles(s, tickers=args.tickers or None)} profiles")


def cmd_refresh_prices(_args):
    from app.services.ingest import refresh_intraday

    with _session() as s:
        print(f"refreshed {refresh_intraday(s)} tickers")


def cmd_load_niches(args):
    from app.services.ingest import fetch_new_symbols, fill_ciks
    from app.services.niches import load_catalog

    with _session() as s:
        result = load_catalog(s)
        print(f"loaded {result['niches']} niches, {result['members']} memberships; "
              f"{len(result['new_tickers'])} new symbols")
        if getattr(args, "fetch", True):
            fill_ciks(s)
            if result["new_tickers"]:
                print(f"stored {fetch_new_symbols(s, result['new_tickers'])} price bars for new symbols")


cmd_load_niches.configure_parser = lambda p: p.add_argument(
    "--no-fetch", dest="fetch", action="store_false", help="only update the catalog; skip profiles and prices")


def cmd_bootstrap(args):
    upgrade_head()
    cmd_load_universe(args)
    cmd_load_niches(argparse.Namespace(fetch=False))
    with _session() as s:
        from app.services.ingest import fill_ciks

        fill_ciks(s)
    cmd_profiles(argparse.Namespace(tickers=None))
    cmd_backfill(argparse.Namespace(period="5y", tickers=None))


def cmd_seed_demo(_args):
    from app.seed import seed_all

    upgrade_head()
    with _session() as s:
        seed_all(s)
    print("seeded demo data")


def cmd_import_patents_bulk(args):
    from app.services.patents import import_bulk

    with _session() as s:
        imported = import_bulk(s, args.directory, tickers=args.tickers or None)
    print(f"imported {sum(imported.values())} patent records for {len(imported)} companies")


cmd_import_patents_bulk.configure_parser = lambda p: (
    p.add_argument("directory", help="folder with g_patent / pg_published_application TSV files"),
    p.add_argument("--tickers", nargs="*", default=None),
)


def cmd_refresh_research(args):
    from functools import partial

    from app.services.research_jobs import WEEKLY_RESEARCH
    from app.services.refresh import last_fetch, run_refresh

    with _session() as s:
        for ticker in args.tickers:
            for resource, source, fn in WEEKLY_RESEARCH:
                run_refresh(resource, ticker.upper(), source, partial(fn, ticker=ticker.upper()))
                row = last_fetch(s, resource, ticker.upper())
                s.expire_all()
                print(f"{ticker.upper()} {resource}: {row.status if row else '?'} {row.message or '' if row else ''}")


cmd_refresh_research.configure_parser = lambda p: p.add_argument("tickers", nargs="+")


COMMANDS = {
    "migrate": (cmd_migrate, "apply database migrations"),
    "load-universe": (cmd_load_universe, "load S&P 500 + Nasdaq-100 constituents"),
    "load-niches": (cmd_load_niches, "apply the curated niche catalog and fetch data for new symbols"),
    "backfill": (cmd_backfill, "backfill daily prices"),
    "profiles": (cmd_profiles, "fetch sector/industry/profile data"),
    "refresh-prices": (cmd_refresh_prices, "refresh latest prices and swing metrics"),
    "bootstrap": (cmd_bootstrap, "migrate + universe + niches + profiles + 5y backfill"),
    "seed-demo": (cmd_seed_demo, "load deterministic offline demo data"),
    "import-patents-bulk": (cmd_import_patents_bulk, "import PatentsView bulk TSV files (API fallback)"),
    "refresh-research": (cmd_refresh_research, "refresh CEO, global presence and patents for tickers"),
}

EXTRA_COMMANDS: dict = {}


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="investar")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (fn, help_text) in {**COMMANDS, **EXTRA_COMMANDS}.items():
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(fn=fn)
        if name in ("backfill", "profiles"):
            p.add_argument("tickers", nargs="*")
        if name == "backfill":
            p.add_argument("--period", default="5y")
        if hasattr(fn, "configure_parser"):
            fn.configure_parser(p)
    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
