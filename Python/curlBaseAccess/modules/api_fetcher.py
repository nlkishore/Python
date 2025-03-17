import requests
from modules.logger import get_logger

logger = get_logger(__name__)

def fetch_api_data(name, url):
    """Fetch API data from the given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise HTTP errors (4xx, 5xx)
        logger.info(f"API Response for {name}: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching API data ({name}): {e}")
        return None
