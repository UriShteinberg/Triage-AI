#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import csv


def read_text_with_fallback(path: Path) -> str:
    """
    Read file bytes and decode using a few common Windows encodings.
    Falls back to 'latin-1' (never fails) if needed.
    """
    data = path.read_bytes()

    encodings_to_try = [
        "utf-8-sig",
        "utf-8",
        "cp1255",   # Hebrew Windows
        "cp1252",   # Western Windows
        "latin-1",  # never fails
    ]

    last_err = None
    for enc in encodings_to_try:
        try:
            return data.decode(enc)
        except UnicodeDecodeError as e:
            last_err = e

    # Should never happen because latin-1 doesn't raise, but just in case:
    raise last_err  # type: ignore


def split_semicolon_lines(text: str) -> list[list[str]]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() != ""]
    rows = [ln.split(";") for ln in lines]
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", default="data.csv")
    p.add_argument("--out", dest="out", default="emeregency_service_triage_application.csv")
    args = p.parse_args()

    base_dir = Path(__file__).resolve().parent
    in_path = (base_dir / args.inp).resolve()
    out_path = (base_dir / args.out).resolve()

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    text = read_text_with_fallback(in_path)
    rows = split_semicolon_lines(text)

    if not rows:
        raise ValueError("No rows found.")

    header = [h.strip() for h in rows[0]]
    data_rows = rows[1:]

    # pad / trim each row to header length
    fixed_rows = []
    for r in data_rows:
        r = [c.strip() for c in r]
        if len(r) < len(header):
            r = r + [""] * (len(header) - len(r))
        elif len(r) > len(header):
            r = r[: len(header)]
        fixed_rows.append(r)

    # write clean comma CSV
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(fixed_rows)

    print(f"Wrote: {out_path}")
    print(f"Columns: {len(header)} | Rows: {len(fixed_rows)}")
    print("Last column name:", header[-1])


if __name__ == "__main__":
    main()
