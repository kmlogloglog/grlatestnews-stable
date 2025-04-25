import os
import logging
import json
import requests
import re
import html
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

# Mistral AI API configuration
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def create_fallback_output(articles: List[Dict[str, Any]], error_message: str) -> Dict[str, Any]:
    """
    Create a simple HTML fallback for displaying articles when API fails.
    
    Args:
        articles: The list of articles to display
        error_message: The error message to show
        
    Returns:
        Dictionary with HTML content for displaying the articles directly
    """
    # Create a simple HTML structure to display the articles
    soup = BeautifulSoup("<h1>Greek Domestic News Summary</h1>", 'html.parser')
    
    # Add error message
    error_p = soup.new_tag("p")
    error_p["style"] = "color: #e74c3c; font-weight: bold;"
    error_p.string = f"Unable to summarize news: {error_message}"
    soup.append(error_p)
    
    retry_p = soup.new_tag("p")
    retry_p.string = "Here are the raw news articles we found:"
    soup.append(retry_p)
    
    # Add a limited number of articles
    limit = min(12, len(articles))
    for i, article in enumerate(articles[:limit], 1):
        # Title
        h2 = soup.new_tag("h2")
        h2.string = f"{i}. {article.get('title', 'Untitled Article')}"
        soup.append(h2)
        
        # Source
        source_p = soup.new_tag("p")
        source_p["class"] = "news-source"
        source_p.string = f"Source: {article.get('source', 'Unknown Source')}"
        soup.append(source_p)
        
        # URL
        url = article.get('url', '')
        if url:
            a = soup.new_tag("a")
            a["href"] = url
            a["target"] = "_blank"
            a["class"] = "read-more"
            a.string = "Read Full Article"
            soup.append(a)
    
    return {
        "html_content": str(soup),
        "article_count": len(articles),
        "sources": list(set(article.get('source', '') for article in articles)),
        "error": error_message
    }

def clean_html_content(html_content):
    """
    Clean and process the HTML content to ensure it's well-formed.
    
    Args:
        html_content: Raw HTML content from the API
        
    Returns:
        Cleaned and properly formatted HTML content
    """
    try:
        # Check if content already has HTML tags
        has_html = '<h1>' in html_content or '<h2>' in html_content
        
        if has_html:
            # The response might contain explanatory text before the actual HTML content
            # Let's try to extract just the HTML part
            
            # Find the HTML content start - usually with the first <h1> tag
            html_start = html_content.find('<h1>')
            if html_start == -1:
                # If no <h1>, try to find another HTML tag
                for tag in ['<h2>', '<div>', '<p>']:
                    html_start = html_content.find(tag)
                    if html_start != -1:
                        break
            
            # If we found an HTML tag, extract from there to the end
            if html_start != -1:
                html_content = html_content[html_start:]
                logger.info("Extracted HTML content starting with a tag")
            
            # Parse with BeautifulSoup to clean up the HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Make sure all links have target="_blank" and proper class
            for a_tag in soup.find_all('a'):
                if 'href' in a_tag.attrs:
                    # Keep the URL exactly as is but add target and class
                    a_tag['target'] = '_blank'
                    a_tag['class'] = 'read-more'
            
            # Make sure we have a title
            h1_tag = soup.find('h1')
            if not h1_tag:
                h1_tag = soup.new_tag('h1')
                h1_tag.string = 'Greek Domestic News Summary'
                soup.insert(0, h1_tag)
            
            # Count news stories and log
            h2_tags = soup.find_all('h2')
            logger.info(f"Found {len(h2_tags)} news stories in the response")
            
            # Check for proper formatting
            if len(h2_tags) < 1:
                # If there are no h2 tags, the HTML might be malformed
                # Let's create a simple structured summary instead
                logger.warning("No news items found in HTML response, creating fallback structure")
                
                fallback_soup = BeautifulSoup("<h1>Greek Domestic News Summary</h1>", 'html.parser')
                
                # Add a paragraph explaining the issue
                p_tag = soup.new_tag('p')
                p_tag.string = "The content could not be properly formatted. Please try again."
                fallback_soup.append(p_tag)
                
                # Add whatever content we received 
                pre_tag = soup.new_tag('pre')
                pre_tag.string = html_content
                fallback_soup.append(pre_tag)
                
                return str(fallback_soup)
            
            return str(soup)
            
        else:
            # If response doesn't contain HTML, wrap it in a simple structure
            logger.warning("Response doesn't contain HTML tags, creating structured content")
            clean_content = html_content.replace('<', '&lt;').replace('>', '&gt;')
            return f"<h1>Greek Domestic News Summary</h1><p>The content could not be properly formatted.</p><pre>{clean_content}</pre>"
    
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {str(e)}")
        # Return a safe fallback in case of any error
        return "<h1>Greek Domestic News Summary</h1><p>There was an error processing the news content. Please try again.</p>"

def summarize_news(news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarize news data using Mistral AI with a focus on translation to English.
    
    Args:
        news_data: List of dictionaries containing news articles
        
    Returns:
        Dictionary with summarized news content
    """
    if not MISTRAL_API_KEY:
        logger.error("Mistral API key not found in environment variables")
        # Use direct display as fallback if no API key
        return create_direct_output(news_data, "No Mistral API key provided")
    
    try:
        # Keep system prompt very simple
        system_prompt = """
        Translate Greek news to English and format as HTML with exactly 12 news entries.
        """
        
        # Prepare the user prompt with the articles
        user_prompt = "Here are the Greek news articles to translate and summarize:\n\n"
        
        # Limit to 20 articles to avoid token limits
        max_articles = min(20, len(news_data))
        selected_articles = news_data[:max_articles]
        
        # Add articles to the prompt with minimal content to reduce token usage
        for i, article in enumerate(selected_articles, 1):
            user_prompt += f"ARTICLE {i}\n"
            user_prompt += f"Title: {article.get('title', 'Unknown Title')}\n"
            user_prompt += f"Source: {article.get('source', 'Unknown Source')}\n"
            user_prompt += f"URL: {article.get('url', 'Unknown URL')}\n"
            
            # Use much shorter content snippets to save tokens
            content = article.get('content', '')
            if content:
                # Just use the first 200 characters for translation context
                snippet = content[:200] + "..." if len(content) > 200 else content
                user_prompt += f"Content: {snippet}\n\n"
            else:
                user_prompt += "Content: [No content available]\n\n"
        
        # Add extremely explicit instructions to guarantee formatting
        user_prompt += """
        TRANSLATE EACH ARTICLE'S TITLE AND CONTENT FROM GREEK TO ENGLISH.
        
        FORMAT YOUR RESPONSE AS PURE HTML WITH EXACTLY 12 NEWS STORIES.
        
        YOU MUST FOLLOW THIS EXACT FORMAT:
        
<h1>Greek Domestic News Summary</h1>

<h2>1. [TRANSLATED TITLE IN ENGLISH]</h2>
<p>[2-3 SENTENCE SUMMARY IN ENGLISH]</p>
<p class="news-source">Source: [SOURCE NAME]</p>
<a href="[EXACT_ORIGINAL_URL]" target="_blank" class="read-more">Read Full Article</a>

<h2>2. [TRANSLATED TITLE IN ENGLISH]</h2>
<p>[2-3 SENTENCE SUMMARY IN ENGLISH]</p>
<p class="news-source">Source: [SOURCE NAME]</p>
<a href="[EXACT_ORIGINAL_URL]" target="_blank" class="read-more">Read Full Article</a>

<h2>3. [TRANSLATED TITLE IN ENGLISH]</h2>
<p>[2-3 SENTENCE SUMMARY IN ENGLISH]</p>
<p class="news-source">Source: [SOURCE NAME]</p>
<a href="[EXACT_ORIGINAL_URL]" target="_blank" class="read-more">Read Full Article</a>

        [AND SO ON UNTIL YOU HAVE EXACTLY 12 STORIES TOTAL]
        
        CRITICAL RULES:
        1. START DIRECTLY WITH <h1> TAG - NO INTRODUCTORY TEXT
        2. END WITH THE LAST </a> TAG - NO CONCLUSION OR EXPLANATION
        3. INCLUDE EXACTLY 12 NEWS STORIES - EACH WITH h2, p, p.news-source, AND a TAGS
        4. TRANSLATE ALL GREEK TEXT TO ENGLISH
        5. KEEP ALL URLS EXACTLY AS PROVIDED - DO NOT MODIFY THEM
        
        FINAL CHECK: COUNT YOUR STORIES AND VERIFY YOU HAVE EXACTLY 12.
        """
        
        # Make the API request
        logger.debug("Sending request to Mistral AI")
        response = requests.post(
            MISTRAL_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MISTRAL_API_KEY}"
            },
            json={
                "model": "mistral-small",  # Using smaller model for reliability
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,       # Lower temperature for more deterministic results
                "max_tokens": 4000        # Need enough tokens for 12 stories
            },
            timeout=90  # 90 second timeout
        )
        
        response.raise_for_status()
        result = response.json()
        logger.debug("Received response from Mistral AI")
        
        # Extract and clean the content
        summary_content = result["choices"][0]["message"]["content"]
        cleaned_summary = clean_html_content(summary_content)
        
        # Verify we got proper HTML with multiple news entries
        soup = BeautifulSoup(cleaned_summary, 'html.parser')
        story_count = len(soup.find_all('h2'))
        
        if story_count >= 3:  # We at least got a few stories
            logger.info(f"API successfully returned {story_count} translated news stories")
            return {
                "html_content": cleaned_summary,
                "article_count": story_count,
                "sources": list(set(article.get('source', '') for article in selected_articles)),
                "translated": True
            }
        else:
            # If fewer than 3 stories, something likely went wrong with the response
            logger.warning(f"API returned only {story_count} stories, using fallback")
            return create_direct_output(news_data, "API returned insufficient stories")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to Mistral AI: {str(e)}")
        return create_direct_output(news_data, f"API Connection Error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error in summarization: {str(e)}")
        return create_direct_output(news_data, f"Summarization Error: {str(e)}")


def create_direct_output(news_data: List[Dict[str, Any]], error_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a direct HTML output from the raw news data without using the API.
    This function simply organizes the scraped articles with minimal processing.
    
    Args:
        news_data: List of dictionaries containing news articles
        error_message: Optional error message to display
        
    Returns:
        Dictionary with HTML content for displaying the articles directly
    """
    # Create a simple HTML structure
    soup = BeautifulSoup("<h1>Greek Domestic News Summary</h1>", 'html.parser')
    
    # Add a simple explanation
    note_p = soup.new_tag("p")
    note_p["style"] = "font-style: italic; margin-bottom: 20px;"
    note_p.string = "Here are the most recent news articles from Greek sources:"
    soup.append(note_p)
    
    # If there's an error message, display it
    if error_message:
        error_p = soup.new_tag("p")
        error_p["style"] = "color: #e74c3c; font-weight: bold; margin-bottom: 20px;"
        error_p.string = f"Note: Translation unavailable. ({error_message})"
        soup.append(error_p)
    
    # Select up to 12 articles
    limit = min(12, len(news_data))
    for i, article in enumerate(news_data[:limit], 1):
        # Extract title and try to translate using a simple rule-based approach
        title = article.get('title', 'Untitled Article')
        
        # Add the heading with number
        h2 = soup.new_tag("h2")
        h2.string = f"{i}. {title}"
        soup.append(h2)
        
        # Add a short excerpt from the content if available
        content = article.get('content', '')
        if content:
            # Get first 2-3 sentences or a small excerpt
            sentences = re.split(r'[.!?]+', content)
            excerpt = '. '.join(sentences[:min(3, len(sentences))]).strip()
            
            if not excerpt:  # Fallback if split didn't work
                excerpt = content[:300] + "..." if len(content) > 300 else content
                
            p = soup.new_tag("p")
            p.string = excerpt
            soup.append(p)
        
        # Add source
        source_p = soup.new_tag("p")
        source_p["class"] = "news-source"
        source_p.string = f"Source: {article.get('source', 'Unknown Source')}"
        soup.append(source_p)
        
        # Add link to original article
        url = article.get('url', '')
        if url:
            a = soup.new_tag("a")
            a["href"] = url
            a["target"] = "_blank"
            a["class"] = "read-more"
            a.string = "Read Full Article"
            soup.append(a)
    
    return {
        "html_content": str(soup),
        "article_count": len(news_data),
        "sources": list(set(article.get('source', '') for article in news_data)),
        "direct_mode": True
    }
