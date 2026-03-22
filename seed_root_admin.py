#!/usr/bin/env python3
"""
Initialize the Nestperts local auth SQLite database and register the root administrator.

The root admin is approved for login, has admin privileges, and cannot be deleted or
demoted by other admins (stored in app_settings.root_email).

Usage (from repository root, with virtualenv activated):

    python seed_root_admin.py

You will be prompted for the root admin email. You can still pass it explicitly:

    python seed_root_admin.py you@example.com

Optional:

    python seed_root_admin.py --db /path/to/custom_auth.db
    python seed_root_admin.py --force   # replace existing root (combine with email arg or prompt)

Requires GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET only for signing in via the web app;
this script only touches the SQLite file.

Repository: https://github.com/OliseNS/nexus_project
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or update the local Nestperts auth DB and set the root admin email."
    )
    parser.add_argument(
        "email",
        nargs="?",
        default=None,
        help="Root admin email (if omitted, you will be prompted in the terminal)",
    )
    parser.add_argument(
        "--db",
        dest="auth_db_path",
        metavar="PATH",
        help="SQLite path (overrides AUTH_DB_PATH; default: data/user_auth.db under repo root)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="If a different root is already set, replace it with this email",
    )
    args = parser.parse_args()

    email = (args.email or "").strip().lower()
    if not email:
        try:
            email = input("Root admin email (Google account): ").strip().lower()
        except EOFError:
            print("No email provided.", file=sys.stderr)
            sys.exit(1)
    if not email or "@" not in email:
        print("A valid email address is required.", file=sys.stderr)
        sys.exit(1)

    try:
        from dotenv import load_dotenv
    except ImportError:
        print("python-dotenv is required (install project requirements).", file=sys.stderr)
        sys.exit(1)

    load_dotenv(ROOT / ".env")

    if args.auth_db_path:
        os.environ["AUTH_DB_PATH"] = str(Path(args.auth_db_path).expanduser().resolve())

    from labeller.auth import get_auth_db_path, seed_root_admin

    try:
        seed_root_admin(email, force=args.force)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(f"Auth database: {get_auth_db_path()}")
    print(f"Root admin seeded: {email}")
    print("Next: add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and SECRET_KEY to .env, then run Nestperts and sign in with Google.")


if __name__ == "__main__":
    main()
