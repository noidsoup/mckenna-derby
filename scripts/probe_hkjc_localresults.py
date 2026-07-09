#!/usr/bin/env python3
"""Availability probe for HKJC Local Results pages (not a bulk scraper).

Samples meeting dates from ``rawdata/races.csv`` and records whether the
official Local Results HTML returns dividends (TIERCE/TRIO) or
\"No information\".

Use for research / validation planning only. This repo does **not** bulk
download or parse dividends from HKJC (copyright / ToS). Prefer Renavon
Full Archive for joinable 2001–2005 data — see
``scripts/import_renavon_dividends.md``.

Example::

    python scripts/probe_hkjc_localresults.py --mode sample
    python scripts/probe_hkjc_localresults.py --mode monthly --start 2001-01-01
"""

from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RACES = ROOT / "rawdata" / "races.csv"
DEFAULT_OUT = ROOT / "output" / "hkjc_localresults_probe.csv"
BASE = (
    "https://racing.hkjc.com/racing/information/English/racing/LocalResults.aspx"
)
UA = (
    "Mozilla/5.0 (compatible; McKennaDerbyAvailabilityProbe/0.1; "
    "+research; not for bulk harvest)"
)

SAMPLE_DATES = [
    "1997-06-02",
    "1997-09-18",
    "1997-12-29",
    "1998-08-05",
    "1999-07-28",
    "2000-01-02",
    "2000-08-02",
    "2000-12-31",
    "2001-01-03",
    "2001-08-01",
    "2002-07-31",
    "2003-01-01",
    "2003-08-02",
    "2004-07-31",
    "2005-01-01",
    "2005-06-05",
    "2005-08-28",
]


def fetch(date_iso: str, venue: str, race_no: int) -> str:
    y, m, d = date_iso.split("-")
    url = f"{BASE}?RaceDate={y}/{m}/{d}&Racecourse={venue}&RaceNo={int(race_no)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def classify(body: str) -> dict:
    no_info = "No information" in body
    upper = body.upper()
    return {
        "no_info": no_info,
        "has_tierce": (not no_info) and ("TIERCE" in upper),
        "has_trio": (not no_info) and ("TRIO" in upper),
        "bytes": len(body),
    }


def probe_one(date_iso: str, venue: str, race_no: int, sleep_s: float) -> dict:
    body = fetch(date_iso, venue, race_no)
    row = {"date": date_iso, "venue": venue, "race_no": race_no, **classify(body)}
    if row["no_info"]:
        other = "HV" if venue == "ST" else "ST"
        time.sleep(sleep_s)
        body2 = fetch(date_iso, other, 1)
        alt = classify(body2)
        if alt["has_tierce"]:
            row.update(
                {
                    "venue": other,
                    "race_no": 1,
                    "alt_venue_used": True,
                    **{k: alt[k] for k in ("no_info", "has_tierce", "has_trio", "bytes")},
                }
            )
        else:
            row["alt_venue_used"] = False
    else:
        row["alt_venue_used"] = False
    return row


def dates_for_mode(races: pd.DataFrame, mode: str, start: str, end: str) -> pd.DataFrame:
    sub = races[(races["date"] >= start) & (races["date"] <= end)]
    if mode == "sample":
        want = [d for d in SAMPLE_DATES if start <= d <= end]
        rows = []
        for d in want:
            hit = sub[sub["date"] == d]
            if hit.empty:
                continue
            rows.append(hit.sort_values(["venue", "race_no"]).iloc[0])
        return pd.DataFrame(rows)
    # monthly: first meeting day per YYYY-MM
    sub = sub.copy()
    sub["ym"] = sub["date"].str.slice(0, 7)
    return sub.sort_values(["date", "venue", "race_no"]).groupby("ym", as_index=False).first()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--races", type=Path, default=DEFAULT_RACES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mode", choices=("sample", "monthly"), default="sample")
    ap.add_argument("--start", default="1997-06-02")
    ap.add_argument("--end", default="2005-08-28")
    ap.add_argument("--sleep", type=float, default=0.8, help="seconds between requests")
    args = ap.parse_args()

    if not args.races.exists():
        raise SystemExit(f"Missing {args.races}")

    races = pd.read_csv(args.races, usecols=["race_id", "date", "venue", "race_no"])
    targets = dates_for_mode(races, args.mode, args.start, args.end)
    print(f"Probing {len(targets)} meetings ({args.mode}) …")

    rows = []
    for _, r in targets.iterrows():
        try:
            row = probe_one(str(r["date"]), str(r["venue"]), int(r["race_no"]), args.sleep)
            row["race_id"] = int(r["race_id"])
            status = "ok" if row["has_tierce"] else "no_info"
            print(f"  {row['date']} {row['venue']} R{row['race_no']}: {status}")
            rows.append(row)
        except Exception as exc:  # noqa: BLE001 — probe continues
            print(f"  {r['date']} ERROR {exc}")
            rows.append({"date": r["date"], "venue": r["venue"], "error": str(exc)})
        time.sleep(args.sleep)

    out = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    n_ok = int(out["has_tierce"].fillna(False).sum()) if "has_tierce" in out.columns else 0
    print(f"Wrote {args.out}: {n_ok}/{len(out)} with TIERCE visible")
    print(
        "Reminder: availability ≠ license to bulk scrape. "
        "Use Renavon archive for production joins."
    )


if __name__ == "__main__":
    main()
