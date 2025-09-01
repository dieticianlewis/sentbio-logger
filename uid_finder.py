import requests
from bs4 import BeautifulSoup
import re

# --- Add the usernames you want to find UIDs for here ---
USERNAMES_TO_FIND = [
    "brattyxmeri",
    "fairybrat",
    "digitalvicc"
]

def find_uids():
    print("--- Starting UID Finder ---")
    results = {}
    for username in USERNAMES_TO_FIND:
        profile_url = f"https://sent.bio/{username}"
        print(f"Searching on {profile_url}...")
        try:
            response = requests.get(profile_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tags = soup.find_all('meta', property='og:image')
            
            found_uid = None
            for tag in meta_tags:
                if tag.has_attr('content') and "public_users" in tag['content']:
                    match = re.search(r"public_users(?:/|%2F)([a-zA-Z0-9]+)(?:/|%2F)", tag['content'])
                    if match:
                        found_uid = match.group(1)
                        break
            
            if found_uid:
                print(f"  SUCCESS: Found UID for {username}: {found_uid}")
                results[username] = found_uid
            else:
                print(f"  FAILURE: Could not find a UID for {username}.")
                results[username] = "NOT_FOUND"

        except requests.exceptions.RequestException as e:
            print(f"  ERROR: Could not fetch page for {username}: {e}")
            results[username] = "FETCH_ERROR"
            
    print("\n--- Results ---")
    print("Copy the following lines into your logger.py PROFILES_TO_TRACK list:")
    for username, uid in results.items():
        print(f'    {{\n        "username": "{username}",\n        "uid": "{uid}",\n        "wishlist_tweet": "{username}\'s \'{{title}}\' goal received ${{amount:.2f}}! at {{time}} EST",\n        "tip_tweet": "{username} also received a random tip! at {{time}} EST"\n    }},')

if __name__ == "__main__":
    find_uids()