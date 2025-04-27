import logging
import time
import random
import trafilatura
import concurrent.futures
import requests # Using requests+bs4 for link finding for more control
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Optional, Set, Any
import datetime
import pytz
import dateparser

# Configure logging
logger = logging.getLogger(__name__)

# List of Greek news websites to scrape (imported from config if available)
try:
    import config
    NEWS_SOURCES = config.NEWS_SOURCES
except Exception:
    # fallback if config import fails
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
        "https://www.gazzetta.gr/",
        "https://www.policenet.gr/"
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(homepage_url, headers=headers, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Fetched homepage {homepage_url} successfully. Status code: {response.status_code}")
        logger.info(f"Homepage content (first 500 chars): {response.text[:500]}")

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

        logger.info(f"Extracted {len(links)} candidate links from {homepage_url}")

        if not links:
            logger.warning(f"No links found on homepage: {homepage_url}")

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
    """Scrape content and metadata from a single article URL using Trafilatura and fallback meta tag extraction."""
    try:
        logger.debug(f"Attempting to scrape article: {url}")
        time.sleep(random.uniform(0.3, 1.0))
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Failed to download article content (fetch_url returned None): {url}")
            return None
        # Extract main content and metadata
        content = trafilatura.extract(downloaded, output_format='txt')
        metadata = trafilatura.metadata.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else None
        # Try to get date from trafilatura metadata
        pub_date = None
        date_source = None
        if metadata and metadata.date:
            pub_date = dateparser.parse(metadata.date)
            date_source = 'trafilatura'
        # If no date, try meta tags and <time> tags
        if not pub_date:
            soup = BeautifulSoup(downloaded, 'lxml')
            # Common meta tags for published date
            meta_date_selectors = [
                {'name': 'meta', 'attrs': {'property': 'article:published_time'}},
                {'name': 'meta', 'attrs': {'name': 'pubdate'}},
                {'name': 'meta', 'attrs': {'name': 'date'}},
                {'name': 'meta', 'attrs': {'itemprop': 'datePublished'}},
                {'name': 'meta', 'attrs': {'property': 'og:published_time'}},
                {'name': 'meta', 'attrs': {'property': 'og:updated_time'}},
            ]
            for selector in meta_date_selectors:
                tag = soup.find(**selector)
                if tag and tag.get('content'):
                    pub_date = dateparser.parse(tag['content'])
                    if pub_date:
                        date_source = f"meta:{selector['attrs']}"
                        break
            # Try <time> tag
            if not pub_date:
                time_tag = soup.find('time')
                if time_tag:
                    # Try datetime attribute or text
                    date_str = time_tag.get('datetime') or time_tag.text
                    pub_date = dateparser.parse(date_str)
                    if pub_date:
                        date_source = 'time_tag'
        # If still no date, log as not found
        if not pub_date:
            logger.warning(f"No publication date found for article: {url}")
        else:
            logger.info(f"Extracted publication date ({date_source}): {pub_date} for article: {url}")
        source_domain = extract_domain(url)
        logger.info(f"Successfully scraped: {title[:50] if title else 'NO TITLE'}... from {source_domain}")
        return {
            "title": title,
            "content": content.strip() if content else '',
            "url": url,
            "source": source_domain,
            "date": pub_date.date().isoformat() if pub_date else None
        }
    except Exception as e:
        logger.error(f"Error during scraping/extraction for article {url}: {e}", exc_info=False)
        return None


def is_greek_related(article):
    """Return True if the article is about Greece based on title/content."""
    if not article:
        return False
    text = (article.get('title', '') + ' ' + article.get('content', '')).lower()
    greek_keywords = [
        'greece', 'greek', 'athens', 'thessaloniki', 'crete', 'aegean', 'macedonia',
        'ελλάδα', 'ελλην', 'αθήνα', 'θεσσαλονίκη', 'κρήτη', 'αιγαίο', 'μακεδονία', 'πάτρα', 'πειραιάς', 'κυκλάδες', 'ηράκλειο', 'σαλονίκη'
    ]
    return any(keyword in text for keyword in greek_keywords)


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

    # Use config values if available
    try:
        sources = config.NEWS_SOURCES
    except Exception:
        sources = NEWS_SOURCES

    logger.info(f"Scraping news from {len(sources)} sources. Max articles per source: {max_articles_per_source}, Total target: {total_articles_target}")

    # Fetch links from each source, but limit immediately after extraction
    for source_url in sources:
        try:
            candidate_links = get_news_links(source_url, limit=max_articles_per_source)
            if len(candidate_links) > max_articles_per_source:
                logger.warning(f"Trimmed {len(candidate_links)} links to {max_articles_per_source} for {source_url}")
                candidate_links = candidate_links[:max_articles_per_source]
            logger.info(f"Using {len(candidate_links)} links from {source_url}")
            for link in candidate_links:
                if link not in all_article_urls:
                    all_article_urls.add(link)
        except Exception as exc:
            logger.error(f"Error fetching links from {source_url}: {exc}")

    logger.info(f"Collected {len(all_article_urls)} unique potential URLs. Will attempt to scrape up to {total_articles_target} articles.")

    # Limit total articles scraped
    urls_to_scrape = list(all_article_urls)[:total_articles_target]

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

    # Get today's date in EET (Eastern European Time)
    eet = pytz.timezone('Europe/Athens')
    today_eet = datetime.datetime.now(eet).date()

    filtered_news = []
    for article in all_news_data:
        # DEBUG: Log the title and date for each article
        logger.info(f"DEBUG: Article '{article.get('title','NO TITLE')}' date field: {repr(article.get('date'))}")
        pub_date = None
        # Try to extract date from article if present
        if 'date' in article and article['date']:
            try:
                pub_date = article['date']
                if isinstance(pub_date, str):
                    pub_date = datetime.datetime.fromisoformat(pub_date).date()
            except Exception:
                pub_date = None
        # STRICT: Only include if pub_date matches today_eet
        if pub_date == today_eet:
            filtered_news.append(article)
    logger.info(f"STRICT FILTER: {len(filtered_news)} articles for today's date in EET ({today_eet}) out of {len(all_news_data)} scraped.")

    # Relax filter: If no articles for today, include articles from today or yesterday
    if len(filtered_news) == 0:
        yesterday_eet = today_eet - datetime.timedelta(days=1)
        for article in all_news_data:
            pub_date = None
            if 'date' in article and article['date']:
                try:
                    pub_date = article['date']
                    if isinstance(pub_date, str):
                        pub_date = datetime.datetime.fromisoformat(pub_date).date()
                except Exception:
                    pub_date = None
            if pub_date in [today_eet, yesterday_eet]:
                filtered_news.append(article)
        logger.info(f"Relaxed filter: {len(filtered_news)} articles for today or yesterday (EET) out of {len(all_news_data)} scraped.")

    # If still none, fallback to latest as before
    if len(filtered_news) == 0:
        dated_articles = []
        for article in all_news_data:
            pub_date = None
            if 'date' in article and article['date']:
                try:
                    pub_date = article['date']
                    if isinstance(pub_date, str):
                        pub_date = datetime.datetime.fromisoformat(pub_date).date()
                except Exception:
                    pub_date = None
            if pub_date:
                dated_articles.append((pub_date, article))
        dated_articles.sort(reverse=True, key=lambda x: x[0])
        filtered_news = [a[1] for a in dated_articles[:10]]
        logger.info(f"No articles for today or yesterday, returning {len(filtered_news)} latest articles instead.")

    # After collecting articles, filter for Greek-related
    filtered_news = [a for a in filtered_news if is_greek_related(a)]
    logger.info(f"After Greece relevance filter: {len(filtered_news)} articles remain.")

    return filtered_news

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