from selenium import webdriver
import time
#import chromedriver_binary  # Adds chromedriver binary to path

driver = webdriver.Chrome()
driver.get("http://www.python.org")
time.sleep(20)