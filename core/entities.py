import re

def extract_hub(text: str):
    m = re.search(r"hub\s*-?\s*(\d)", text, re.I)
    return f"Hub-{m.group(1)}" if m else None

def extract_node(text: str):
    m = re.search(r"n\s*-?\s*(\d)", text, re.I)
    return f"N-{m.group(1)}" if m else None

def extract_engine(text: str):
    m = re.search(r"(pe|se|h\dpe|h\dse)\s*\d+", text, re.I)
    return m.group(0).lower() if m else None
