"""
ingest.py (FAIL-FAST, NO SKIPS, ASCII-SAFE)
-------------------------------------------
Ingest Supabase table `cc_dx_knowledge` into Pinecone integrated-embedding index.

.env required:
  SUPABASE_URL
  SUPABASE_KEY
  PINECONE_API_KEY
  PINECONE_INDEX_HOST

.env optional:
  TABLE=cc_dx_knowledge
  NAMESPACE=ccdx_kb
  FETCH_BATCH_ROWS=500
  UPSERT_BATCH=40            # MUST be <= 96
  MAX_ROWS=0
  TOKENS_PER_MINUTE=150000   # keep under 250k
  MAX_RETRIES=8
  ASCII_ONLY=1               # default 1 (recommended) to avoid UTF-8 poison chars
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from supabase import create_client
from pinecone import Pinecone
from pinecone.exceptions import PineconeApiException


# ----------------------------
# Config
# ----------------------------
TABLE = os.getenv("TABLE", "cc_dx_knowledge")
NAMESPACE = os.getenv("NAMESPACE", "ccdx_kb")

FETCH_BATCH_ROWS = int(os.getenv("FETCH_BATCH_ROWS", "500"))
UPSERT_BATCH = int(os.getenv("UPSERT_BATCH", "40"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "0"))

TOKENS_PER_MINUTE = int(os.getenv("TOKENS_PER_MINUTE", "150000"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "8"))
ASCII_ONLY = os.getenv("ASCII_ONLY", "1").strip() not in ("0", "false", "False")

PINECONE_MAX_BATCH = 96
if UPSERT_BATCH > PINECONE_MAX_BATCH:
    UPSERT_BATCH = PINECONE_MAX_BATCH

DUMPS_DIR = Path("pinecone_dumps")
DUMPS_DIR.mkdir(exist_ok=True)


# ----------------------------
# Sanitization
# ----------------------------
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_SURROGATES = re.compile(r"[\uD800-\uDFFF]")
_HEX_ESCAPE = re.compile(r"\\x([0-9a-fA-F]{2})")


def _decode_backslash_x(text: str) -> str:
    """Convert literal '\\xNN' sequences into real chars (latin-1 mapping)."""
    def repl(m: re.Match) -> str:
        b = int(m.group(1), 16)
        return bytes([b]).decode("latin-1")
    return _HEX_ESCAPE.sub(repl, text)


def s(x: Any) -> str:
    """Make a string safe for Pinecone request stream."""
    if x is None:
        return ""
    if isinstance(x, bytes):
        txt = x.decode("utf-8", errors="replace")
    else:
        txt = str(x)

    txt = _decode_backslash_x(txt)
    txt = unicodedata.normalize("NFKC", txt)
    txt = _CONTROL_CHARS.sub(" ", txt)
    txt = _SURROGATES.sub("", txt)

    # Ensure valid UTF-8 in Python
    txt = txt.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

    # 🔒 Bulletproof mode: convert to ASCII only (removes poison chars)
    if ASCII_ONLY:
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")

    return txt.strip()


def b(x: Any) -> bool:
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    try:
        return bool(int(x))
    except Exception:
        return bool(x)


def clean_meta(x: Any) -> Any:
    """Pinecone metadata must be JSON scalar types. No None."""
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            return None
        return x
    if isinstance(x, str):
        return s(x)
    return s(x)


def safe_filename(name: str, maxlen: int = 180) -> str:
    """Windows-safe file names (no : * ? \" < > | / \\)."""
    name = re.sub(r'[\\/:*?"<>|]+', "_", str(name))
    name = re.sub(r"\s+", "_", name).strip("_")
    return name[:maxlen]


def dump_json(obj: Any, filename: str) -> Path:
    path = DUMPS_DIR / safe_filename(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def validate_ascii(obj: Any, where: str) -> None:
    """
    Defensive check: after s(), all strings should be ASCII if ASCII_ONLY=True.
    If not, raise to catch before Pinecone.
    """
    if not ASCII_ONLY:
        return

    def _walk(v: Any, path: str) -> None:
        if isinstance(v, str):
            try:
                v.encode("ascii")
            except Exception as e:
                raise RuntimeError(f"Non-ASCII string at {where}:{path} -> {repr(v[:120])}") from e
        elif isinstance(v, dict):
            for k, vv in v.items():
                _walk(k, f"{path}.<key>")
                _walk(vv, f"{path}.{k}")
        elif isinstance(v, list):
            for i, vv in enumerate(v):
                _walk(vv, f"{path}[{i}]")

    _walk(obj, "$")


# ----------------------------
# Token throttling (rough)
# ----------------------------
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class TokenLimiter:
    def __init__(self, tpm: int):
        self.tpm = tpm
        self.q = deque()  # (t, tokens)

    def _prune(self, now: float) -> None:
        while self.q and (now - self.q[0][0]) > 60.0:
            self.q.popleft()

    def used(self, now: float) -> int:
        self._prune(now)
        return sum(toks for _, toks in self.q)

    def wait(self, tokens: int) -> None:
        while True:
            now = time.time()
            used = self.used(now)
            if used + tokens <= self.tpm:
                self.q.append((now, tokens))
                return
            sleep_for = max(0.5, 60.0 - (now - self.q[0][0]) + 0.05)
            time.sleep(min(sleep_for, 5.0))


# ----------------------------
# Record building (flattened metadata)
# ----------------------------
def build_records(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    cc_dx_id = row.get("cc_dx_id")
    if cc_dx_id is None:
        raise RuntimeError("Row missing cc_dx_id")

    chief = s(row.get("chief_complaint_name"))
    dx = s(row.get("diagnosis_name"))

    meta_raw = {
        "cc_dx_id": int(cc_dx_id),
        "chief_complaint_name": chief,
        "diagnosis_name": dx,
        "chief_complaint_id": clean_meta(row.get("chief_complaint_id")),
        "diagnosis_id": clean_meta(row.get("diagnosis_id")),
        "reason_code": clean_meta(row.get("reason_code")),
        "cc_life_threatening": b(row.get("cc_life_threatening")),
        "most_common": b(row.get("most_common")),
        "common_peds": b(row.get("common_peds")),
        "life_or_limb_threatening": b(row.get("life_or_limb_threatening")),
        "n_tests": clean_meta(row.get("n_tests")),
        "n_meds": clean_meta(row.get("n_meds")),
        "n_procedures": clean_meta(row.get("n_procedures")),
        "n_specialties": clean_meta(row.get("n_specialties")),
    }
    meta = {k: v for k, v in meta_raw.items() if v is not None}

    chunk1 = s("\n".join([
        f"Chief complaint: {chief}",
        f"Candidate diagnosis: {dx}",
        f"Description: {s(row.get('diagnosis_description'))}",
        f"Symptoms: {s(row.get('diagnosis_symptoms_text'))}",
        "",
        "Flags:",
        f"- most_common: {meta.get('most_common', False)}",
        f"- common_peds: {meta.get('common_peds', False)}",
        f"- life_or_limb_threatening: {meta.get('life_or_limb_threatening', False)}",
        f"- cc_life_threatening: {meta.get('cc_life_threatening', False)}",
    ]))

    chunk2 = s("\n".join([
        f"Chief complaint: {chief}",
        f"Diagnosis: {dx}",
        "Workup:",
        s(row.get("diagnosis_workup")),
        "",
        "Suggested tests:",
        s(row.get("diagnosis_other_specific_tests")),
        s(row.get("tests_list")),
    ]))

    chunk3 = s("\n".join([
        f"Chief complaint: {chief}",
        f"Diagnosis: {dx}",
        "Treatment:",
        s(row.get("diagnosis_treatment")),
        "",
        "Medications:",
        s(row.get("meds_list")),
        "Procedures:",
        s(row.get("procedures_list")),
        "Specialties:",
        s(row.get("specialties_list")),
    ]))

    records: List[Dict[str, Any]] = []
    if chunk1:
        records.append({"_id": f"ccdx:{cc_dx_id}:1", "text": chunk1, **meta})
    if chunk2:
        records.append({"_id": f"ccdx:{cc_dx_id}:2", "text": chunk2, **meta})
    if chunk3:
        records.append({"_id": f"ccdx:{cc_dx_id}:3", "text": chunk3, **meta})

    if not records:
        raise RuntimeError(f"cc_dx_id={cc_dx_id} produced 0 records")

    # Defensive validation before sending
    for rec in records:
        validate_ascii(rec, where=rec["_id"])
        json.dumps(rec)  # ensures JSON-serializable

    return records


# ----------------------------
# Pinecone upsert (fail-fast)
# ----------------------------
def pinecone_err(e: Exception) -> str:
    if isinstance(e, PineconeApiException):
        return f"(status={getattr(e,'status',None)}) body={getattr(e,'body',None)}"
    return str(e)


def upsert_with_retry(index, namespace: str, batch: List[Dict[str, Any]], limiter: TokenLimiter) -> None:
    tokens = sum(estimate_tokens(r.get("text", "")) for r in batch)
    limiter.wait(tokens)

    last: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            index.upsert_records(namespace, batch)
            return
        except PineconeApiException as e:
            last = e
            if getattr(e, "status", None) == 429:
                time.sleep(min(60, 2 ** attempt))
                continue
            break
        except Exception as e:
            last = e
            break

    raise RuntimeError(f"Upsert failed after retries: {pinecone_err(last)}")


def isolate_first_failing(index, namespace: str, batch: List[Dict[str, Any]], limiter: TokenLimiter) -> Tuple[Dict[str, Any], str]:
    def try_up(recs: List[Dict[str, Any]]) -> None:
        upsert_with_retry(index, namespace, recs, limiter)

    def rec_isolate(recs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(recs) == 1:
            return recs[0]
        mid = len(recs) // 2
        left, right = recs[:mid], recs[mid:]
        try:
            try_up(left)
        except Exception:
            return rec_isolate(left)
        try:
            try_up(right)
        except Exception:
            return rec_isolate(right)
        raise RuntimeError("Batch failed but both halves succeeded (timing/rate-limit).")

    bad = rec_isolate(batch)
    try:
        upsert_with_retry(index, namespace, [bad], limiter)
        return bad, "No error when upserting alone (unexpected)."
    except Exception as e:
        return bad, str(e)


def upsert_or_fail(index, namespace: str, batch: List[Dict[str, Any]], batch_no: int, limiter: TokenLimiter) -> None:
    try:
        upsert_with_retry(index, namespace, batch, limiter)
    except Exception as e:
        batch_path = dump_json(batch, f"failed_batch_{batch_no:04d}.json")
        print(f"[FAIL] Batch upsert failed -> {batch_path}")

        bad, err_detail = isolate_first_failing(index, namespace, batch, limiter)
        rid = bad.get("_id", "unknown")
        rec_path = dump_json(bad, f"failed_record_{batch_no:04d}_{rid}.json")

        raise RuntimeError(
            f"Pinecone upsert failed.\n"
            f"Batch dumped: {batch_path}\n"
            f"First failing record dumped: {rec_path} (id={rid})\n"
            f"Error detail: {err_detail}\n"
        ) from e


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    load_dotenv()
    required = ["SUPABASE_URL", "SUPABASE_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_HOST"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

    supa = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(host=os.environ["PINECONE_INDEX_HOST"])

    print(f"Starting ingest from Supabase table '{TABLE}' -> Pinecone namespace '{NAMESPACE}'")
    print(f"Supabase: {os.environ['SUPABASE_URL']}")
    print(f"Pinecone host: {os.environ['PINECONE_INDEX_HOST']}")
    print(f"FETCH_BATCH_ROWS={FETCH_BATCH_ROWS} | UPSERT_BATCH={UPSERT_BATCH} (max {PINECONE_MAX_BATCH})")
    print(f"TOKENS_PER_MINUTE={TOKENS_PER_MINUTE} | MAX_RETRIES={MAX_RETRIES} | ASCII_ONLY={ASCII_ONLY}")

    limiter = TokenLimiter(TOKENS_PER_MINUTE)

    offset = 0
    total_rows = 0
    total_records = 0
    batch_no = 0

    while True:
        if MAX_ROWS > 0 and total_rows >= MAX_ROWS:
            break

        resp = (
            supa.table(TABLE)
            .select("*")
            .range(offset, offset + FETCH_BATCH_ROWS - 1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break

        if MAX_ROWS > 0:
            rows = rows[: max(0, MAX_ROWS - total_rows)]

        total_rows += len(rows)

        all_records: List[Dict[str, Any]] = []
        for r in rows:
            all_records.extend(build_records(r))

        for i in range(0, len(all_records), UPSERT_BATCH):
            batch = all_records[i:i + UPSERT_BATCH]
            batch_no += 1
            upsert_or_fail(index, NAMESPACE, batch, batch_no, limiter)
            total_records += len(batch)

        print(f"progress: rows={total_rows} | records={total_records}")
        offset += FETCH_BATCH_ROWS

    print("DONE")
    print({"rows": total_rows, "records": total_records, "namespace": NAMESPACE, "dumps_dir": str(DUMPS_DIR)})


if __name__ == "__main__":
    main()
