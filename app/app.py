import os
import json
from datetime import datetime
from flask import Flask, render_template, jsonify
from composio import ComposioToolSet

app = Flask(__name__)

# Account configurations
ACCOUNTS = {
    "dailyhealthai5": {
        "name": "Daily Health ai",
        "username": "dailyhealthai5",
        "account_id": "28401662522860447",
        "connection_id": "instagram_ninth-flak",
        "alias": "Dailyhealth",
        "icon": "👩",
        "drive_folder_id": "1rOyJGRBiVbWiG_-BNX4cOZLJmTodPQfx"
    },
    "aihulkureels": {
        "name": "Hulku Re",
        "username": "aihulkureels",
        "account_id": "27927888190222835",
        "connection_id": "instagram_bated-leant",
        "alias": "hulku",
        "icon": "🤔",
        "drive_folder_id": "17T3KvIZU6N-RgsNLUomVpcBV-PGgmV6v"
    },
    "miniaturebuilds": {
        "name": "Miniature Builds",
        "username": "miniaturebuilds.ai",
        "account_id": "38343581375256884",
        "connection_id": "instagram_bolk-reflex",
        "alias": "miniature",
        "icon": "🔬",
        "drive_folder_id": "1zb8LieBL4AZaT7wXw3il9Ch8t8thFIK_",
        "subfolders": [
            {"name": "CHEF REELS", "id": "1xZBnOtx-vkq6eevEi-YRUsya5D_wJtV1"},
            {"name": "MINITURE REELS", "id": "1BurBteBA37OrEeCNCJMooQM5B6KL9lMR"},
            {"name": "MAKEUP REELS", "id": "1ViJwUdwoG4l_aIHF_lnsGuZDOxNqL1SI"},
            {"name": "EXTRA 1", "id": "10RAVbcma2xYxa5XQFzEVAQmTg0Urlpav"},
            {"name": "EXTRA 2", "id": "1zfPiwaIgXqg5wzYGP7rax8GufSLEkv3z"}
        ]
    }
}

# Cache for data
cache = {
    "data": None,
    "last_fetch": None
}

CACHE_DURATION = 300  # 5 minutes

def fetch_live_data():
    """Fetch live data from Instagram and Google Drive via Composio"""
    try:
        toolset = ComposioToolSet(api_key=os.environ.get("COMPOSIO_API_KEY"))
        
        accounts_data = {}
        
        for key, config in ACCOUNTS.items():
            account_info = {
                "name": config["name"],
                "username": config["username"],
                "accountId": config["account_id"],
                "alias": config["alias"],
                "icon": config["icon"],
                "driveFolderId": config["drive_folder_id"],
                "followers": 0,
                "reach": 0,
                "mediaCount": 0,
                "driveVideos": 0,
                "latestPost": None,
                "subfolders": config.get("subfolders")
            }
            
            # Fetch Instagram user info
            try:
                result = toolset.execute_action(
                    action="INSTAGRAM_GET_USER_INFO",
                    params={"ig_user_id": config["account_id"]},
                    connected_account_id=config["connection_id"]
                )
                if result.get("data"):
                    data = result["data"]
                    account_info["followers"] = data.get("followers_count", 0) or 0
                    account_info["mediaCount"] = data.get("media_count", 0) or 0
            except Exception as e:
                print(f"Error fetching Instagram info for {key}: {e}")
            
            # Fetch Instagram insights
            try:
                result = toolset.execute_action(
                    action="INSTAGRAM_GET_USER_INSIGHTS",
                    params={
                        "ig_user_id": config["account_id"],
                        "metric": ["reach", "profile_views"],
                        "period": "day"
                    },
                    connected_account_id=config["connection_id"]
                )
                if result.get("data") and result["data"].get("data"):
                    for metric in result["data"]["data"]:
                        if metric.get("name") == "reach":
                            values = metric.get("values", [])
                            if values:
                                account_info["reach"] = values[-1].get("value", 0)
            except Exception as e:
                print(f"Error fetching Instagram insights for {key}: {e}")
            
            # Fetch Google Drive videos
            try:
                query = f"'{config['drive_folder_id']}' in parents and mimeType contains 'video'"
                result = toolset.execute_action(
                    action="GOOGLEDRIVE_LIST_FILES",
                    params={
                        "q": query,
                        "fields": "files(id,name)",
                        "pageSize": 100
                    }
                )
                if result.get("data") and result["data"].get("files"):
                    account_info["driveVideos"] = len(result["data"]["files"])
            except Exception as e:
                print(f"Error fetching Google Drive for {key}: {e}")
            
            accounts_data[key] = account_info
        
        return {
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "accounts": accounts_data,
            "postingLog": []
        }
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def get_data():
    """Get data with caching"""
    now = datetime.utcnow()
    
    if cache["data"] and cache["last_fetch"]:
        elapsed = (now - cache["last_fetch"]).total_seconds()
        if elapsed < CACHE_DURATION:
            return cache["data"]
    
    # Fetch fresh data
    data = fetch_live_data()
    if data:
        cache["data"] = data
        cache["last_fetch"] = now
        return data
    
    # Return cached data if fetch fails
    return cache["data"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    data = get_data()
    if data:
        return jsonify(data)
    return jsonify({"error": "Failed to fetch data"}), 500

@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Force refresh data"""
    cache["last_fetch"] = None
    data = get_data()
    if data:
        return jsonify({"status": "ok", "lastUpdated": data["lastUpdated"]})
    return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)