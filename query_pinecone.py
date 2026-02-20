import os
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone
import requests

repo_root = Path(__file__).resolve().parent
dotenv_path = os.getenv("ENV_FILE", str(repo_root / ".env"))
load_dotenv(dotenv_path=dotenv_path, override=True)

API_KEY = os.getenv("PINECONE_API_KEY")
HOST = os.getenv("PINECONE_INDEX_HOST")
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "ccdx_kb")

LMMOD_API_KEY = os.getenv("LMMOD_API_KEY")


def get_embedding(text: str):
    url = "https://api.llmod.ai/v1/embeddings"
    headers = {"Authorization": f"Bearer {LMMOD_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "RPRTHPB-text-embedding-3-small",
        "input": text,
        "dimensions": 1024,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    emb = data["data"][0]["embedding"]
    print("Embedding length:", len(emb))
    return emb
    # return data["data"][0]["embedding"]


print("PINECONE:", "OK" if API_KEY and HOST else "MISSING")
print("LMMOD_API_KEY:", "SET" if LMMOD_API_KEY else "MISSING")
print("NAMESPACE:", NAMESPACE)

pc = Pinecone(api_key=API_KEY)
index = pc.Index(host=HOST)

q = "72yo shortness of breath hypoxemia SpO2 88 COPD"
vec = get_embedding(q)

res = index.query(
    vector=vec,
    top_k=5,
    namespace=NAMESPACE,
    include_metadata=True,
)

print("\n=== TOP MATCHES ===")
for m in res.get("matches", []):
    md = m.get("metadata", {})
    print("score:", m.get("score"), "| id:", m.get("id"), "| title:", md.get("title"), "| source:", md.get("source"))
print("\nTotal matches:", len(res.get("matches", [])))
