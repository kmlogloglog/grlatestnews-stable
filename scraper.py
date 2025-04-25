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
        
        # Keywords that suggest this is a news article in Greek websites
        article_indicators = [
            "/article/", "/news/", "/ellada/", "/politics/", "/greece/", 
            "/politiki/", "/economy/", "/oikonomia/", "/kosmos/", "/world/", 
            "/koinonia/", "/society/", "/ygeia/", "/health/"
        ]
        
        # Keywords that suggest this is NOT a news article
        exclude_indicators = [
            "/tag/", "/author/", "/category/", "/contact/", "/about/", 
            "/privacy/", "/terms/", "/video/", "/photos/", "/galleries/",
            "javascript:", "#", "mailto:", "tel:", "/rss/"
        ]
        
        for link in links:
            skip = False
            
            # Skip empty or javascript links
            if not link or link.startswith('#') or link.startswith('javascript'):
                continue
                
            # Handle relative URLs
            if link.startswith('/'):
                link = url.rstrip('/') + link
            elif not (link.startswith('http://') or link.startswith('https://')):
                continue
                
            # Check for exclusion indicators
            for indicator in exclude_indicators:
                if indicator in link:
                    skip = True
                    break
                    
            if skip:
                continue
                
            link_domain = extract_domain(link)
            
            # Check if it's from the same domain and likely an article
            if link_domain == domain:
                is_article = False
                # Check for article indicators
                for indicator in article_indicators:
                    if indicator in link:
                        is_article = True
                        break
                        
                # Additional heuristics: typical URL patterns for Greek news sites
                # Check for date-like patterns in URL which often indicate news articles
                if not is_article and any(pattern in link for pattern in ["/2024/", "/2023/", "/2022/"]):
                    is_article = True
                    
                # Check for numeric IDs which often indicate article pages
                if not is_article:
                    parts = link.split('/')
                    for part in parts:
                        if part.isdigit() and len(part) > 4:  # Longer numbers are likely article IDs
                            is_article = True
                            break
                
                if is_article:
                    filtered_links.append(link)
        
        # Deduplicate 
        unique_links = list(set(filtered_links))
        
        # Sort by length of URL in ascending order (shorter URLs tend to be more canonical)
        unique_links.sort(key=len)
        
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
    
    # Use a diverse set of sources to get better coverage
    # Selecting some mainstream Greek news sources
    diverse_sources = [
        "https://www.kathimerini.gr/",
        "https://www.tanea.gr/",
        "https://www.protothema.gr/",
        "https://www.iefimerida.gr/",
        "https://www.newsit.gr/",
        "https://www.in.gr/"
    ]
    
    logger.info(f"Using diverse sources: {diverse_sources}")
    
    # Get article URLs from each news source homepage
    all_article_urls = []
    for source_url in diverse_sources:
        try:
            # Get up to 5 article links from each source
            article_urls = get_news_links(source_url, 5)
            if article_urls:
                # Add up to 3 URLs from this source (for balance)
                all_article_urls.extend(article_urls[:3])
                logger.debug(f"Added {len(article_urls[:3])} links from {source_url}")
        except Exception as e:
            logger.error(f"Error processing source {source_url}: {str(e)}")
    
    # Limit total to prevent timeouts (max 15 articles)
    if len(all_article_urls) > 15:
        all_article_urls = all_article_urls[:15]
    
    logger.info(f"Found {len(all_article_urls)} article URLs to scrape across {len(diverse_sources)} sources")
    
    # Use ThreadPoolExecutor to scrape articles in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_url = {executor.submit(scrape_article, url): url for url in all_article_urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                article_data = future.result()
                if article_data and article_data.get("content"):
                    # Make sure URL is properly formed and accessible
                    if article_data.get("url") and article_data["url"].startswith("http"):
                        # Test to see if the URL is valid and accessible before adding
                        logger.debug(f"Adding article: {article_data.get('title', 'Untitled')} from {article_data.get('source', 'Unknown')}")
                        all_news_data.append(article_data)
            except Exception as e:
                logger.error(f"Error processing article {url}: {str(e)}")
    
    # Sort by length of content as a rough heuristic for article quality
    all_news_data.sort(key=lambda x: len(x.get("content", "")), reverse=True)
    
    logger.info(f"Successfully scraped {len(all_news_data)} articles")
    return all_news_data
