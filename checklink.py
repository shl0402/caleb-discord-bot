import time
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# ======= CONFIGURATION =======
# Replace with your Discord channel URL
discord_url = "https://discord.com/channels/1255396002521808906/1270140003879747604"

# (Optional) If you want to use a specific Chrome profile to avoid login issues,
# uncomment the line below and update the path accordingly.
# For example, on Windows:
profile_path = "C:\\Users\\Pithon\\AppData\\Local\\Google\\Chrome\\User Data"
# options.add_argument(f"user-data-dir={profile_path}")

# ==============================

# Configure Chrome options for undetected_chromedriver
options = uc.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument('--disable-popup-blocking')
options.add_argument('--disable-notifications')
# Uncomment and update the following line if you need to use a custom profile:
# options.add_argument("user-data-dir=C:\\Path\\To\\Your\\Chrome\\User Data")

# Initialize the undetected-chromedriver
print("[INFO] Initializing Chrome using undetected-chromedriver...")
driver = uc.Chrome(options=options)

# Open the Discord channel URL
driver.get(discord_url)
print("[INFO] Navigating to Discord channel...")
time.sleep(15)  # Adjust this wait time as needed for the page to load completely

# Set to store links that have already been discovered
found_links = set()

# Regular expression to detect http or https links
link_regex = re.compile(r"https?://\S+")

print("[INFO] Monitoring Discord chat for new links... (Press Ctrl+C to stop)")

try:
    while True:
        # Locate message elements; the CSS selector below targets elements with classes containing 'messageContent'
        message_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='messageContent']")
        
        for element in message_elements:
            text = element.text
            # Search for links in the text
            links_in_text = link_regex.findall(text)
            
            # Print and store any newly discovered links
            for link in links_in_text:
                if link not in found_links:
                    print("New link found:", link)
                    found_links.add(link)
                    
        # Wait a few seconds before scanning the chat again
        time.sleep(5)

except KeyboardInterrupt:
    print("\n[INFO] Monitoring stopped by user.")

except Exception as e:
    print("[ERROR] An error occurred:", str(e))

finally:
    print("[INFO] Closing browser...")
    driver.quit()