import argparse
import os
import sys

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec, PodSpec


def _build_spec_from_source(spec_dict: dict):
    if not isinstance(spec_dict, dict):
        raise ValueError("Source index spec is missing or invalid.")

    if "serverless" in spec_dict:
        s = spec_dict["serverless"] or {}
        cloud = s.get("cloud")
        region = s.get("region")
        if not cloud or not region:
            raise ValueError("Serverless spec is missing cloud/region.")
        return ServerlessSpec(cloud=cloud, region=region)

    if "pod" in spec_dict:
        s = spec_dict["pod"] or {}
        env = s.get("environment")
        pod_type = s.get("pod_type", "p1.x1")
        replicas = s.get("replicas")
        shards = s.get("shards")
        pods = s.get("pods")
        metadata_config = s.get("metadata_config")
        source_collection = s.get("source_collection")
        if not env:
            raise ValueError("Pod spec is missing environment.")
        return PodSpec(
            environment=env,
            pod_type=pod_type,
            replicas=replicas,
            shards=shards,
            pods=pods,
            metadata_config=metadata_config,
            source_collection=source_collection,
        )

    raise ValueError("Unsupported index spec type (expected serverless or pod).")


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Create a new Pinecone index cloned from an existing index spec."
    )
    parser.add_argument(
        "--source",
        default=os.getenv("PINECONE_INDEX_NAME"),
        help="Source index name to clone (default: PINECONE_INDEX_NAME).",
    )
    parser.add_argument(
        "--new-name",
        default=os.getenv("PINECONE_NEW_INDEX_NAME"),
        help="New index name (or set PINECONE_NEW_INDEX_NAME).",
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=os.getenv("PINECONE_NEW_DIMENSION"),
        help="Vector dimension for the new index (must match your embedding model).",
    )
    parser.add_argument(
        "--metric",
        default=None,
        help="Override metric (default: source index metric).",
    )
    parser.add_argument(
        "--vector-type",
        default=None,
        help="Override vector type (default: source index vector_type).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved settings without creating the index.",
    )

    args = parser.parse_args()

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("ERROR: PINECONE_API_KEY is not set.", file=sys.stderr)
        return 2
    if not args.source:
        print("ERROR: source index name is required.", file=sys.stderr)
        return 2
    if not args.new_name:
        print("ERROR: new index name is required.", file=sys.stderr)
        return 2

    pc = Pinecone(api_key=api_key)

    # Prevent accidental overwrite
    existing = {idx.get("name") for idx in pc.list_indexes() if isinstance(idx, dict)}
    if args.new_name in existing:
        print(f"ERROR: index '{args.new_name}' already exists.", file=sys.stderr)
        return 2

    src = pc.describe_index(args.source).to_dict()
    metric = args.metric or src.get("metric", "cosine")
    vector_type = args.vector_type or src.get("vector_type", "dense")

    dimension = args.dimension if args.dimension is not None else src.get("dimension")
    if dimension is None:
        print("ERROR: dimension is required but could not be resolved.", file=sys.stderr)
        return 2
    if args.dimension is None:
        print(
            f"WARNING: dimension not specified; using source dimension {dimension}. "
            "This must match your embedding model."
        )

    spec_obj = _build_spec_from_source(src.get("spec") or {})

    if args.dry_run:
        print("DRY RUN: create index with settings:")
        print(f"  name: {args.new_name}")
        print(f"  dimension: {dimension}")
        print(f"  metric: {metric}")
        print(f"  vector_type: {vector_type}")
        print(f"  spec: {spec_obj}")
        return 0

    pc.create_index(
        name=args.new_name,
        dimension=int(dimension),
        metric=metric,
        vector_type=vector_type,
        spec=spec_obj,
    )
    print(f"Created index '{args.new_name}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
