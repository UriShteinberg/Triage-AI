import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import requests
from dotenv import load_dotenv
from pinecone import Pinecone


def build_text(row: Dict[str, Any]) -> str:
    parts = []

    def add(label: str, value: str):
        if value:
            parts.append(f"{label}: {value.strip()}")

    add("Chief complaint", row.get("chief_complaint_name", ""))
    add("Diagnosis", row.get("diagnosis_name", ""))
    add("Symptoms", row.get("diagnosis_symptoms_text", ""))
    add("Description", row.get("diagnosis_description", ""))
    add("Workup", row.get("diagnosis_workup", ""))
    add("Treatment", row.get("diagnosis_treatment", ""))
    add("Specific tests", row.get("diagnosis_other_specific_tests", ""))

    text = " | ".join(parts)
    # Keep text reasonably sized to avoid oversized payloads.
    return text[:4000]


def get_embedding(text: str, api_key: str, model: str, dimensions: int | None) -> List[float]:
    url = "https://api.llmod.ai/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text}
    if dimensions:
        payload["dimensions"] = int(dimensions)

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Embedding request failed ({resp.status_code}): {resp.text[:500]}"
        )
    data = resp.json()
    emb = data["data"][0]["embedding"]
    if dimensions and len(emb) != int(dimensions):
        raise ValueError(f"Embedding dim mismatch: got {len(emb)} expected {dimensions}")
    return emb


def build_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": "cc_dx_knowledge.csv",
        "cc_dx_id": row.get("cc_dx_id"),
        "chief_complaint_id": row.get("chief_complaint_id"),
        "chief_complaint_name": row.get("chief_complaint_name"),
        "diagnosis_id": row.get("diagnosis_id"),
        "diagnosis_name": row.get("diagnosis_name"),
        "diagnosis_symptoms_text": row.get("diagnosis_symptoms_text"),
        "tests_list": row.get("tests_list"),
        "specialties_list": row.get("specialties_list"),
        "procedures_list": row.get("procedures_list"),
        "life_or_limb_threatening": row.get("life_or_limb_threatening"),
    }


def _format_seconds(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def _count_rows(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            total = sum(1 for _ in f) - 1  # exclude header
            return max(total, 0)
    except Exception:
        return 0


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_path = os.getenv("ENV_FILE", str(repo_root / ".env"))
    load_dotenv(dotenv_path=dotenv_path)

    parser = argparse.ArgumentParser(description="Ingest cc_dx_knowledge into Pinecone.")
    parser.add_argument("--input", default=os.path.join("data", "cc_dx_knowledge.csv"))
    parser.add_argument("--namespace", default=os.getenv("PINECONE_NAMESPACE", "ccdx_kb"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--limit", type=int, default=0, help="0 = no limit")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep between batches (seconds)")
    parser.add_argument("--model", default=None, help="Override embedding model.")
    parser.add_argument("--dimensions", type=int, default=None, help="Override embedding dimension.")
    parser.add_argument(
        "--no-dimensions",
        action="store_true",
        help="Do not send a dimensions parameter to the embeddings API.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar output.",
    )
    args = parser.parse_args()

    api_key = os.getenv("PINECONE_API_KEY")
    index_host = os.getenv("PINECONE_INDEX_HOST")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    llmod_api_key = os.getenv("LMMOD_API_KEY")
    model = args.model or os.getenv("RAG_EMBEDDING_MODEL", "RPRTHPB-gpt-5-mini")
    dimensions = args.dimensions if args.dimensions is not None else os.getenv("RAG_EMBEDDING_DIM", "1024")

    if not api_key or not index_host or not index_name:
        print(
            "ERROR: PINECONE_API_KEY / PINECONE_INDEX_HOST / PINECONE_INDEX_NAME must be set.",
            file=sys.stderr,
        )
        print(f"Loaded env file: {dotenv_path}", file=sys.stderr)
        return 2
    if not llmod_api_key:
        print("ERROR: LMMOD_API_KEY must be set.", file=sys.stderr)
        return 2
    if not os.path.exists(args.input):
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 2

    try:
        dimensions_int = int(dimensions) if (dimensions and not args.no_dimensions) else None
    except ValueError:
        print("ERROR: RAG_EMBEDDING_DIM must be an integer.", file=sys.stderr)
        return 2

    pc = Pinecone(api_key=api_key)
    index = pc.Index(host=index_host)

    to_upsert = []
    total = 0
    start_time = time.time()
    total_rows = 0
    if not args.no_progress:
        total_rows = _count_rows(args.input)
        if args.limit and total_rows:
            total_rows = min(total_rows, args.limit)

    progress_failed = False

    def render_progress(done: int):
        nonlocal progress_failed
        if not total_rows:
            return
        pct = min(1.0, done / max(1, total_rows))
        bar_len = 30
        filled = int(bar_len * pct)
        bar = "#" * filled + "-" * (bar_len - filled)
        elapsed = time.time() - start_time
        rate = done / elapsed if elapsed > 0 else 0.0
        eta = (total_rows - done) / rate if rate > 0 else 0.0
        msg = (
            f"\r[{bar}] {done}/{total_rows} "
            f"{pct * 100:5.1f}% ETA {_format_seconds(eta)}"
        )
        try:
            print(msg, end="", flush=True)
        except OSError:
            # Some terminals (or background processes) can't handle \r updates.
            progress_failed = True
            print()  # move to new line for subsequent logs

    with open(args.input, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if args.limit and total >= args.limit:
                break

            text = build_text(row)
            if not text:
                continue

            emb = get_embedding(text, llmod_api_key, model, dimensions_int)
            vec_id = f"ccdx-{row.get('cc_dx_id')}-{row.get('diagnosis_id')}"
            metadata = build_metadata(row)
            to_upsert.append({"id": vec_id, "values": emb, "metadata": metadata})
            total += 1
            if not args.no_progress and not progress_failed:
                render_progress(total)

            if len(to_upsert) >= args.batch_size:
                index.upsert(vectors=to_upsert, namespace=args.namespace)
                if args.no_progress:
                    print(f"Upserted {total} records...")
                to_upsert = []
                if args.sleep:
                    time.sleep(args.sleep)

    if to_upsert:
        index.upsert(vectors=to_upsert, namespace=args.namespace)
        if args.no_progress:
            print(f"Upserted {total} records (final batch).")

    if not args.no_progress and total_rows:
        print()  # newline after progress bar
    print("Ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
