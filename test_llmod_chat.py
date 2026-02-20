import os
from dotenv import load_dotenv
import requests

load_dotenv()

key = os.getenv("LMMOD_API_KEY")
print("Key loaded:", bool(key))

url = "https://api.llmod.ai/v1/chat/completions"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
payload = {
    "model": "RPRTHPB-gpt-5-mini",
    "messages": [{"role": "user", "content": "Say hello in Hebrew in one sentence."}],
    "temperature": 1
}

r = requests.post(url, headers=headers, json=payload, timeout=30)
print("Status:", r.status_code)
print(r.text[:500])
