import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BRANDDEO_SERVER_ID = os.environ.get("BRANDDEO_SERVER_ID", "1462786676983332866")
API_KEY = os.environ.get("API_KEY", "branddeo2024")

BASE_URL = "https://discord.com/api/v10"
HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}


def check_api_key():
    key = request.headers.get("X-API-Key") or request.args.get("key")
    if key != API_KEY:
        return False
    return True


def discord_get(endpoint):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS)
        if r.status_code == 200:
            return r.json()
        return {"error": r.status_code, "message": r.text[:500]}
    except Exception as e:
        return {"error": str(e)}


def discord_post(endpoint, data):
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", headers=HEADERS, json=data)
        if r.status_code in [200, 201, 204]:
            return r.json() if r.text else {"success": True}
        return {"error": r.status_code, "message": r.text[:500]}
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def home():
    return jsonify({"status": "ok", "bot": "Branddeo Assistant", "version": "1.0"})


@app.route("/channels")
def get_channels():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}/channels")
    if isinstance(data, list):
        categories = {}
        text_channels = []
        for ch in data:
            if ch["type"] == 4:
                categories[ch["id"]] = ch["name"]
            elif ch["type"] == 0:
                text_channels.append({"id": ch["id"], "name": ch["name"], "category": categories.get(ch.get("parent_id"), "Sans categorie"), "position": ch.get("position", 0)})
        text_channels.sort(key=lambda x: x["position"])
        return jsonify({"channels": text_channels})
    return jsonify(data)


@app.route("/members")
def get_members():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}/members?limit=100")
    if isinstance(data, list):
        members = []
        for m in data:
            user = m.get("user", {})
            members.append({"id": user.get("id"), "username": user.get("username"), "global_name": user.get("global_name"), "nick": m.get("nick"), "display": m.get("nick") or user.get("global_name") or user.get("username"), "bot": user.get("bot", False)})
        return jsonify({"members": members})
    return jsonify(data)


@app.route("/messages/<channel_id>")
def get_messages(channel_id):
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    limit = request.args.get("limit", 10, type=int)
    data = discord_get(f"/channels/{channel_id}/messages?limit={limit}")
    if isinstance(data, list):
        messages = []
        for msg in reversed(data):
            author = msg.get("author", {})
            content = msg.get("content", "")
            for mention in msg.get("mentions", []):
                mid = mention.get("id", "")
                mname = mention.get("global_name") or mention.get("username", "")
                content = content.replace(f"<@{mid}>", f"@{mname}")
                content = content.replace(f"<@!{mid}>", f"@{mname}")
            messages.append({"id": msg.get("id"), "author": author.get("global_name") or author.get("username", "???"), "author_bot": author.get("bot", False), "content": content, "timestamp": msg.get("timestamp", "")[:16].replace("T", " ")})
        return jsonify({"messages": messages})
    return jsonify(data)


@app.route("/send", methods=["POST"])
def send_message():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    body = request.json
    channel_id = body.get("channel_id")
    content = body.get("content", "")
    if not channel_id:
        return jsonify({"error": "channel_id required"}), 400
    result = discord_post(f"/channels/{channel_id}/messages", {"content": content})
    return jsonify(result)


@app.route("/send-mention", methods=["POST"])
def send_with_mention():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    body = request.json
    channel_id = body.get("channel_id")
    user_name = body.get("user_name", "")
    message = body.get("message", "")
    if not channel_id:
        return jsonify({"error": "channel_id required"}), 400
    members_data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}/members?limit=100")
    user_id = None
    if isinstance(members_data, list):
        for m in members_data:
            user = m.get("user", {})
            nick = m.get("nick", "") or ""
            username = user.get("username", "")
            global_name = user.get("global_name", "") or ""
            if (user_name.lower() in username.lower() or user_name.lower() in global_name.lower() or user_name.lower() in nick.lower()):
                user_id = user["id"]
                break
    if user_id:
        content = f"<@{user_id}> {message}"
        result = discord_post(f"/channels/{channel_id}/messages", {"content": content})
        return jsonify(result)
    return jsonify({"error": f"User not found: {user_name}"}), 404


@app.route("/overview")
def server_overview():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    channels_data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}/channels")
    members_data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}/members?limit=100")
    guild_data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}")
    result = {"server": guild_data.get("name", "Branddeo") if isinstance(guild_data, dict) else "Branddeo"}
    if isinstance(members_data, list):
        humans = [m for m in members_data if not m.get("user", {}).get("bot")]
        bots = [m for m in members_data if m.get("user", {}).get("bot")]
        result["members"] = {"humans": len(humans), "bots": len(bots)}
        result["human_list"] = [m.get("nick") or m.get("user", {}).get("global_name") or m.get("user", {}).get("username") for m in humans]
    if isinstance(channels_data, list):
        categories = {}
        text_channels = []
        for ch in channels_data:
            if ch["type"] == 4:
                categories[ch["id"]] = ch["name"]
            elif ch["type"] == 0:
                text_channels.append(ch)
        result["channels_count"] = len(text_channels)
        activity = []
        for ch in sorted(text_channels, key=lambda x: x.get("position", 0)):
            msgs = discord_get(f"/channels/{ch['id']}/messages?limit=1")
            if isinstance(msgs, list) and msgs:
                last = msgs[0]
                author = last.get("author", {})
                activity.append({"channel": ch["name"], "category": categories.get(ch.get("parent_id"), ""), "last_author": author.get("global_name") or author.get("username", ""), "last_message": last.get("content", "")[:100], "timestamp": last.get("timestamp", "")[:16].replace("T", " ")})
        result["activity"] = activity
    return jsonify(result)


@app.route("/all-messages")
def read_all_channels():
    if not check_api_key():
        return jsonify({"error": "unauthorized"}), 401
    limit = request.args.get("limit", 5, type=int)
    channels_data = discord_get(f"/guilds/{BRANDDEO_SERVER_ID}/channels")
    if not isinstance(channels_data, list):
        return jsonify(channels_data)
    categories = {}
    text_channels = []
    for ch in channels_data:
        if ch["type"] == 4:
            categories[ch["id"]] = ch["name"]
        elif ch["type"] == 0:
            text_channels.append(ch)
    all_msgs = []
    for ch in sorted(text_channels, key=lambda x: x.get("position", 0)):
        msgs = discord_get(f"/channels/{ch['id']}/messages?limit={limit}")
        if isinstance(msgs, list) and msgs:
            channel_msgs = []
            for msg in reversed(msgs):
                author = msg.get("author", {})
                content = msg.get("content", "")
                for mention in msg.get("mentions", []):
                    mid = mention.get("id", "")
                    mname = mention.get("global_name") or mention.get("username", "")
                    content = content.replace(f"<@{mid}>", f"@{mname}")
                    content = content.replace(f"<@!{mid}>", f"@{mname}")
                channel_msgs.append({"author": author.get("global_name") or author.get("username", "???"), "content": content[:200], "timestamp": msg.get("timestamp", "")[:16].replace("T", " ")})
            all_msgs.append({"channel": ch["name"], "category": categories.get(ch.get("parent_id"), ""), "messages": channel_msgs})
    return jsonify({"channels": all_msgs})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
