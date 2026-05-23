#!/usr/bin/env python3
"""
Fetch https://ja4db.com/api/read and write:
- csv/all_records.csv               (full JSON->CSV; columns = union of all keys)
- csv/<ja4*_fingerprint>.csv        (one CSV per JA4* column, excluding ja4_fingerprint_string)

Each per-fingerprint CSV contains:
  application, library, device, os, user_agent_string, certificate_authority, verified, notes, <that fingerprint column>
and only includes rows where that fingerprint value is present/non-empty.

Usage:
  python ja4db_export.py
  python ja4db_export.py --base-dir ./
  python ja4db_export.py --url https://ja4db.com/api/read
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Set

import requests


URL_DEFAULT = "https://ja4db.com/api/read"

BASE_COLS = [
    "application",
    "library",
    "device",
    "os",
    "user_agent_string",
    "certificate_authority",
    "verified",
    "notes",
    "observation_count",
]

# for each ja4* e
FINGERPRINT_COLS = [
    "ja4_fingerprint",
    "ja4_fingerprint_string",
    "ja4s_fingerprint",
    "ja4h_fingerprint",
    "ja4x_fingerprint",
    "ja4t_fingerprint",
    "ja4ts_fingerprint",
    "ja4tscan_fingerprint",
]


USER_AGENT = (
    "ja4db-export/1.0 (+https://github.com/Niicolaa/ja4db-export) "
    "python-requests"
)


def fetch_json(url: str, timeout_s: int = 300, attempts: int = 4) -> Any:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, */*;q=0.1",
    }
    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout_s)
        except requests.RequestException as e:
            last_exc = e
            print(f"[fetch_json] attempt {i}/{attempts} network error: {e}")
        else:
            if r.status_code >= 400:
                snippet = r.text[:500].replace("\n", " ")
                print(
                    f"[fetch_json] attempt {i}/{attempts} HTTP {r.status_code} "
                    f"for {url} body[:500]={snippet!r}"
                )
                last_exc = requests.HTTPError(
                    f"{r.status_code} for {url}", response=r
                )
            else:
                try:
                    return r.json()
                except ValueError as e:
                    snippet = r.text[:500].replace("\n", " ")
                    print(
                        f"[fetch_json] attempt {i}/{attempts} JSON parse error: {e} "
                        f"body[:500]={snippet!r}"
                    )
                    last_exc = e
        if i < attempts:
            backoff = 2 ** i
            print(f"[fetch_json] sleeping {backoff}s before retry")
            time.sleep(backoff)
    assert last_exc is not None
    raise last_exc


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def to_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    # lists/dicts/etc. -> JSON string in the cell
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def norm(v: Any) -> str:
    """Normalize values for sorting."""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return f"{v:020}"   # numeric stable sort
    return str(v).lower().strip()


def record_sort_key(r: Dict[str, Any]) -> tuple:
    """
    Stable global ordering for all records.
    """
    return (
        norm(r.get("application")),
        norm(r.get("library")),
        norm(r.get("os")),
        norm(r.get("user_agent_string")),
        norm(r.get("ja4_fingerprint")),
        norm(r.get("ja4s_fingerprint")),
        norm(r.get("ja4h_fingerprint")),
        norm(r.get("ja4x_fingerprint")),
        norm(r.get("ja4t_fingerprint")),
        norm(r.get("ja4ts_fingerprint")),
        norm(r.get("ja4tscan_fingerprint")),
    )


def write_full_csv(payload: Any, csv_dir: Path, filename: str = "all_records.csv") -> Path:
    if not isinstance(payload, list):
        raise TypeError(
            "Expected API to return a JSON array (list of objects). "
            f"Got: {type(payload).__name__}"
        )

    rows: List[Dict[str, Any]] = [x for x in payload if isinstance(x, dict)]
    rows.sort(key=record_sort_key)
  
    keys: Set[str] = set()
    for r in rows:
        keys.update(r.keys())

    # base cols first (if present), then remaining keys sorted
    ordered: List[str] = [k for k in BASE_COLS if k in keys]
    ordered.extend(sorted(k for k in keys if k not in ordered))

    csv_dir.mkdir(parents=True, exist_ok=True)
    out_path = csv_dir / filename
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: to_csv_cell(r.get(k)) for k in ordered})
    return out_path


def write_fingerprint_csvs(payload: Any, csv_dir: Path) -> None:
    if not isinstance(payload, list):
        raise TypeError(
            "Expected API to return a JSON array (list of objects). "
            f"Got: {type(payload).__name__}"
        )

    csv_dir.mkdir(parents=True, exist_ok=True)

    files: Dict[str, Any] = {}
    writers: Dict[str, csv.DictWriter] = {}
    try:
        for fp_col in FINGERPRINT_COLS:
            path = csv_dir / f"{fp_col}.csv"
            fh = path.open("w", newline="", encoding="utf-8")
            files[fp_col] = fh
            fieldnames = BASE_COLS + [fp_col]
            w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            writers[fp_col] = w

        # Collect rows first
        buckets: Dict[str, List[Dict[str, Any]]] = {fp: [] for fp in FINGERPRINT_COLS}

        for item in payload:
            if not isinstance(item, dict):
                continue

            base = {c: to_csv_cell(item.get(c)) for c in BASE_COLS}

            for fp_col in FINGERPRINT_COLS:
                v = item.get(fp_col)
                if not is_present(v):
                    continue

                row = dict(base)
                row[fp_col] = to_csv_cell(v)
                buckets[fp_col].append(row)

        # Sort each CSV deterministically
        for fp_col, rows in buckets.items():
            rows.sort(key=lambda r: (
                norm(r.get(fp_col)),
                norm(r.get("application")),
                norm(r.get("library")),
                norm(r.get("os")),
                norm(r.get("user_agent_string")),
            ))
            for r in rows:
                writers[fp_col].writerow(r)

    finally:
        for fh in files.values():
            try:
                fh.close()
            except Exception:
                pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL_DEFAULT, help="JA4DB API read endpoint")
    ap.add_argument("--base-dir", default=".", help="Base output directory")
    args = ap.parse_args()

    base_dir = Path(args.base_dir).expanduser().resolve()
    csv_dir = base_dir / "csv"

    payload = fetch_json(args.url)

    full_csv_path = write_full_csv(payload, csv_dir, "all_records.csv")
    write_fingerprint_csvs(payload, csv_dir)

    print(f"Wrote full CSV:  {full_csv_path}")
    print(f"Wrote JA4 CSVs:  {csv_dir}")


if __name__ == "__main__":
    main()
