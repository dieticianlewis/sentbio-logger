import os
import json
import time
import requests

# --- Configuration ---
# This script is hardcoded to only track 'alquis' and specific wishlist items.
ALQUIS_UID = "it54UEAVGkdEcRJLthGuidZHObp2"
WISHLIST_ITEMS_TO_TRACK = ["ub fee", "to talk", "autotweet minimum", "breakfast"]
STATE_FILE = "alquis_wishlist.json"
WISHLIST_API_URL = "https://firestore.googleapis.com/v1/projects/sent-wc254r/databases/(default)/documents/wishlists?pageSize=300"

# --- Core Functions ---

def get_all_wishlist_data():
    """Fetches the entire public wishlist collection via a direct API call."""
    print("Fetching all wishlist data from public API...")
    try:
        response = requests.get(WISHLIST_API_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not fetch wishlist API: {e}")
        return None

def extract_alquis_wishlist(api_data):
    """
    Parses the full API response and extracts only the specified wishlist items
    for the user 'alquis'.
    """
    # Initialize all tracked items with a default value of 0.0.
    # This ensures that if an item is removed from the website, it's reflected
    # in our state file as 0.0, which counts as a change.
    alquis_wishlist = {item: 0.0 for item in WISHLIST_ITEMS_TO_TRACK}

    documents = api_data.get("documents", [])
    for doc in documents:
        fields = doc.get("fields", {})
        owner_uid = fields.get("owner", {}).get("stringValue")

        # Check if this document belongs to alquis
        if owner_uid == ALQUIS_UID:
            title = fields.get("title", {}).get("stringValue")

            # Check if this is one of the items we want to track
            if title in WISHLIST_ITEMS_TO_TRACK:
                funded_obj = fields.get("funded", {})
                # Get either the decimal ('doubleValue') or whole number ('integerValue')
                funded = funded_obj.get("doubleValue") or funded_obj.get("integerValue")

                if funded is not None:
                    alquis_wishlist[title] = float(funded)

    return alquis_wishlist

def read_previous_wishlist():
    """Reads the last saved wishlist data from the state file."""
    if not os.path.exists(STATE_FILE):
        print("State file not found. Will create a new one.")
        return {}
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("Warning: State file is corrupted. A new one will be created.")
            return {}

def write_wishlist(data):
    """Writes the current wishlist data to the state file."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

# --- Main Execution ---
if __name__ == "__main__":
    print(f"--- Starting Alquis-Only Wishlist Logger ---")
    print(f"Tracking items: {', '.join(WISHLIST_ITEMS_TO_TRACK)}")

    # 1. Fetch the latest data from the API
    full_api_data = get_all_wishlist_data()
    if not full_api_data:
        print("Aborting run due to API fetch failure.")
        exit()

    # 2. Extract only the specific data we care about
    current_wishlist = extract_alquis_wishlist(full_api_data)

    # 3. Read the previously saved data
    previous_wishlist = read_previous_wishlist()

    # 4. Compare the old and new data
    if current_wishlist != previous_wishlist:
        print("\nChange detected! Wishlist values have been updated.")
        print("--- Old Data ---")
        print(json.dumps(previous_wishlist, indent=2))
        print("--- New Data ---")
        print(json.dumps(current_wishlist, indent=2))

        # 5. Write the new data to the file
        write_wishlist(current_wishlist)
        print(f"\nSUCCESS: New data saved to '{STATE_FILE}'.")
    else:
        print("\nNo changes detected. Wishlist values are the same as the last run.")

    print("--- Run Finished ---")