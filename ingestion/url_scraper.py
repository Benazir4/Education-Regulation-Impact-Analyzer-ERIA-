"""
ingestion/url_scraper.py
Scrapes education regulation text from official URLs (UGC, AICTE, etc.)
"""

import requests
from bs4 import BeautifulSoup
import re


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Tags that usually contain policy text
CONTENT_TAGS = ["article", "main", "section", "div", "p"]

# Tags to strip (noise)
NOISE_TAGS = ["nav", "header", "footer", "script", "style", "aside", "form", "iframe"]


def fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch raw HTML from a URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        raise RuntimeError("Request timed out. The website may be slow.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to the URL. Check your internet connection.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP Error: {e.response.status_code}")


def clean_text(text: str) -> str:
    """Clean extracted text — remove extra whitespace, blank lines."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_html(html: str) -> str:
    """Parse HTML and extract meaningful regulation text."""
    soup = BeautifulSoup(html, "lxml")

    # Remove noise elements
    for tag in NOISE_TAGS:
        for element in soup.find_all(tag):
            element.decompose()

    # Try to find main content block
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", {"id": re.compile(r"content|main|body", re.I)})
        or soup.find("div", {"class": re.compile(r"content|main|body", re.I)})
    )

    if main_content:
        text = main_content.get_text(separator="\n")
    else:
        text = soup.get_text(separator="\n")

    return clean_text(text)


def scrape_url(url: str) -> dict:
    """
    Main function: scrapes text from a given URL.
    Returns a dict with the extracted text and metadata.
    """
    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        html = fetch_url(url)
        text = extract_text_from_html(html)
    except Exception as e:
        return {
            "url": url,
            "text": "",
            "status": "error",
            "message": str(e),
        }

    if len(text) < 100:
        return {
            "url": url,
            "text": "",
            "status": "error",
            "message": "Could not extract meaningful text from this URL.",
        }

    return {
        "url": url,
        "text": text,
        "char_count": len(text),
        "status": "success",
        "message": f"Successfully extracted {len(text):,} characters from URL.",
    }
