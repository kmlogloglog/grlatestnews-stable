import logging
import time
import random
import trafilatura
import concurrent.futures
from urllib.parse import urlparse

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
    "https://www.gazzetta.gr/",
    "https://www.policenet.gr/"
]

def extract_domain(url):
    """Extract the domain name from a URL."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain

def get_news_links(url, limit=5):
    """Extract news article links from a homepage."""
    try:
        logger.debug(f"Fetching links from: {url}")
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.error(f"Failed to download content from {url}")
            return []
        
        # Extract using BeautifulSoup since trafilatura.extract_links is not available
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(downloaded, 'html.parser')
        
        # Find all links
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        
        # Filter links to only include those from the same domain and normalize URLs
        domain = extract_domain(url)
        filtered_links = []
        
        for link in links:
            # Handle relative URLs
            if link.startswith('/'):
                link = url.rstrip('/') + link
            elif not (link.startswith('http://') or link.startswith('https://')):
                continue
                
            link_domain = extract_domain(link)
            # Check if it's from the same domain and likely an article
            if link_domain == domain and ("/article/" in link or "/news/" in link or "/ellada/" in link or "/politics/" in link):
                filtered_links.append(link)
        
        # Deduplicate and limit the number of links
        unique_links = list(set(filtered_links))
        logger.debug(f"Found {len(unique_links)} unique article links from {url}")
        return unique_links[:limit]
        
    except Exception as e:
        logger.error(f"Error getting links from {url}: {str(e)}")
        return []

def scrape_article(url):
    """Scrape content from a single article URL."""
    try:
        logger.debug(f"Scraping article: {url}")
        
        # Add a small delay to avoid overwhelming the server
        time.sleep(random.uniform(0.5, 2.0))
        
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.error(f"Failed to download article: {url}")
            return None
        
        # Extract main content
        content = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        
        # Get metadata like title
        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else "Unknown Title"
        
        # Get source domain
        source = extract_domain(url)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "source": source
        }
        
    except Exception as e:
        logger.error(f"Error scraping article {url}: {str(e)}")
        return None

def scrape_news():
    """Scrape news from all sources and their articles."""
    all_news_data = []
    
    # Start with a list to hold all article URLs
    all_article_urls = []
    
    # Get article URLs from each news source homepage
    for source_url in NEWS_SOURCES:
        try:
            article_urls = get_news_links(source_url)
            all_article_urls.extend(article_urls)
            
            # Small delay between sources
            time.sleep(random.uniform(1.0, 3.0))
            
        except Exception as e:
            logger.error(f"Error processing source {source_url}: {str(e)}")
    
    logger.info(f"Found {len(all_article_urls)} article URLs to scrape")
    
    # Use ThreadPoolExecutor to scrape articles in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_article, url): url for url in all_article_urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                article_data = future.result()
                if article_data and article_data["content"]:
                    all_news_data.append(article_data)
            except Exception as e:
                logger.error(f"Error processing article {url}: {str(e)}")
    
    logger.info(f"Successfully scraped {len(all_news_data)} articles")
    return all_news_data
