import requests
from bs4 import BeautifulSoup
from modules.logger import get_logger

logger = get_logger(__name__)

def fetch_and_parse_html(name, url):
    """Fetch and parse HTML content from a webpage."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract Title
        title = soup.title.string if soup.title else "No title found"
        logger.info(f"Web Page ({name}) Title: {title}")

        # Extract first paragraph
        paragraph = soup.find("p")
        para_text = paragraph.get_text() if paragraph else "No paragraphs found"
        logger.info(f"First paragraph: {para_text}")

        # Extract all links
        links = [a["href"] for a in soup.find_all("a", href=True)]
        logger.info(f"Found {len(links)} links on {name}")

        return {"title": title, "paragraph": para_text, "links": links}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching web page ({name}): {e}")
        return None
