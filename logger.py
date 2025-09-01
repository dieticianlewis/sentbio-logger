import os
import json
import time
import requests
import tweepy
from dotenv import load_dotenv
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

load_dotenv()

# --- Configuration ---
ENABLE_TWEETING = False 

PROFILES_TO_TRACK = [
    {
        "username": "alquis",
        "uid": "it54UEAVGkdEcRJLthGuidZHObp2",
        "wishlist_tweet": "Keira's '{title}' goal received ${amount:.2f}! at {time} EST",
        "tip_tweet": "Keira also received a random tip! at {time} EST",
        "leaderboard_tweet": "Keira's leaderboard rank changed to {position}! (Score: {score:.2f}) at {time} EST"
    },
    {
        "username": "gnnx",
        "uid": "FN70NUv8JFQvEUUre5odEeQny3m2",
        "wishlist_tweet": "GNNX's '{title}' goal received ${amount:.2f}! at {time} EST",
        "tip_tweet": "GNNX also received a random tip! at {time} EST",
        "leaderboard_tweet": "GNNX's leaderboard rank changed to {position}! (Score: {score:.2f}) at {time} EST"
    },
    {
        "username": "brattyxmeri",
        "uid": "cSPu7EY8Q7XeSO3pdFX8GdkwLRY2",
        "wishlist_tweet": "brattyxmeri's '{title}' goal received ${amount:.2f}! at {time} EST",
        "tip_tweet": "brattyxmeri also received a random tip! at {time} EST",
        "leaderboard_tweet": "brattyxmeri's leaderboard rank changed to {position}! (Score: {score:.2f}) at {time} EST"
    },
    {
        "username": "fairybrat",
        "uid": "AUOYyApWAKTYOqHTOSMW80WgZT02",
        "wishlist_tweet": "fairybrat's '{title}' goal received ${amount:.2f}! at {time} EST",
        "tip_tweet": "fairybrat also received a random tip! at {time} EST",
        "leaderboard_tweet": "fairybrat's leaderboard rank changed to {position}! (Score: {score:.2f}) at {time} EST"
    },
    {
        "username": "digitalvicc",
        "uid": "BlTp70OXxTMjZMG4BRI4qs8V3L13",
        "wishlist_tweet": "digitalvicc's '{title}' goal received ${amount:.2f}! at {time} EST",
        "tip_tweet": "digitalvicc also received a random tip! at {time} EST",
        "leaderboard_tweet": "digitalvicc's leaderboard rank changed to {position}! (Score: {score:.2f}) at {time} EST"
    }
]

STATE_FILE = "current_state.json"
LOG_FOLDER = "data_logs"
WISHLIST_API_URL = "https://firestore.googleapis.com/v1/projects/sent-wc254r/databases/(default)/documents/wishlists?pageSize=300"

# Global dictionary to hold captured data for a single run
captured_data = {}

# --- Data Fetching and Parsing Functions ---

def get_all_wishlist_data():
    """Fetches the entire public wishlist collection via direct API call."""
    print("Fetching all wishlist data from public API...")
    try:
        response = requests.get(WISHLIST_API_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching wishlist API: {e}")
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

# --- THIS IS THE NEW, SMARTER PARSER ---
def handle_console_message(msg):
    """Listens to the console and captures both leaderboard position AND score."""
    global captured_data
    text = msg.text.strip()

    # Check for leaderboard position (e.g., "1st", "24th")
    if re.fullmatch(r'\d+(st|nd|rd|th)', text):
        print(f"  [Console Capture] SUCCESS: Captured leaderboard position: {text}")
        captured_data["position"] = text
        return

    # Check for leaderboard score/total (a floating point number)
    try:
        value = float(text)
        if "." in text and value > 0:
            print(f"  [Console Capture] SUCCESS: Captured leaderboard score: {value}")
            captured_data["score"] = value
    except (ValueError, TypeError):
        pass

def get_leaderboard_data_via_playwright(username):
    """Launches a browser and captures all leaderboard console data."""
    global captured_data
    captured_data = {} # Reset for each user

    print(f"Launching robot browser for {username} to get leaderboard data...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("console", handle_console_message)
            page.goto(f"https://sent.bio/{username}", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(5000)
            browser.close()
            return captured_data
    except Exception as e:
        print(f"An error occurred during browser automation for {username}: {e}")
        return {}

# --- (State and Twitter functions are unchanged) ---
def read_state():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, 'r') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return {}
def write_state(data):
    with open(STATE_FILE, 'w') as f: json.dump(data, f, indent=2)
def post_to_twitter(message):
    if not ENABLE_TWEETING:
        print(f"--- [TEST MODE] TWEET POSTED --- \n{message}\n--------------------------------")
        return True
    # Your real tweepy code here...

# --- Main Logic ---
if __name__ == "__main__":
    print("Starting Hybrid Correlation Bot...")
    all_states = read_state()
    something_was_updated = False
    now_est = datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M")

    full_wishlist_data = get_all_wishlist_data()
    if not full_wishlist_data:
        print("Could not fetch wishlist data. Aborting.")
        exit()

    current_state = {}
    for profile in PROFILES_TO_TRACK:
        username = profile["username"]
        uid = profile["uid"]
        print(f"\n--- Processing Profile: {username} ---")
        
        previous_user_state = all_states.get(username, {})
        previous_wishlist = previous_user_state.get("wishlist", {})
        previous_leaderboard = previous_user_state.get("leaderboard", {})

        current_wishlist = parse_and_filter_wishlists(full_wishlist_data, uid)
        current_leaderboard = get_leaderboard_data_via_playwright(username)
        
        current_user_state = {
            "wishlist": current_wishlist,
            "leaderboard": current_leaderboard
        }
        current_state[username] = current_user_state
        
        print(f"Parsed Wishlist: {current_wishlist}")
        print(f"Parsed Leaderboard: {current_leaderboard}")

        tweets_to_send = []
        known_increase = 0.0
        
        for title, new_funded in current_wishlist.items():
            old_funded = previous_wishlist.get(title, 0.0)
            if old_funded > 0 and new_funded > old_funded:
                contribution = new_funded - old_funded
                known_increase += contribution
                tweets_to_send.append(
                    profile["wishlist_tweet"].format(title=title, amount=contribution, time=now_est)
                )
        
        if current_leaderboard.get("score") is not None and previous_leaderboard.get("score") is not None:
            if float(current_leaderboard["score"]) > float(previous_leaderboard["score"]) and known_increase == 0.0:
                 tweets_to_send.append(
                    profile["tip_tweet"].format(time=now_est)
                )
        
        if current_leaderboard.get("position") and previous_leaderboard.get("position"):
             if current_leaderboard["position"] != previous_leaderboard["position"]:
                  tweets_to_send.append(
                    profile["leaderboard_tweet"].format(
                        position=current_leaderboard['position'], 
                        score=current_leaderboard.get('score', 0.0), 
                        time=now_est
                    )
                )

        if tweets_to_send:
            # Logic to post tweets...
            print(f"\nFound {len(tweets_to_send)} new event(s)!")
            all_succeeded = True
            for message in tweets_to_send:
                if not post_to_twitter(message):
                    all_succeeded = False; break
                time.sleep(2)
            if all_succeeded: something_was_updated = True
        else:
            print("No new events detected.")

    if current_state != all_states and something_was_updated:
        print("\nChange detected. Saving new data log and updating state.")
        if not os.path.exists(LOG_FOLDER): os.makedirs(LOG_FOLDER)
        filename = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        with open(os.path.join(LOG_FOLDER, filename), 'w') as f: json.dump(current_state, f, indent=2)
        print(f"SUCCESS: New data log saved to '{os.path.join(LOG_FOLDER, filename)}'")
        write_state(current_state)
    else:
        print("\nNo changes detected or tweets failed. State not updated.")