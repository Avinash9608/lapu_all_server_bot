def detect_intent(text: str):
    t = text.lower()

    if "db" in t or "database" in t:
        return "SHOW_DB"

    if "connector" in t:
        return "SHOW_CONNECTORS"

    if "pe" in t or "se" in t:
        return "SHOW_ENGINE"

    return "UNKNOWN"
