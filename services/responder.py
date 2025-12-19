# services/responder.py
import re
from services.finder import find_by_ip, find_by_alias, find_hub_db

def respond(intent):
    text = intent["text"].lower()

    # IP query
    ip = re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)
    if ip:
        r = find_by_ip(ip.group())
        if r:
            return f"🔍 IP FOUND\nHub : {r['hub']}\nNode: {r['node']}\nType: {r['type']}\nAlias/Role: {r.get('alias', r.get('role'))}"
        return "❌ IP not found"

    # Alias query
    parts = text.split()
    for p in parts:
        r = find_by_alias(p)
        if r:
            return f"🔍 ALIAS FOUND\nAlias: {p}\nHub : {r['hub']}\nNode: {r['node']}\nType: {r['type']}\nIP  : {r['ip']}"

    # DB query
    if "db" in text:
        primary = "primary" in text or "new" in text
        hub = re.search(r"hub\s*-?\s*\d+", text)
        if hub:
            r = find_hub_db(hub.group(), primary)
            if r:
                return f"🗄️ DATABASE\nHub : {r[0]}\nNode: {r[1]}\nType: {r[2]}\nIP  : {r[3]}"

    return "❗ Try: 10.x.x.x | h3se4 ip | Hub1 primary db ip"
