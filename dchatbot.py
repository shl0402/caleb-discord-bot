import discord
from discord.ext import commands
import asyncio
import time

from private import token

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ------------------------------------------------------------------------
# Configure your Selenium Chrome options
# ------------------------------------------------------------------------
def get_chrome_driver():
    """
    Set up Chrome WebDriver with modern Selenium modules.
    """
    options = Options()
    # Uncomment for headless execution
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    
    # Automatically download and manage ChromeDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

# ------------------------------------------------------------------------
# Discord Bot Setup
# ------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True  # Make sure to enable the message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# We create a queue to handle queries one at a time
processing_queue = asyncio.Queue()

# We keep a single driver instance (or you can create a new instance for each query)
# but be aware of session handling and concurrency issues:
driver = get_chrome_driver()

# ------------------------------------------------------------------------
# Utility function: get ChatGPT-like response from the website
# ------------------------------------------------------------------------
def get_response_from_site(query: str) -> str:
    """
    Open the website, send a query, wait for the response, and return the result.
    """
    driver = get_chrome_driver()
    
    try:
        # Navigate to the target website
        driver.get("https://chatgpt.com/g/g-p-67693aa31a648191beba20510e108679/project?model=gpt-4o")
        
        # Wait for the page to load fully (adjust timeout as needed)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@id='promptbox']"))
        )

        # Locate the input box and send the query
        search_box = driver.find_element(By.XPATH, "//textarea[@id='promptbox']")
        search_box.clear()
        search_box.send_keys(query)

        # Locate and click the "Send" button (adjust selector if needed)
        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@id='sendBtn']"))
        )
        send_button.click()

        # Wait for the response to appear (adjust selector and timeout as needed)
        response_element = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='response-output']"))
        )

        # Extract and return the text from the response element
        response_text = response_element.text
        return response_text

    finally:
        # Close the browser session
        driver.quit()

# ------------------------------------------------------------------------
# The background task that processes the queue
# ------------------------------------------------------------------------
async def process_queue():
    while True:
        ctx, query = await processing_queue.get()
        try:
            # 1. Call the Selenium-based function to get the AI's answer
            answer = get_response_from_site(query)
            
            # 2. Send the answer back to the channel
            await ctx.send(f"**AI says:** {answer[:2000]}")  # Discord has a 2000 char limit per message

        except Exception as e:
            # In case something goes wrong
            await ctx.send(f"Error occurred while fetching response: `{e}`")

        processing_queue.task_done()

# ------------------------------------------------------------------------
# The !chat command
# ------------------------------------------------------------------------
@bot.command()
async def chat(ctx, *, query: str):
    """
    The user will call: !chat <some prompt here>
    We'll put it in the queue to be processed one by one.
    """
    await ctx.send(f"**Received query:** {query}\nQueueing up your request...")
    await processing_queue.put((ctx, query))

# ------------------------------------------------------------------------
# On bot start, launch the queue processor
# ------------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    # Start a background task to keep processing the queue
    bot.loop.create_task(process_queue())

# ------------------------------------------------------------------------
# Finally, run the bot
# ------------------------------------------------------------------------
bot.run(token())
