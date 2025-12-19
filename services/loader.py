import json
import os

def load_data():
    data_str = os.getenv("HUBS_JSON")
    if data_str:
        return json.loads(data_str)
    # fallback to local file
    path = os.path.join(os.path.dirname(__file__), "../data/hubs.json")
    with open(path, "r") as f:
        return json.load(f)
