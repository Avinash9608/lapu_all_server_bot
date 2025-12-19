import os
import json
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from aiohttp import web

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HUB_JSON_PATH = os.getenv("HUB_JSON_PATH")

# Load hubs data - support both file path and JSON string
if HUB_JSON_PATH:
    # Check if it's a file path or JSON content
    if os.path.exists(HUB_JSON_PATH):
        # It's a file path
        with open(HUB_JSON_PATH, 'r', encoding='utf-8') as f:
            hubs_data = json.load(f)
    elif HUB_JSON_PATH.strip().startswith('{'):
        # It's JSON content as string
        hubs_data = json.loads(HUB_JSON_PATH)
    else:
        # Try as file path relative to current directory
        if os.path.exists(HUB_JSON_PATH):
            with open(HUB_JSON_PATH, 'r', encoding='utf-8') as f:
                hubs_data = json.load(f)
        else:
            raise FileNotFoundError(f"HUB_JSON_PATH not found: {HUB_JSON_PATH}")
else:
    # Fallback to default location
    default_path = os.path.join(os.path.dirname(__file__), "data", "hubs.json")
    with open(default_path, 'r', encoding='utf-8') as f:
        hubs_data = json.load(f)

def normalize_name(name):
    """Normalize hub/node names: Hub3 -> Hub-3, N1 -> N-1, Hub-3 -> Hub-3"""
    if not name:
        return ""
    name = name.replace(' ', '').upper()
    # Handle Hub format: HUB3 or HUB-3 -> Hub-3
    name = re.sub(r'HUB-?(\d+)', r'Hub-\1', name, flags=re.IGNORECASE)
    # Handle Node format: N1 or N-1 -> N-1
    name = re.sub(r'N-?(\d+)', r'N-\1', name, flags=re.IGNORECASE)
    return name

def find_servers(hub_name, node_name=None):
    """Find servers for exact hub/node - handles ALL data structures"""
    hub_name = normalize_name(hub_name)
    
    for hub_entry in hubs_data["hubs"]:
        # Hub-1 style: direct {"hub": "Hub-1", "node": "N-1", "servers": [...]}
        # Only match if it has top-level "servers" and no "nodes" field
        if normalize_name(hub_entry.get("hub", "")) == hub_name and "servers" in hub_entry and "nodes" not in hub_entry:
            if node_name is None or normalize_name(hub_entry.get("node", "")) == normalize_name(node_name):
                return hub_entry.get("servers", [])
        
        # Hub-2/3/4 style: {"hub": "Hub-2", "nodes": [{"node": "N-1", "servers": [...]}, ...]}
        if normalize_name(hub_entry.get("hub", "")) == hub_name and "nodes" in hub_entry:
            target_node = normalize_name(node_name or "N-1")
            for node in hub_entry["nodes"]:
                if normalize_name(node.get("node", "N-1")) == target_node:
                    return node.get("servers", [])
        
        # Hub-5/6 style: {"Hub-5": {"N-1": {"apps": [...], "engines": [...]}}}
        # Check both with and without dash
        hub_key_with_dash = hub_name
        hub_key_no_dash = hub_name.replace('-', '')
        hub_key = None
        if hub_key_with_dash in hub_entry:
            hub_key = hub_key_with_dash
        elif hub_key_no_dash in hub_entry:
            hub_key = hub_key_no_dash
        
        if hub_key:
            target_node = normalize_name(node_name or "N-1")
            node_data = hub_entry[hub_key].get(target_node, {})
            
            # Convert Hub-5/6 format to standard servers format
            servers = []
            # Apps
            for app in node_data.get("apps", []):
                servers.append({"app": app["type"], "alias": app["alias"], "ip": app["ip"]})
            # Engines
            for engine in node_data.get("engines", []):
                servers.append({
                    "app": "Engine",
                    "alias": engine["alias"],
                    "ip": engine["engine_ip"],
                    "connector": {"alias": engine.get("connector_alias", ""), "ip": engine["connector_ip"]}
                })
            return servers
    
    return []

def search_ip_alias(query):
    """Search IP or alias across ALL servers, connectors, and databases"""
    query_lower = query.lower()
    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', query)
    search_ip = ip_match.group(0) if ip_match else None
    
    results = []
    
    for hub_entry in hubs_data["hubs"]:
        hub_name = hub_entry.get("hub") or list(hub_entry.keys())[0]
        
        # Check database IPs first
        db_data = None
        node_name = None
        
        # Hub-1 style
        if "servers" in hub_entry and "nodes" not in hub_entry:
            all_servers = hub_entry["servers"]
            node_name = hub_entry.get("node", "N-1")
            db_data = hub_entry.get("db", {})
            
            # Check database IPs for Hub-1
            if search_ip and db_data:
                for db_key, db_ip in db_data.items():
                    if isinstance(db_ip, str) and search_ip == db_ip:
                        results.append({
                            "hub": hub_name,
                            "node": node_name,
                            "app": "Database",
                            "alias": db_key.replace("_", " ").title(),
                            "ip": db_ip,
                            "conn_ip": "",
                            "conn_alias": ""
                        })
            
            # Check servers for Hub-1
            for server in all_servers:
                alias = server.get("alias", "").lower()
                ip = server.get("ip", "")
                conn = server.get("connector", {})
                conn_ip = conn.get("ip", "")
                conn_alias = conn.get("alias", "").lower()
                
                if (query_lower in alias or 
                    query_lower in conn_alias or
                    (search_ip and (search_ip == ip or search_ip == conn_ip))):
                    
                    results.append({
                        "hub": hub_name,
                        "node": node_name,
                        "app": server.get("app", ""),
                        "alias": server["alias"],
                        "ip": ip,
                        "conn_ip": conn_ip,
                        "conn_alias": conn.get("alias", "")
                    })
        # Hub-2/3/4 style  
        elif "nodes" in hub_entry:
            for node in hub_entry["nodes"]:
                all_servers = node.get("servers", [])
                node_name = node.get("node", "N-1")
                db_data = node.get("db", {})
                
                # Check database IPs for this node
                if search_ip and db_data:
                    for db_key, db_ip in db_data.items():
                        if isinstance(db_ip, str) and search_ip == db_ip:
                            results.append({
                                "hub": hub_name,
                                "node": node_name,
                                "app": "Database",
                                "alias": db_key.replace("_", " ").title(),
                                "ip": db_ip,
                                "conn_ip": "",
                                "conn_alias": ""
                            })
                
                # Check servers for this node
                for server in all_servers:
                    alias = server.get("alias", "").lower()
                    ip = server.get("ip", "")
                    conn = server.get("connector", {})
                    conn_ip = conn.get("ip", "")
                    conn_alias = conn.get("alias", "").lower()
                    
                    if (query_lower in alias or 
                        query_lower in conn_alias or
                        (search_ip and (search_ip == ip or search_ip == conn_ip))):
                        
                        results.append({
                            "hub": hub_name,
                            "node": node_name,
                            "app": server.get("app", ""),
                            "alias": server["alias"],
                            "ip": ip,
                            "conn_ip": conn_ip,
                            "conn_alias": conn.get("alias", "")
                        })
        # Hub-5/6 style: {"Hub-5": {"N-1": {"apps": [...], "engines": [...], "database": {...}}}}
        else:
            # This is Hub-5/6 format
            for hub_key, nodes_data in hub_entry.items():
                if isinstance(nodes_data, dict):
                    hub_name = hub_key
                    for node_key, node_data in nodes_data.items():
                        node_name = node_key
                        
                        # Check database IPs
                        db_data = node_data.get("database", {})
                        if search_ip and db_data:
                            for db_key, db_ip in db_data.items():
                                if isinstance(db_ip, str) and search_ip == db_ip:
                                    results.append({
                                        "hub": hub_name,
                                        "node": node_name,
                                        "app": "Database",
                                        "alias": db_key.replace("_", " ").title(),
                                        "ip": db_ip,
                                        "conn_ip": "",
                                        "conn_alias": ""
                                    })
                        
                        # Process apps
                        for app in node_data.get("apps", []):
                            alias = app.get("alias", "").lower()
                            ip = app.get("ip", "")
                            
                            if (query_lower in alias or (search_ip and search_ip == ip)):
                                results.append({
                                    "hub": hub_name,
                                    "node": node_name,
                                    "app": app.get("type", ""),
                                    "alias": app["alias"],
                                    "ip": ip,
                                    "conn_ip": "",
                                    "conn_alias": ""
                                })
                        
                        # Process engines
                        for engine in node_data.get("engines", []):
                            alias = engine.get("alias", "").lower()
                            engine_ip = engine.get("engine_ip", "")
                            conn_ip = engine.get("connector_ip", "")
                            conn_alias = engine.get("connector_alias", "").lower()
                            
                            if (query_lower in alias or 
                                query_lower in conn_alias or
                                (search_ip and (search_ip == engine_ip or search_ip == conn_ip))):
                                
                                results.append({
                                    "hub": hub_name,
                                    "node": node_name,
                                    "app": "Engine",
                                    "alias": engine["alias"],
                                    "ip": engine_ip,
                                    "conn_ip": conn_ip,
                                    "conn_alias": engine.get("connector_alias", "")
                                })
    
    return results

def format_server_list(servers, hub_name, node_name="", connectors_only=False):
    """Format servers beautifully"""
    if not servers:
        return []
    
    lines = []
    for server in servers:
        app = server.get("app", "")
        alias = server["alias"]
        ip = server["ip"]
        
        if "Engine" in app:
            conn = server.get("connector", {})
            conn_ip = conn.get("ip", "N/A")
            conn_alias = conn.get("alias", "")
            
            if connectors_only:
                # Show only connector info
                lines.append(f"🔌 `{conn_alias}` → `{conn_ip}`")
            else:
                # Show engine with connector
                lines.append(f"🔧 `{alias}` → `{ip}`\n   🔌 `{conn_ip}` ({conn_alias})")
        else:
            if not connectors_only:
                lines.append(f"🌐 `{alias}` → `{ip}`")
    
    return lines

def handle_query(text):
    text = text.strip()
    text_lower = text.lower()
    
    # 1. IP/Alias search FIRST
    results = search_ip_alias(text)
    if results:
        output = []
        for r in results:
            if r["app"] == "Database":
                output.append(
                    f"🎯 *{r['hub']} {r['node']}*\n"
                    f"💾 *Database* `{r['alias']}` → `{r['ip']}`"
                )
            elif r["conn_ip"]:
                output.append(
                    f"🎯 *{r['hub']} {r['node']}*\n"
                    f"🔧 *{r['app']}* `{r['alias']}`\n"
                    f"💻 `{r['ip']}`\n"
                    f"🔌 `{r['conn_ip']}` ({r['conn_alias']})"
                )
            else:
                output.append(
                    f"🎯 *{r['hub']} {r['node']}*\n"
                    f"🌐 *{r['app']}* `{r['alias']}` → `{r['ip']}`"
                )
        return "\n\n".join(output)
    
    # 2. Extract hub/node
    hub_match = re.search(r'(hub[-\s]*\d+)', text_lower)
    node_match = re.search(r'(n[-\s]*\d+)', text_lower)
    
    hub_name = normalize_name(hub_match.group(1)) if hub_match else None
    node_name = normalize_name(node_match.group(1)) if node_match else None
    
    # 3. Hub/Node servers list
    if hub_name:
        servers = find_servers(hub_name, node_name)
        connectors_only = 'connector' in text_lower
        if any(word in text_lower for word in ['engine', 'server', 'connector', 'list', 'name']):
            lines = format_server_list(servers, hub_name, node_name, connectors_only=connectors_only)
            if lines:
                header = f"🔌 *{hub_name} {node_name or 'All'} Connectors*" if connectors_only else f"🔧 *{hub_name} {node_name or 'All'}*"
                return f"{header}\n\n" + "\n".join(lines)
            return f"❌ No servers in *{hub_name}* {node_name or ''}"
    
    # 4. List hubs
    if 'hub' in text_lower and 'list' in text_lower:
        hubs = sorted(set(h.get("hub") or list(h.keys())[0] for h in hubs_data["hubs"]))
        return f"🏠 *Hubs:*\n`{', '.join(hubs)}`"
    
    # 5. Help
    return (
        "🤖 *HubBot*\n\n"
        "🔍 `10.222.197.214` | `h3pc1`\n\n"
        "📋 `Hub3 N1 connectors` | `Hub-2 N-2`"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *HubBot*\n\n`Hub3 N1 connectors` | `10.222.197.214`",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = handle_query(update.message.text)
    await update.message.reply_text(response, parse_mode='Markdown')

def create_app():
    """Create and configure the bot application"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return application

# Global bot application instance
bot_app = None

# Health check endpoint
async def health_check(request):
    """Health check endpoint for Render"""
    return web.Response(text="Bot is running")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    bot_app = create_app()
    
    # Check if we're in production (Render) or development
    PORT = os.getenv("PORT")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    
    if PORT:
        # Production mode: Use webhook with web server
        logging.info(f"Starting in webhook mode on port {PORT}")
        
        # Create webhook handler
        async def webhook_handler(request):
            """Handle incoming webhook requests"""
            if request.method == "POST":
                try:
                    data = await request.json()
                    update = Update.de_json(data, bot_app.bot)
                    await bot_app.process_update(update)
                except Exception as e:
                    logging.error(f"Error processing webhook: {e}")
            return web.Response(text="OK")
        
        # Set webhook on startup
        async def post_init(app):
            if WEBHOOK_URL:
                webhook_path = f"{WEBHOOK_URL}/webhook"
                await bot_app.bot.set_webhook(url=webhook_path)
                logging.info(f"Webhook set to {webhook_path}")
            else:
                logging.warning("WEBHOOK_URL not set, webhook not configured")
        
        # Create web application
        web_app = web.Application()
        web_app.router.add_post("/webhook", webhook_handler)
        web_app.router.add_get("/health", health_check)
        web_app.router.add_get("/", health_check)
        web_app.on_startup.append(post_init)
        
        # Start web server
        logging.info(f"Starting web server on port {PORT}")
        web.run_app(web_app, port=int(PORT), host="0.0.0.0")
    else:
        # Development mode: Use polling
        logging.info("Starting in polling mode (development)")
        bot_app.run_polling()
