import logging
import time
import random
import trafilatura
import concurrent.futures
import requests # Using requests+bs4 for link finding for more control
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional, Set, Any

# Configure logging
logger = logging.getLogger(__name__)

# List of Greek news websites to scrape
NEWS_SOURCES = [
    "https://www.protothema.gr/",
    "https://www.newsit.gr/",
    "https://www.newsbomb.gr/",
    "https://www.in.gr/",
    "https://www.iefimerida.gr/",
    "https://www.kathimerini.gr/",
    "https://www.news247.gr/",
    "https://www.naftemporiki.gr/",
    "https://www.tanea.gr/",
    "https://www.gazzetta.gr/", # Sports news might be less relevant?
    "https://www.policenet.gr/" # More specific audience
]

# Patterns often indicating non-article pages to exclude
EXCLUDE_URL_PATTERNS = [
    "/tag/", "/category/", "/author/", "/user/", "/search/", "/videos/", "/photos/", "/gallery/",
    "/contact", "/about", "/privacy", "/terms", "/faq/", "/archive/", "/syndication/", "/feed/",
    "/live/", "/events/", "/shop/", "/classifieds/", "/jobs/", "/weather/", "/horoscope/",
    "javascript:", "#", "mailto:", "tel:", ".pdf", ".jpg", ".png", ".gif", ".zip", ".rar",
    "facebook.com", "twitter.com", "linkedin.com", "instagram.com", "youtube.com",
    "login", "register", "subscribe", "syndromites" # Greek for subscribers
]

# Optional: Patterns that might *boost* likelihood (use sparingly)
# ARTICLE_URL_HINTS = ["/article/", "/post/", "/eidiseis/", "/nea/", "/reportaz/"] # Greek news/article

def extract_domain(url: str) -> str:
    """Extract the domain name (e.g., 'protothema.gr') from a URL."""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def get_news_links(homepage_url: str, limit: int = 5) -> List[str]:
    """
    Extract potential news article links from a homepage using requests and BeautifulSoup.
    Focuses on excluding known non-article patterns.
    """
    links: Set[str] = set()
    domain = extract_domain(homepage_url)
    if not domain:
        logger.error(f"Could not extract domain from homepage URL: {homepage_url}")
        return []

    try:
        logger.debug(f"Fetching links from: {homepage_url}")
        # Use requests for more control over headers and timeout
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(homepage_url, headers=headers, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if not href:
                continue

            # Create absolute URL
            absolute_url = urljoin(homepage_url, href)
            link_domain = extract_domain(absolute_url)

            # Basic Filtering:
            # 1. Must be HTTP/HTTPS
            if not absolute_url.startswith(('http://', 'https://')):
                continue
            # 2. Must be from the same primary domain
            if link_domain != domain:
                continue
            # 3. Exclude URLs matching common non-article patterns
            if any(pattern in absolute_url.lower() for pattern in EXCLUDE_URL_PATTERNS):
                continue
            # 4. Basic length check (very short URLs are often not articles)
            if len(absolute_url) < len(homepage_url) + 10: # Heuristic
                 continue

            # If it passes filters, add it
            links.add(absolute_url)

        # Sort by apparent freshness (often longer URLs are newer, but this is weak)
        # Or simply take a random sample after filtering
        link_list = sorted(list(links), key=len, reverse=True) # Longer URLs sometimes are more specific/newer

        logger.info(f"Found {len(link_list)} potential article links from {homepage_url}")
        return link_list[:limit]

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Error getting links from {homepage_url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error parsing links from {homepage_url}: {e}")
        return []


def scrape_article(url: str) -> Optional[Dict[str, Any]]:
    """Scrape content and metadata from a single article URL using Trafilatura."""
    try:
        logger.debug(f"Attempting to scrape article: {url}")

        # Add a small random delay
        time.sleep(random.uniform(0.3, 1.0))

        # Fetch and extract using Trafilatura
        # Setting decode_errors='ignore' might help with some encoding issues
        downloaded = trafilatura.fetch_url(url, decode_errors='ignore')
        if not downloaded:
            logger.warning(f"Failed to download article content (fetch_url returned None): {url}")
            return None

        # Extract main content
        content = trafilatura.extract(downloaded,
                                      include_comments=False,
                                      include_tables=False,
                                      output_format='text', # Get plain text
                                      include_formatting=False) # No markdown

        if not content or len(content.split()) < 50: # Filter out pages with very little extracted text
            logger.warning(f"Extracted content too short or empty, likely not a main article: {url}")
            return None

        # Attempt to get metadata
        title = "Untitled Article"
        try:
            metadata = trafilatura.extract_metadata(downloaded)
            if metadata and metadata.title:
                title = metadata.title
        except Exception as meta_err:
             logger.warning(f"Could not extract metadata for {url}: {meta_err}")


        source_domain = extract_domain(url)

        logger.info(f"Successfully scraped: {title[:50]}... from {source_domain}")
        return {
            "title": title,
            "content": content.strip(), # Clean whitespace
            "url": url,
            "source": source_domain
        }

    except Exception as e:
        # Catch potential errors during fetch or extract
        logger.error(f"Error during scraping/extraction for article {url}: {e}", exc_info=False) # Set exc_info=True for traceback
        return None


def scrape_news(max_articles_per_source: int = 4, total_articles_target: int = 20) -> List[Dict[str, Any]]:
    """
    Scrape news from sources, fetching links and then article content in parallel.

    Args:
        max_articles_per_source: Max links to fetch from each homepage.
        total_articles_target: Aim for roughly this many articles to scrape.

    Returns:
        A list of dictionaries, each containing scraped article data.
    """
    all_news_data: List[Dict[str, Any]] = []
    all_article_urls: Set[str] = set() # Use a set to avoid duplicate URLs early

    # Use a subset of sources if desired, or the full list
    # sources_to_use = NEWS_SOURCES[:7] # Example: Limit sources
    sources_to_use = NEWS_SOURCES
    logger.info(f"Starting scrape for {len(sources_to_use)} sources...")

    # --- Phase 1: Get potential article URLs ---
    # Can run this sequentially or in parallel (parallel might be faster but hit rate limits)
    for source_url in sources_to_use:
        article_urls = get_news_links(source_url, limit=max_articles_per_source + 2) # Get slightly more initially
        if article_urls:
            added_count = len(set(article_urls) - all_article_urls)
            all_article_urls.update(article_urls)
            logger.debug(f"Added {added_count} new unique links from {source_url}. Total unique URLs: {len(all_article_urls)}")
        time.sleep(random.uniform(0.2, 0.5)) # Small delay between fetching homepages

    # Limit the total number of URLs before scraping articles
    limited_urls = list(all_article_urls)
    random.shuffle(limited_urls) # Shuffle to get diversity if limiting severely
    urls_to_scrape = limited_urls[:min(len(limited_urls), total_articles_target * 2)] # Aim high initially, as some will fail

    logger.info(f"Collected {len(all_article_urls)} unique potential URLs. Will attempt to scrape {len(urls_to_scrape)} articles.")

    # --- Phase 2: Scrape articles in parallel ---
    if not urls_to_scrape:
         logger.warning("No article URLs found to scrape.")
         return []

    successful_scrapes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit scraping tasks
        future_to_url = {executor.submit(scrape_article, url): url for url in urls_to_scrape}

        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                article_data = future.result()
                # Check if data is valid and content exists
                if article_data and isinstance(article_data, dict) and article_data.get("content"):
                    all_news_data.append(article_data)
                    successful_scrapes += 1
                elif article_data is None:
                    logger.debug(f"Scraping returned None (filtered or failed) for: {url}")
                else:
                     logger.warning(f"Scraping returned unexpected data type ({type(article_data)}) for: {url}")

            except Exception as exc:
                logger.error(f"Generating task for {url} resulted in an exception: {exc}", exc_info=False)

    logger.info(f"Scraping complete. Successfully retrieved content for {successful_scrapes} out of {len(urls_to_scrape)} attempted articles.")

    # Optional: Sort by content length or keep as is
    # all_news_data.sort(key=lambda x: len(x.get("content", "")), reverse=True)

    return all_news_data

# Example usage (if running this file directly)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting direct scraper test...")
    scraped_data = scrape_news()
    print(f"\n--- Scraper Test Results ---")
    print(f"Total articles scraped: {len(scraped_data)}")
    if scraped_data:
        print("Example article:")
        print(f"  Title: {scraped_data[0].get('title')}")
        print(f"  Source: {scraped_data[0].get('source')}")
        print(f"  URL: {scraped_data[0].get('url')}")
        print(f"  Content Snippet: {scraped_data[0].get('content', '')[:150]}...")
    logger.info("Direct scraper test finished.")