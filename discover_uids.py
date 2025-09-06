import json
import re
from playwright.sync_api import sync_playwright, TimeoutError

# --- Configuration ---
# We are targeting a user known to have the clickable, detailed leaderboard.
TARGET_USERNAME = "brattyxmeri"
# These are the same coordinates from your logger.py
CLICK_COORDS = {"x": 790, "y": 371}

def discover_leaderboard_users():
    """
    Launches a browser, navigates to a specific profile, clicks to trigger
    the detailed leaderboard, captures the console output, and prints the user data.
    """
    print("Starting user discovery process...")
    print(f"Targeting user '{TARGET_USERNAME}' to access the detailed leaderboard.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print(f"  Navigating to https://sent.bio/{TARGET_USERNAME}...")
            page.goto(f"https://sent.bio/{TARGET_USERNAME}", wait_until="domcontentloaded", timeout=45000)

            print("  Waiting for the application container to load...")
            page.locator("flutter-view").wait_for(state='attached', timeout=30000)
            
            # A short wait to ensure all scripts on the page are initialized
            print("  Waiting 3 seconds for dynamic content to initialize...")
            page.wait_for_timeout(3000)

            print(f"  Clicking coordinates X={CLICK_COORDS['x']}, Y={CLICK_COORDS['y']} to trigger leaderboard...")
            
            # Use 'expect_console_message' to wait specifically for our target data
            with page.expect_console_message(
                lambda msg: "fetchLeaderboard response:" in msg.text, 
                timeout=15000
            ) as console_message_info:
                page.mouse.click(CLICK_COORDS['x'], CLICK_COORDS['y'])

            print("  Successfully captured leaderboard data from console!")
            
            # Extract the raw text from the captured message
            message = console_message_info.value
            raw_js_object_str = message.text.replace("fetchLeaderboard response: ", "").strip()
            
            print("\n--- Cleaning and Parsing Data ---")
            
            # This cleaning logic is copied from your logger.py to handle the non-standard JS object
            cleaned_str = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', raw_js_object_str)
            cleaned_str = re.sub(r':\s*([a-zA-Z_]+)', r': "\1"', cleaned_str)
            cleaned_str = re.sub(r':\s*(\d+(st|nd|rd|th))', r': "\1"', cleaned_str)
            cleaned_str = cleaned_str.replace(': "null"', ': null')
            cleaned_str = cleaned_str.replace(': "true"', ': true')
            cleaned_str = cleaned_str.replace(': "false"', ': false')
            
            leaderboard_data = json.loads(cleaned_str)
            
            print("\n--- DISCOVERED USER DATA ---")
            # Pretty-print the JSON so it's easy to read
            print(json.dumps(leaderboard_data, indent=2))
            
            # Extract and print a summary list
            users = leaderboard_data.get('users', [])
            if users:
                print("\n--- Summary (username | uid) ---")
                for user in users:
                    # Look for username and uid fields (names might vary, e.g., 'id', 'userId')
                    username = user.get('username', 'N/A')
                    uid = user.get('uid', 'N/A') # The field might be named 'uid', 'id', etc.
                    print(f"{username: <20} | {uid}")

        except TimeoutError:
            print("\nError: Timed out waiting for the leaderboard console message.")
            print("This could be due to a change in the website's behavior or a slow network.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
        finally:
            print("\nClosing browser.")
            browser.close()

if __name__ == "__main__":
    discover_leaderboard_users()