from selenium import webdriver
from selenium.webdriver.chrome.service import Service

service = Service("C:\\path\\to\\chromedriver.exe")
driver = webdriver.Chrome(service=service)
driver.get("https://www.google.com")
print(driver.title)
driver.quit()
