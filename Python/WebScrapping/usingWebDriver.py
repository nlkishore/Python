from selenium import webdriver
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

options = webdriver.EdgeOptions()
service = Service(EdgeChromiumDriverManager().install())

driver = webdriver.Edge(service=service, options=options)
driver.get("https://www.google.com")
