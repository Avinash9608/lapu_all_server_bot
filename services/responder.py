# services/responder.py
from services.finder import find_by_ip, find_by_alias, find_hub_db

def generate_response(text):
    text_lower = text.lower().strip()

    # -------- IP SEARCH --------
    if any(c.isdigit() for c in text_lower):
        result = find_by_ip(text_lower)
        if result:
            if result["type"] == "DB":
                return f"💾 DB Found: {result['hub']} - {result['node']} - {result['role']}"
            elif result["type"] == "Connector":
                return f"🔌 Connector Found: {result['hub']} - {result['node']} - {result['alias']}"
            else:
                return f"🖥️ Server Found: {result['hub']} - {result['node']} - {result['type']} - {result['alias']}"
        else:
            return "❌ IP not found."

    # -------- ALIAS SEARCH --------
    if text_lower.startswith("alias "):
        alias = text_lower.replace("alias ", "").strip()
        result = find_by_alias(alias)
        if result:
            return f"🔹 Alias Found: {result['hub']} - {result['node']} - {result['type']} - {result['ip']}"
        else:
            return "❌ Alias not found."

    # -------- HUB DB SEARCH --------
    if text_lower.startswith("hub "):
        hub_name = text_lower.replace("hub ", "").strip()
        result = find_hub_db(hub_name, primary=True)
        if result:
            hub, node, role, ip = result
            return f"💾 Hub DB Found: {hub} - {node} - {role} - {ip}"
        else:
            return "❌ Hub DB not found."

    return "❗ Please send a valid IP, 'alias <name>' or 'hub <name>'"
