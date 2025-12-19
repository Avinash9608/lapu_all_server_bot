# services/loader.py
import json
import os

def load_data():
    # 1️⃣ First try ENV (Render / Production)
    env_json = os.getenv("HUBS_JSON")
    if env_json:
        return json.loads(env_json)

    # 2️⃣ Fallback to local file (Local dev)
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "../data/hubs.json")

    with open(path, "r") as f:
        return json.load(f)
