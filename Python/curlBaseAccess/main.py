import configparser
import os
from modules.api_fetcher import fetch_api_data
from modules.html_parser import fetch_and_parse_html
from modules.logger import get_logger

logger = get_logger(__name__)

# Read INI File
config_path = os.path.join("config", "commands.ini")
config = configparser.ConfigParser()
config.read(config_path)

# Process API Requests
if "API_REQUESTS" in config:
    for key, url in config["API_REQUESTS"].items():
        response = fetch_api_data(key, url)
        if response:
            logger.info(f"Data fetched from {key}: {response}")

# Process Web Pages
if "WEB_PAGES" in config:
    for key, url in config["WEB_PAGES"].items():
        parsed_data = fetch_and_parse_html(key, url)
        if parsed_data:
            logger.info(f"Parsed HTML data from {key}: {parsed_data}")
