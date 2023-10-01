from bs4 import BeautifulSoup
from selenium import webdriver

# Create your driver
driver = webdriver.Chrome()

# Get  page
driver.get('http://news.ycombinator.com')

# Feed the source to BeautifulSoup
soup = BeautifulSoup(driver.page_source)

print (soup.title)  # <title>Hacker News</title>