import os
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone

repo_root = Path(__file__).resolve().parent
dotenv_path = os.getenv("ENV_FILE", str(repo_root / ".env"))
load_dotenv(dotenv_path=dotenv_path, override=True)

api_key = os.getenv("PINECONE_API_KEY")
host = os.getenv("PINECONE_INDEX_HOST")
name = os.getenv("PINECONE_INDEX_NAME")

print("PINECONE_API_KEY:", "SET" if api_key else "MISSING")
print("PINECONE_INDEX_HOST:", host)
print("PINECONE_INDEX_NAME:", name)

pc = Pinecone(api_key=api_key)
index = pc.Index(host=host)
stats = index.describe_index_stats()

print("\n=== INDEX STATS ===")
print(stats)
