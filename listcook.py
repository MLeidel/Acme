#!/usr/bin/env python3
'''  listcook.py
list unique cookies from cookies.sqlite (moz_cookies table)

Usage:
  python listcook.py
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

    sql = f"SELECT DISTINCT host FROM moz_cookies order by host ASC"

    conn = sqlite3.connect("cookies.sqlite")
    try:
        cur = conn.cursor()
        cur.execute(sql)

        for (host,) in cur.fetchall():
            print(host)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
