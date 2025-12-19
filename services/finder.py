# services/finder.py
from services.loader import load_data

data = load_data()["hubs"]

def normalize():
    records = []

    for item in data:

        # ===== FORMAT 1 =====
        if "hub" in item and "servers" in item:
            records.append({
                "hub": item["hub"],
                "node": item["node"],
                "db": item.get("db", {}),
                "servers": item["servers"]
            })

        # ===== FORMAT 2 =====
        elif "hub" in item and "nodes" in item:
            for n in item["nodes"]:
                records.append({
                    "hub": item["hub"],
                    "node": n["node"],
                    "db": n.get("db", {}),
                    "servers": n.get("servers", [])
                })

        # ===== FORMAT 3 =====
        else:
            for hub_name, nodes in item.items():
                for node, body in nodes.items():
                    servers = []

                    for a in body.get("apps", []):
                        servers.append({
                            "app": a["type"],
                            "alias": a["alias"],
                            "ip": a["ip"]
                        })

                    for e in body.get("engines", []):
                        servers.append({
                            "app": "Engine",
                            "alias": e["alias"],
                            "ip": e["engine_ip"],
                            "connector": {
                                "alias": e["connector_alias"],
                                "ip": e["connector_ip"]
                            }
                        })

                    records.append({
                        "hub": hub_name,
                        "node": node,
                        "db": body.get("database", {}),
                        "servers": servers
                    })

    return records

NORMALIZED = normalize()

# -------- IP SEARCH --------
def find_by_ip(ip):
    for r in NORMALIZED:
        for k, v in r["db"].items():
            if v == ip:
                return {"type": "DB", "hub": r["hub"], "node": r["node"], "role": k}

        for s in r["servers"]:
            if s["ip"] == ip:
                return {"type": s["app"], "hub": r["hub"], "node": r["node"], "alias": s["alias"]}
            if "connector" in s and s["connector"]["ip"] == ip:
                return {"type": "Connector", "hub": r["hub"], "node": r["node"], "alias": s["connector"]["alias"]}

    return None

# -------- ALIAS SEARCH --------
def find_by_alias(alias):
    alias = alias.lower()
    for r in NORMALIZED:
        for s in r["servers"]:
            if s["alias"].lower() == alias:
                return {"hub": r["hub"], "node": r["node"], "type": s["app"], "ip": s["ip"]}
            if "connector" in s and s["connector"]["alias"].lower() == alias:
                return {"hub": r["hub"], "node": r["node"], "type": "Connector", "ip": s["connector"]["ip"]}
    return None

# -------- HUB DB SEARCH --------
def find_hub_db(hub, primary=True):
    for r in NORMALIZED:
        if hub.lower() in r["hub"].lower():
            for k, v in r["db"].items():
                if primary and "primary" in k:
                    return r["hub"], r["node"], k, v
    return None
