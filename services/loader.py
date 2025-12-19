import json

def load_data():
    with open("data/hubs.json", "r") as f:
        return json.load(f)
