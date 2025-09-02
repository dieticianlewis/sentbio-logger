from playwright.sync_api import sync_playwright
import time
import os

# --- We will always use this standard window size ---
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720

# --- The HTML for our self-contained coordinate finder page ---
COORDS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Coordinate Finder</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f0f0f0; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Mouse Coordinate Finder</h1>
    <p>Keep this tab open. The X and Y coordinates of your mouse will be displayed in the tab's title.</p>
    <p>Navigate to the target website in this window to find the coordinates of an element.</p>
    
    <script>
        document.addEventListener('mousemove', function(e) {
            // Update the document title with the live coordinates
            document.title = `X: ${e.clientX}, Y: ${e.clientY}`;
        });
    </script>
</body>
</html>
"""

def run():
    # Create the temporary HTML file
    with open("coords.html", "w") as f:
        f.write(COORDS_HTML)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        
        # Go to our new, local HTML file
        page.goto(f"file://{os.path.abspath('coords.html')}")
        
        print("\n" + "="*60)
        print("COORDINATE FINDER IS RUNNING")
        print(f"The browser window is now fixed at {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} pixels.")
        print("\n1. Go to the browser window that just opened.")
        print("2. In that SAME window, navigate to https://sent.bio/brattyxmeri.")
        print("3. CAREFULLY move your mouse over the 'stats' icon.")
        print("4. Look at the TITLE of the browser tab. It will show the live X and Y values.")
        print("5. Write down the X and Y coordinates (e.g., X: 1150, Y: 125).")
        print("6. Close the browser to end the script.")
        print("="*60 + "\n")
        
        page.wait_for_event("close")

        print("Browser closed. Script finished.")

    # Clean up the temporary HTML file
    os.remove("coords.html")


if __name__ == "__main__":
    run()