import time
import re
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from private import token
from private import login
from private import pwd

# ==== CONFIGURATION ====
# Discord user login credentials
login_identifier = login()       # e.g., "+1234567890" or "email@example.com"
login_password = pwd()

# URL of the Discord channel you want to monitor
discord_channel_url = "https://discord.com/channels/1255396002521808906/1270140003879747604"

# The link prefix to filter for.
target_link_prefix = "https://www.roblox.com/share?code="

# Forwarding configuration:
discord_bot_token = token()   # Replace with your Discord bot API token
forward_channel_id = "1342416025244799007"       # The channel ID in the target server to forward the message
role_id_to_ping = "1344274116085157940"
# role_id_to_ping = "1342416086649405481"                      # The role ID to be pinged in the forwarded message
# ========================

# Configure Chrome options for undetected-chromedriver.
options = uc.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-notifications")
# Optional: Use your Chrome profile if desired:
# options.add_argument("user-data-dir=C:\\Path\\To\\Your\\Chrome\\User Data")

print("[INFO] Launching Chrome using undetected-chromedriver...")
driver = uc.Chrome(options=options)

# Navigate to Discord's login page.
driver.get("https://discord.com/login")
time.sleep(5)  # Allow time for the page to load

# Click "Continue in Browser" if it appears.
try:
    continue_button = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue in Browser')]"))
    )
    print("[INFO] Clicking 'Continue in Browser' button...")
    continue_button.click()
    time.sleep(3)  # Allow time for UI transition
except Exception as e:
    print("[WARNING] 'Continue in Browser' button not found or already clicked. Error:", e)

# Wait for the login form and fill in the credentials.
try:
    print("[INFO] Waiting for login fields...")
    identifier_field = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//input[@name='email']"))
    )
    password_field = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//input[@name='password']"))
    )

    # Fill in the login credentials.
    identifier_field.clear()
    identifier_field.send_keys(login_identifier)
    password_field.clear()
    password_field.send_keys(login_password)

    # Submit the login form by sending the Enter key.
    password_field.send_keys(Keys.ENTER)
    print("[INFO] Submitted login credentials...")
except Exception as e:
    print("[ERROR] Failed to locate or interact with the login fields:", e)
    driver.quit()
    exit(1)

# Wait for login to complete. Discord logs in successfully when the URL changes to include '/channels/'.
try:
    WebDriverWait(driver, 30).until(
        EC.url_contains("/channels/")
    )
    print("[INFO] Login successful!")
except Exception as e:
    print("[ERROR] Login may have failed (timed out waiting for logged-in page):", e)
    driver.quit()
    exit(1)

# Navigate to the target Discord channel.
driver.get(discord_channel_url)
print("[INFO] Navigating to the Discord channel...")
time.sleep(15)  # Allow time for channel and messages to load

# Set to store complete messages that have been processed.
found_messages = set()

# Before starting monitoring, run an initialization (warmup) period.
warmup_duration = 60  # seconds
warmup_start = time.time()
print("[INFO] Warming up for 60 seconds to collect initial messages. No forwarding during this time.")
while time.time() - warmup_start < warmup_duration:
    message_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='messageContent']")
    for element in message_elements:
        found_messages.add(element.text)
    time.sleep(5)
print("[INFO] Warmup period complete. Monitoring new messages for target links will now begin.")

def forward_message(message_text):
    """
    Forwards the provided message_text to the specified Discord channel using a bot.
    The forwarded message will include a ping to a designated role.
    """
    url = f"https://discord.com/api/v10/channels/{forward_channel_id}/messages"
    payload = {
        "content": f"<@&{role_id_to_ping}> \n{message_text}"
    }
    headers = {
        "Authorization": f"Bot {discord_bot_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in (200, 201):
            print("[INFO] Message forwarded successfully.")
        else:
            print(f"[ERROR] Failed to forward message: {response.status_code} {response.text}")
    except Exception as e:
        print("[ERROR] Exception occurred while forwarding message:", e)

# Regular expression to detect http(s) links.
link_regex = re.compile(r"https?://\S+")

print("[INFO] Monitoring Discord chat for new messages with target links...")
try:
    while True:
        # Locate message elements (adjust the selector if Discord updates its UI).
        message_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='messageContent']")
        for element in message_elements:
            message_text = element.text

            # Only process messages not already seen.
            if message_text in found_messages:
                continue

            # Check for links in the new message.
            links_found = link_regex.findall(message_text)
            for link in links_found:
                if link.startswith(target_link_prefix):
                    print("\n[INFO] New message containing target link found:")
                    print(message_text)
                    found_messages.add(message_text)
                    # Forward the entire message to the target channel, pinging the desired role.
                    forward_message(message_text)
                    break  # Exit the link loop after finding one matching link.
        # Wait before scanning for new messages.
        time.sleep(5)
except KeyboardInterrupt:
    print("\n[INFO] Monitoring stopped by user.")
except Exception as e:
    print("[ERROR] An error occurred during monitoring:", e)
finally:
    print("[INFO] Closing browser.")
    driver.quit()