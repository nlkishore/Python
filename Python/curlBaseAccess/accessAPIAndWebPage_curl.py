import configparser
import requests
from bs4 import BeautifulSoup
import os
import certifi

# Read INI file
config = configparser.ConfigParser()
config.read("commands.ini")

# SSL Certificate Handling for Windows
if os.name == "nt":
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

def fetch_api_data(name, url):
    """Fetches API data from the given URL."""
    try:
        response = requests.get(url, verify=True, timeout=10)
        response.raise_for_status()  # Raise HTTP errors (4xx, 5xx)
        print(f"API Response for {name}: {response.json()}")  # Assuming JSON response
    except requests.exceptions.RequestException as e:
        print(f"Error fetching API data ({name}): {e}")

def fetch_and_parse_html(name, url):
    """Fetches and parses HTML content from a webpage."""
    try:
        response = requests.get(url, verify=True, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else "No title found"
        print(f"Web Page ({name}) Title: {title}")

        # Extracting first paragraph text
        paragraph = soup.find("p")
        if paragraph:
            print(f"First paragraph: {paragraph.get_text()}\n")
        else:
            print("No paragraphs found\n")
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching web page ({name}): {e}")

# Process API Requests
if "API_REQUESTS" in config:
    for key, url in config["API_REQUESTS"].items():
        fetch_api_data(key, url)

# Process Web Pages
if "WEB_PAGES" in config:
    for key, url in config["WEB_PAGES"].items():
        fetch_and_parse_html(key, url)
