"""
Seed the database from test/health_readings_scenario.json (14 days with scripted stories)
instead of the 48-hour fixture. Reuses everything in seed_test_db.py.

    python test/generate_scenario_readings.py
    python test/seed_scenario.py --clean --yes
"""
import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import seed_test_db  # noqa: E402  (it sets up the backend import paths itself)
from src.core.config import get_settings

seed_test_db._READINGS_FILE = _HERE / "health_readings_scenario.json"

ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def verify_clean_preconditions(clean: bool, yes: bool) -> None:
    if not clean:
        return

    # 1. Require explicit confirmation flag
    if not yes:
        print("\n[SAFETY ERROR] --clean wipes all crew members, user accounts, and health measurements.")
        print("To confirm destructive wiping of test data, you must pass --yes:")
        print("    python test/seed_scenario.py --clean --yes\n")
        sys.exit(1)

    # 2. Refuse unless DB host is localhost
    settings = get_settings()
    host = settings.POSTGRES_SERVER
    if settings.DATABASE_URL:
        parsed = urlparse(settings.DATABASE_URL)
        host = parsed.hostname or host

    if (host or "").lower() not in ALLOWED_LOCAL_HOSTS:
        print(f"\n[SAFETY ERROR] Refusing to run --clean against database host '{host}'.")
        print("Destructive --clean is restricted strictly to local development hosts: localhost, 127.0.0.1.\n")
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Seed database with 14-day scenario readings.")
    ap.add_argument("--clean", action="store_true",
                    help="Wipe existing crew, users and readings first (requires --yes and localhost DB)")
    ap.add_argument("--yes", action="store_true",
                    help="Explicit confirmation required when using --clean")
    args = ap.parse_args()

    verify_clean_preconditions(clean=args.clean, yes=args.yes)
    asyncio.run(seed_test_db.seed_database(clean=args.clean))
