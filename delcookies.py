#!/usr/bin/env python3
'''  delcookies.py
Delete rows from cookies.sqlite (moz_cookies table) where moz_cookies.host
is NOT present in the provided domain list file (goodcookie.txt)

Usage:
  python delcookies.py
'''

import sys
import sqlite3
from pathlib import Path


def load_domains(domains_file: str) -> set[str]:
    domains = set()
    with open(domains_file, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            domains.add(s)
    return domains


def main():

    domains = load_domains("goodcookie.txt")  # a set of all good cookies
    if not domains:
        print("No domains loaded. Refusing to delete all cookies.")
        sys.exit(1)

    placeholders = ",".join(["?"] * len(domains))

    # Delete cookies whose host is NOT in the allowed list.
    # Keep the exact string matches as provided in the file.
    sql = f"DELETE FROM moz_cookies WHERE host NOT IN ({placeholders})"

    conn = sqlite3.connect("cookies.sqlite")
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(domains))
        conn.commit()
        print(f"Deleted {cur.rowcount} rows from moz_cookies.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
