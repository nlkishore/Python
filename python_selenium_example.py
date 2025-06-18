from selenium import webdriver
import time


driver = webdriver.Chrome()
driver.maximize_window()
driver.get("http://www.seleniumeasy.com/test/basic-first-form-demo.html")
time.sleep(40)
assert "Selenium Easy Demo - Simple Form to Automate using Selenium" in driver.title
time.sleep(40)

eleUserMessage = driver.find_element_by_id("user-message") # type: ignore
eleUserMessage.clear()
eleUserMessage.send_keys("Test Python")

eleShowMsgBtn=driver.find_element_by_css_selector('#get-input > .btn') # type: ignore
eleShowMsgBtn.click()

eleYourMsg=driver.find_element_by_id("display") # type: ignore
assert "Test Python" in eleYourMsg.text
driver.close()