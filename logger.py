import os
import json
import time
import requests
from dotenv import load_dotenv
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright
import ast
import tweepy

# This script logs data for specified user profiles from sent.bio.
# It uses a hybrid approach, fetching data from public APIs and using Playwright
# for data only accessible via the frontend. It also includes a mechanism to
# automatically post tweets when specific wishlist fundraising goals reach new milestones.

load_dotenv()

# --- Configuration ---
PROFILES_TO_TRACK = [
    {"username": "alquis", "uid": "it54UEAVGkdEcRJLthGuidZHObp2", "has_detailed_leaderboard": False},
    {"username": "gnnx", "uid": "FN70NUv8JFQvEUUre5odEeQny3m2", "has_detailed_leaderboard": False},
    {"username": "brattyxmeri", "uid": "cSPu7EY8Q7XeSO3pdFX8GdkwLRY2", "has_detailed_leaderboard": True},
    {"username": "fairybrat", "uid": "AUOYyApWAKTYOqHTOSMW80WgZT02", "has_detailed_leaderboard": False},
    {"username": "digitalvicc", "uid": "BlTp70OXxTMjZMG4BRI4qs8V3L13", "has_detailed_leaderboard": False}
]
CLICK_COORDS = {"x": 790, "y": 371}
STATE_FILE_TEMPLATE = "{username}_state.json"
LOG_FOLDER = "data_logs"
WISHLIST_API_URL = "https://firestore.googleapis.com/v1/projects/sent-wc254r/databases/(default)/documents/wishlists?pageSize=300"
LEADERBOARD_API_URL = "https://us-central1-sent-wc254r.cloudfunctions.net/fetchLeaderboardPosition"

# --- Configuration for Automated Tweets ---
# This dictionary defines which wishlist items trigger tweets for which user.
TWEET_CONFIG = {
    "alquis": {
        "to talk": {
            "threshold": 50,
            "message": "Keira the greedy predator @alquis13 got sent $50 'to talk' at {est_time} EST #abuser"
        },
        "autotweet minimum": {
            "threshold": 100,
            "message": "Keira the greedy predator @alquis13 got sent $100 'autotweet minimum' at {est_time} EST #abuser"
        }
    }
}


captured_console_data = {}

# --- Helper Functions ---

def post_to_twitter(message):
    """Posts a message to Twitter using credentials from environment variables."""
    # Check if credentials are set, if not, just print and simulate success for local testing
    if not all(k in os.environ for k in ['TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_TOKEN_SECRET']):
        print("\n--- TWITTER SIMULATION MODE ---")
        print("Twitter API credentials not found in environment variables.")
        print(f"Would have tweeted: \"{message}\"")
        print("-------------------------------\n")
        return True # Return True to allow the script to continue locally without keys

    try:
        client = tweepy.Client(
            consumer_key=os.environ['TWITTER_API_KEY'],
            consumer_secret=os.environ['TWITTER_API_SECRET'],
            access_token=os.environ['TWITTER_ACCESS_TOKEN'],
            access_token_secret=os.environ['TWITTER_ACCESS_TOKEN_SECRET']
        )
        response = client.create_tweet(text=message)
        print(f"SUCCESS: Tweet posted! ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to post tweet: {e}")
        return False

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

def get_leaderboard_data(uid):
    """Fetches the leaderboard data for a specific user."""
    print(f"Fetching leaderboard data for UID: {uid}...")
    try:
        payload = {"data": {"uid": uid}}
        headers = {"Content-Type": "application/json"}
        response = requests.post(LEADERBOARD_API_URL, headers=headers, json=payload, timeout=15)
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

def handle_console_message(msg):
    global captured_console_data
    text = msg.text.strip()

    def parse_js_object_string(js_str):
        py_str = js_str.replace('null', 'None').replace('true', 'True').replace('false', 'False')
        py_str = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)', r"'\1'", py_str)
        py_str = py_str.replace("'None'", "None").replace("'True'", "True").replace("'False'", "False")
        py_str = py_str.replace('$', "'$'").replace('€', "'€'").replace('£', "'£'")
        return ast.literal_eval(py_str)

    if text.startswith("recentSends response:"):
        print("  [Console Capture] Found Recent Sends data!")
        js_object_str = text.replace("recentSends response: ", "")
        try:
            sends = parse_js_object_string(js_object_str)
            formatted_sends = []
            for s in sends:
                formatted_sends.append({
                    "sender": s.get("sender_name", "Unknown"),
                    "amount": f"{s.get('sender_currency_symbol', '$')}{s.get('amount', 0)}"
                })
            captured_console_data["recent_sends"] = formatted_sends
            print("  [Console Capture] SUCCESS: Successfully parsed recent sends.")
        except Exception as e:
            print(f"  [Console Capture] ERROR: Could not parse recent sends: {e}")
        return

    if text.startswith("fetchLeaderboard response:"):
        print("  [Console Capture] Found RICH Leaderboard response!")
        js_object_str = text.replace("fetchLeaderboard response: ", "")
        try:
            cleaned_str = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', js_object_str)
            cleaned_str = re.sub(r':\s*([a-zA-Z_]+)', r': "\1"', cleaned_str)
            cleaned_str = re.sub(r':\s*(\d+(st|nd|rd|th))', r': "\1"', cleaned_str)
            cleaned_str = cleaned_str.replace(': "null"', ': null')
            cleaned_str = cleaned_str.replace(': "true"', ': true')
            cleaned_str = cleaned_str.replace(': "false"', ': false')
            captured_console_data["leaderboard_detailed"] = json.loads(cleaned_str)
            print("  [Console Capture] SUCCESS: Successfully parsed rich leaderboard.")
        except Exception as e:
            print(f"  [Console Capture] ERROR: Could not parse rich leaderboard: {e}")
        return

    if re.fullmatch(r'\d+(st|nd|rd|th)', text):
        if "simple_leaderboard" not in captured_console_data: captured_console_data["simple_leaderboard"] = {}
        captured_console_data["simple_leaderboard"]["position"] = text
        return

    try:
        value = float(text)
        if value >= 0:
            if "simple_leaderboard" not in captured_console_data: captured_console_data["simple_leaderboard"] = {}
            captured_console_data["simple_leaderboard"]["score"] = value
    except ValueError:
        pass

def get_data_from_console_via_playwright(username, should_click_leaderboard):
    global captured_console_data
    captured_console_data = {}
    print(f"Launching robot browser for {username} to get console data...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 720})
            page.on("console", handle_console_message)

            print(f"  Navigating to https://sent.bio/{username}...")
            page.goto(f"https://sent.bio/{username}", wait_until="load", timeout=45000)
            print("  Waiting for app container...")
            page.locator("flutter-view").wait_for(state='attached', timeout=30000)
            print("  Waiting 5 seconds for dynamic content to load...")
            page.wait_for_timeout(5000)

            if should_click_leaderboard:
                try:
                    print(f"  Profile flagged for click. Clicking coordinates: X={CLICK_COORDS['x']}, Y={CLICK_COORDS['y']}")
                    with page.expect_console_message(lambda msg: "fetchLeaderboard response:" in msg.text, timeout=10000):
                        page.mouse.click(CLICK_COORDS['x'], CLICK_COORDS['y'])
                    print("  Successfully clicked and detected leaderboard response.")
                except Exception as click_error:
                    print(f"  Warning: Did not see the rich leaderboard response after clicking: {click_error}")

            print("  Waiting 2 seconds for streams to finalize...")
            page.wait_for_timeout(2000)
            browser.close()
            return captured_console_data
    except Exception as e:
        print(f"An error occurred during browser automation for {username}: {e}")
        return {}

def read_state(username):
    state_file = STATE_FILE_TEMPLATE.format(username=username)
    if not os.path.exists(state_file): return {}
    with open(state_file, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return {}

def write_state(username, data):
    state_file = STATE_FILE_TEMPLATE.format(username=username)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Ultimate Hybrid Data Logger v5.0 with Tweeting...")

    full_wishlist_data = get_all_wishlist_data()
    if not full_wishlist_data:
        print("Could not fetch wishlist data. Aborting.")
        exit()
        
    now_est_str = datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M")
    
    has_alquis_wishlist_changed = False

    for profile in PROFILES_TO_TRACK:
        username = profile["username"]
        uid = profile["uid"]
        should_click = profile.get("has_detailed_leaderboard", False)

        print(f"\n--- Processing Profile: {username} ---")

        previous_state = read_state(username)
        wishlist = parse_and_filter_wishlists(full_wishlist_data, uid)
        api_leaderboard_data = get_leaderboard_data(uid)
        console_data = get_data_from_console_via_playwright(username, should_click)

        current_state = {
            "wishlist": wishlist,
            "leaderboard_simple_api": api_leaderboard_data,
            "leaderboard_simple": console_data.get("simple_leaderboard", {}),
            "leaderboard_detailed": console_data.get("leaderboard_detailed", {}),
            "recent_sends": console_data.get("recent_sends", [])
        }

        print("--- Parsed Data ---")
        print(json.dumps(current_state, indent=2))
        
        if current_state != previous_state:
            print(f"\nChange detected for {username}! Updating state file.")
            write_state(username, current_state)
            print(f"SUCCESS: State file '{username}_state.json' updated.")

            # --- Check for tweetable milestone changes for the specific user ---
            if username in TWEET_CONFIG:
                print(f"Found tweet configuration for '{username}'. Checking for milestones...")
                user_tweet_config = TWEET_CONFIG[username]
                previous_wishlist = previous_state.get("wishlist", {})
                current_wishlist = current_state.get("wishlist", {})

                for item_name, config in user_tweet_config.items():
                    prev_val = previous_wishlist.get(item_name, 0.0)
                    curr_val = current_wishlist.get(item_name, 0.0)
                    threshold = config["threshold"]

                    if curr_val > prev_val: # Only proceed if value has increased
                        # Using integer division to see how many thresholds were crossed
                        prev_milestones = int(prev_val // threshold)
                        curr_milestones = int(curr_val // threshold)
                        
                        num_new_tweets = curr_milestones - prev_milestones

                        if num_new_tweets > 0:
                            print(f"  MILESTONE REACHED for '{item_name}'! Change from ${prev_val:.2f} to ${curr_val:.2f}. Need to send {num_new_tweets} tweet(s).")
                            # Send a tweet for each milestone crossed
                            for i in range(num_new_tweets):
                                message = config["message"].format(
                                    threshold=threshold,
                                    total_funded=curr_val,
                                    est_time=now_est_str 
                                )
                                post_to_twitter(message)
                                time.sleep(2)
            
            # This logic for the log file also remains the same
            if username == "alquis":
                previous_alquis_wishlist = previous_state.get("wishlist", {})
                current_alquis_wishlist = current_state.get("wishlist", {})
                if previous_alquis_wishlist.get("to talk") != current_alquis_wishlist.get("to talk"):
                    has_alquis_wishlist_changed = True
                if previous_alquis_wishlist.get("autotweet minimum") != current_alquis_wishlist.get("autotweet minimum"):
                    has_alquis_wishlist_changed = True
        else:
            print(f"\nNo changes detected for {username}.")

    if has_alquis_wishlist_changed:
        print("\n--- Alquis' specified wishlist items changed! Saving a new combined data log. ---")
        if not os.path.exists(LOG_FOLDER): os.makedirs(LOG_FOLDER)
        now = datetime.now(ZoneInfo("America/New_York"))
        alquis_current_state_for_log = read_state("alquis")
        filename = f"alquis_wishlist_update_{now.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        filepath = os.path.join(LOG_FOLDER, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(alquis_current_state_for_log, f, indent=2)
        print(f"SUCCESS: New data log for alquis' wishlist update saved to '{filepath}'")
    else:
        print("\nAlquis' specified wishlist items did not change, no new log file created.")