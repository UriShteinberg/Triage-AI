from __future__ import annotations

import argparse
import csv
import io
import re
import sqlite3
from pathlib import Path
from typing import List
import pandas as pd


ENCODINGS_TO_TRY = ["utf-8-sig", "utf-8", "cp1255", "cp1252", "latin-1"]


def open_text_fallback(path: Path):
    """Open text file with encoding fallback."""
    last_err = None
    for enc in ENCODINGS_TO_TRY:
        try:
            return path.open("r", encoding=enc, errors="strict", newline="")
        except UnicodeDecodeError as e:
            last_err = e
            continue
        except Exception:
            # try next encoding on any unexpected decode issues
            continue
    # last resort: replace errors (never fails)
    return path.open("r", encoding="latin-1", errors="replace", newline="")

def iter_no_nul(f):
    """Yield lines with NUL bytes removed (csv module crashes on NUL)."""
    for line in f:
        if "\x00" in line:
            line = line.replace("\x00", "")
        yield line

def sniff_delimiter_from_file(path: Path, max_chars: int = 80_000) -> str:
    """Detect delimiter from the beginning of the file."""
    with open_text_fallback(path) as f:
        sample = f.read(max_chars)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        # fallback: guess based on common counts in header line
        first_line = sample.splitlines()[0] if sample else ""
        counts = {d: first_line.count(d) for d in [",", ";", "\t", "|"]}
        return max(counts, key=counts.get) if first_line else ","


def count_lines_fast(path: Path, chunk_size: int = 1024 * 1024) -> int:
    """Fast line count using binary chunks. Returns number of '\n' + 1 if file non-empty."""
    n = 0
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            n += b.count(b"\n")
    # if file has content but no newline, count as 1 line
    return n + 1 if path.stat().st_size > 0 and n == 0 else n


_int_re = re.compile(r"^[+-]?\d+$")
_float_re = re.compile(r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")


def infer_type(values: List[str]) -> str:
    """Infer a simple type from sample strings."""
    v = [x.strip() for x in values if str(x).strip() != ""]
    if not v:
        return "empty"

    # bool-ish
    bool_set = {"0", "1", "true", "false", "yes", "no", "t", "f"}
    if all(str(x).strip().lower() in bool_set for x in v):
        return "bool"

    if all(_int_re.match(x) for x in v):
        return "int"

    if all(_float_re.match(x) for x in v):
        return "float"

    return "text"


def inspect_csv_schemas(dataset_dir: Path, out_path: Path, sample_rows: int = 200) -> None:
    """
    Write markdown report with file name, delimiter, row/col counts, and inferred schema.
    """
    csv_files = sorted(dataset_dir.glob("*.csv"))

    lines = []
    lines.append(f"# Triage dataset CSV schemas\n")
    lines.append(f"Folder: `{dataset_dir}`\n")
    lines.append(f"Files: {len(csv_files)}\n")

    for p in csv_files:
        delim = sniff_delimiter_from_file(p)
        n_lines = count_lines_fast(p)
        n_rows_est = max(n_lines - 1, 0)

        # read header + sample rows
        with open_text_fallback(p) as f:
            reader = csv.reader(iter_no_nul(f), delimiter=delim)
            try:
                header = next(reader)
            except StopIteration:
                header = []

            samples = {h: [] for h in header}
            for i, row in enumerate(reader):
                if i >= sample_rows:
                    break
                # pad/truncate
                if len(row) < len(header):
                    row = row + [""] * (len(header) - len(row))
                elif len(row) > len(header):
                    row = row[: len(header)]
                for h, cell in zip(header, row):
                    samples[h].append(cell)

        # infer types
        schema = [(h, infer_type(samples.get(h, []))) for h in header]

        lines.append(f"\n---\n## {p.name}\n")
        lines.append(f"- Size: {p.stat().st_size/1024/1024:.2f} MB\n")
        delim_disp = "TAB" if delim == "\t" else delim
        lines.append(f"- Delimiter: `{delim_disp}`\n")
        lines.append(f"- Estimated rows (excluding header): **{n_rows_est:,}**\n")
        lines.append(f"- Columns: **{len(header)}**\n\n")

        if not header:
            lines.append("_Empty or unreadable file._\n")
            continue

        lines.append("| column | inferred_type |\n")
        lines.append("|---|---|\n")
        for col, t in schema:
            col_clean = col.strip() if col is not None else ""
            lines.append(f"| {col_clean} | {t} |\n")

    out_path.write_text("".join(lines), encoding="utf-8")



def read_text_with_fallback(path: Path) -> str:
    b = path.read_bytes()
    for enc in ENCODINGS_TO_TRY:
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1", errors="replace")


def sniff_delimiter(text: str) -> str:
    sample = text[:50_000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        return ","


def sanitize_table_name(stem: str) -> str:
    """
    SQLite reserves internal names like sqlite_sequence and anything starting with sqlite_.
    Also make the name SQL-safe.
    """
    name = stem.strip()

    # If it's a reserved/internal name, prefix it
    lower = name.lower()
    if lower == "sqlite_sequence" or lower.startswith("sqlite_"):
        name = f"csv_{name}"

    # Replace spaces / hyphens with underscores, keep alnum + underscore
    name = re.sub(r"[^\w]+", "_", name).strip("_")

    if not name:
        name = "csv_table"
    return name


def load_csv_as_table(conn: sqlite3.Connection, csv_path: Path) -> str:
    text = read_text_with_fallback(csv_path)
    delim = sniff_delimiter(text)

    df = pd.read_csv(
        io.StringIO(text),
        sep=delim,
        dtype=str,
        keep_default_na=False,
        engine="python",
    )

    table = sanitize_table_name(csv_path.stem)
    df.to_sql(table, conn, if_exists="replace", index=False)
    return table

def split_sql_statements(sql_text: str) -> list[str]:
    # normalize newlines
    sql_text = sql_text.replace("\r\n", "\n").replace("\r", "\n")

    # remove '--' comment lines
    lines = []
    for ln in sql_text.splitlines():
        if ln.strip().startswith("--"):
            continue
        lines.append(ln)
    sql_text = "\n".join(lines).strip()

    # 1) Split on semicolons ONLY when followed by a new SELECT/WITH
    parts = re.split(r";\s*(?=(?:select|with)\b)", sql_text, flags=re.I)
    stmts = [p.strip().rstrip(";") for p in parts if p.strip()]
    if len(stmts) > 1:
        return stmts

    # 2) Split on blank lines when the next block starts with SELECT/WITH
    parts = re.split(r"\n\s*\n+(?=(?:select|with)\b)", sql_text, flags=re.I)
    stmts = [p.strip().rstrip(";") for p in parts if p.strip()]
    if len(stmts) > 1:
        return stmts

    # 3) Last resort: split on lines that start with SELECT/WITH
    matches = list(re.finditer(r"(?im)^(select|with)\b", sql_text))
    if len(matches) <= 1:
        return [sql_text.rstrip(";")]

    out = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(sql_text)
        chunk = sql_text[start:end].strip().rstrip(";")
        if chunk:
            out.append(chunk)
    return out


def safe_slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:60] or "result"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-dir", default="triage dataset", help='Folder containing the CSV tables (default: "triage dataset")')
    ap.add_argument("--sql-file", default="triage dataset/sql.txt", help="Path to SQL file (default: triage dataset/sql.txt)")
    ap.add_argument("--out-dir", default=".", help="Where to save output CSVs (default: current folder)")
    ap.add_argument("--inspect", action="store_true", help="Only inspect CSV schemas and exit")
    ap.add_argument("--sample-rows", type=int, default=200, help="Rows to sample for type inference")
    args = ap.parse_args()

    base_dir = Path(__file__).resolve().parent
    dataset_dir = (base_dir / args.dataset_dir).resolve()
    sql_file = (base_dir / args.sql_file).resolve()
    out_dir = (base_dir / args.out_dir).resolve()

    if args.inspect:
        report_path = out_dir / "triage_dataset_schemas.md"
        inspect_csv_schemas(dataset_dir, report_path, sample_rows=args.sample_rows)
        print(f"Wrote schema report: {report_path}")
        return


    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset dir not found: {dataset_dir}")
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")

    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(":memory:")

    # 1) Load CSVs as tables
    csv_files = sorted(dataset_dir.glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in: {dataset_dir}")

    name_map = {}
    for p in csv_files:
        tname = load_csv_as_table(conn, p)
        name_map[p.name] = tname

    print("Loaded tables:")
    for fn, tn in name_map.items():
        print(f"  {fn}  ->  {tn}")


    # 2) Run SQL statements and export results
    sql_text = read_text_with_fallback(sql_file)
    statements = split_sql_statements(sql_text)

    if not statements:
        raise ValueError("No SQL statements found in sql file.")

    for i, stmt in enumerate(statements, start=1):
        try:
            df_res = pd.read_sql_query(stmt, conn)
            name_hint = safe_slug(stmt.splitlines()[0])
            out_path = out_dir / f"sql_result_{i:02d}_{name_hint}.csv"
            df_res.to_csv(out_path, index=False, encoding="utf-8")
            print(f"[OK] Wrote {out_path}  (rows={len(df_res):,}, cols={df_res.shape[1]})")
        except Exception as e:
            err_path = out_dir / f"sql_result_{i:02d}_ERROR.txt"
            err_path.write_text(f"Statement:\n{stmt}\n\nError:\n{e}\n", encoding="utf-8")
            print(f"[FAIL] Statement #{i} failed. Details saved to: {err_path}")

    conn.close()


if __name__ == "__main__":
    main()
