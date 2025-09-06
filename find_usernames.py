import requests
import json

# The API endpoint for the wishlists collection
WISHLIST_API_URL = "https://firestore.googleapis.com/v1/projects/sent-wc254r/databases/(default)/documents/wishlists?pageSize=300"

# --- THE KEY ---
# The *hypothesized* API endpoint for the users collection.
# This is the most common naming convention.
USERS_API_URL = "https://firestore.googleapis.com/v1/projects/sent-wc254r/databases/(default)/documents/users"

def get_user_map_from_api():
    """
    Attempts to fetch all documents from the /users collection
    and builds a dictionary mapping UID -> username.
    """
    print(f"Attempting to fetch user data from: {USERS_API_URL}")
    uid_to_username_map = {}

    try:
        response = requests.get(USERS_API_URL, timeout=15)
        # Raise an exception if the request failed (e.g., 403 Forbidden, 404 Not Found)
        response.raise_for_status()
        
        data = response.json()
        documents = data.get("documents", [])

        if not documents:
            print("Warning: Found the /users collection, but it appears to be empty.")
            return None

        for doc in documents:
            # The UID is often the last part of the document's 'name'
            # e.g., "projects/.../documents/users/it54UEAVGkdEcRJLthGuidZHObp2"
            full_name = doc.get("name", "")
            uid = full_name.split('/')[-1]

            # The username is in the 'fields'
            fields = doc.get("fields", {})
            username = fields.get("username", {}).get("stringValue")

            if uid and username:
                uid_to_username_map[uid] = username

        print(f"Successfully built a map of {len(uid_to_username_map)} users.")
        return uid_to_username_map

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("Error: Access to the /users collection is forbidden. This API endpoint is likely not public.")
        elif e.response.status_code == 404:
            print("Error: The /users collection was not found at this URL.")
        else:
            print(f"An HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"A network error occurred: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while parsing user data: {e}")
        return None


def find_users_from_wishlists(user_map):
    """
    Fetches wishlist data and prints the username for each unique owner UID.
    """
    print("\nFetching wishlist data to find owner UIDs...")
    try:
        response = requests.get(WISHLIST_API_URL, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        documents = data.get("documents", [])
        
        owner_uids = set()
        for doc in documents:
            fields = doc.get("fields", {})
            owner_uid = fields.get("owner", {}).get("stringValue")
            if owner_uid:
                owner_uids.add(owner_uid)

        print(f"Found {len(owner_uids)} unique users in the wishlist data.")
        print("--- Usernames Found ---")
        
        found_count = 0
        for uid in sorted(list(owner_uids)):
            username = user_map.get(uid, "Unknown (not in users collection)")
            print(f"UID: {uid} -> Username: {username}")
            if username != "Unknown (not in users collection)":
                found_count += 1
        
        print(f"\nSuccessfully matched {found_count} of {len(owner_uids)} users.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching wishlist API: {e}")


if __name__ == "__main__":
    # 1. Try to build the map from UID to username
    master_user_map = get_user_map_from_api()

    # 2. If the map was created successfully, use it to look up users
    if master_user_map:
        find_users_from_wishlists(master_user_map)
    else:
        print("\nCould not build the user map. Aborting wishlist lookup.")