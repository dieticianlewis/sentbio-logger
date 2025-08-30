import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# --- Configuration ---
# You can add more users here if you find their UIDs
PROFILES_TO_TRACK = [
    {
        "username": "alquis",
        "uid": "it54UEAVGkdEcRJLthGuidZHObp2"
    },
    {
        "username": "gnnx",
        "uid": "FN70NUv8JFQvEUUre5odEeQny3m2"
    }
]

STATE_FILE = "current_state.json"
LOG_FOLDER = "data_logs"
WISHLIST_API_URL = "https://firestore.googleapis.com/v1/projects/sent-wc254r/databases/(default)/documents/wishlists?pageSize=300"
LEADERBOARD_API_URL = "https://us-central1-sent-wc254r.cloudfunctions.net/fetchLeaderboardPosition"

# --- Data Fetching and Parsing Functions ---

def get_all_wishlist_data():
    """Fetches the entire public wishlist collection."""
    print("Fetching all wishlist data from public API...")
    try:
        response = requests.get(WISHLIST_API_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching wishlist API: {e}")
        return None

def get_leaderboard_data(uid):
    """Fetches the leaderboard data for a specific user."""
    print(f"Fetching leaderboard data for UID: {uid}...")
    try:
        payload = {"data": {"uid": uid}}
        response = requests.post(LEADERBOARD_API_URL, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json().get("result", {})
        return {
            "position": data.get("place"),
            "amount_away": data.get("amountAway")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching leaderboard API: {e}")
        return None

def parse_and_filter_wishlists(api_data, target_uid):
    """Parses the full API response and extracts the wishlist for a single user."""
    user_wishlist = {}
    documents = api_data.get("documents", [])
    for doc in documents:
        fields = doc.get("fields", {})
        owner_uid = fields.get("owner", {}).get("stringValue")
        if owner_uid == target_uid:
            title = fields.get("title", {}).get("stringValue")
            funded_obj = fields.get("funded", {})
            funded = funded_obj.get("doubleValue") or funded_obj.get("integerValue")
            if title and funded is not None:
                user_wishlist[title] = float(funded)
    return user_wishlist

# --- Main Logic ---

if __name__ == "__main__":
    print("Starting data logger...")
    
    # Read the last known state from our memory file
    previous_state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            previous_state = json.load(f)

    # Fetch all the raw data needed
    full_wishlist_data = get_all_wishlist_data()
    if not full_wishlist_data:
        print("Could not fetch wishlist data. Aborting.")
        exit()

    # Build the new, current state object
    current_state = {}
    for profile in PROFILES_TO_TRACK:
        username = profile["username"]
        uid = profile["uid"]
        
        wishlist = parse_and_filter_wishlists(full_wishlist_data, uid)
        leaderboard = get_leaderboard_data(uid)
        
        current_state[username] = {
            "wishlist": wishlist,
            "leaderboard": leaderboard
        }
        print(f"Current parsed state for {username}: {current_state[username]}")

    # The most important step: Compare the new state to the old one
    if current_state != previous_state:
        print("\nChange detected! Saving new data log and updating state.")
        
        # 1. Save the new state to a timestamped log file
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
        
        now = datetime.now(ZoneInfo("America/New_York"))
        filename = now.strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        filepath = os.path.join(LOG_FOLDER, filename)
        
        with open(filepath, 'w') as f:
            json.dump(current_state, f, indent=2)
        print(f"SUCCESS: New data log saved to '{filepath}'")
        
        # 2. Overwrite the main state file to create a new baseline
        with open(STATE_FILE, 'w') as f:
            json.dump(current_state, f, indent=2)
        print(f"SUCCESS: State file '{STATE_FILE}' updated.")
    
    else:
        print("\nNo changes detected. Nothing to log.")