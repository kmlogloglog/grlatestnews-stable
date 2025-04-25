import os
import logging
import json
import requests
import re
import html
from typing import List, Dict, Any
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
    Summarize news data using Mistral AI.
    
    Args:
        news_data: List of dictionaries containing news articles
        
    Returns:
        Dictionary with summarized news content
    """
    if not MISTRAL_API_KEY:
        logger.error("Mistral API key not found in environment variables")
        raise ValueError("Mistral API key not found")
    
    # Prepare system prompt
    system_prompt = """
    You are an expert news analyst and translator specializing in Greek domestic news. Your task is to:
    
    1. Analyze a collection of Greek news articles
    2. Prioritize news stories occurring INSIDE Greece and about Greek domestic affairs
    3. Summarize and translate the content to English
    4. Select the top 12 most important and UNIQUE news stories (avoid duplicates)
    5. For each story, provide a concise title and a 2-3 sentence summary
    6. Focus only on facts, no opinions or creativity
    7. Group related stories together
    8. Include the source website and original URL for each story
    
    CRITICAL INSTRUCTIONS:
    1. Your output must be PURE HTML ONLY - do not include any explanation text before or after the HTML
    2. Do not begin with "Here is the summary" or any similar text
    3. Start directly with the <h1> tag and end with the final </a> tag
    4. Follow the exact HTML structure specified in the prompt
    5. Verify that your output is valid HTML that can be directly injected into a webpage
    """
    
    # Prepare the input for Mistral AI
    # Format the news data into a structured prompt
    user_prompt = "Here are the news articles to summarize and translate to English:\n\n"
    
    # Limit the number of articles to avoid token limits
    max_articles = min(30, len(news_data))
    selected_articles = news_data[:max_articles]
    
    for i, article in enumerate(selected_articles, 1):
        user_prompt += f"ARTICLE {i}\n"
        user_prompt += f"Title: {article.get('title', 'Unknown Title')}\n"
        user_prompt += f"Source: {article.get('source', 'Unknown Source')}\n"
        user_prompt += f"URL: {article.get('url', 'Unknown URL')}\n"
        
        # Limit content length to avoid token limits - shorter to save tokens for output
        content = article.get('content', '')
        if content:
            if len(content) > 1000:  # Reduced from 1500
                content = content[:1000] + "..."
            user_prompt += f"Content:\n{content}\n\n"
        else:
            user_prompt += "Content: [No content available]\n\n"
    
    user_prompt += """
    YOUR MOST IMPORTANT TASK IS TO CREATE AN HTML PAGE WITH EXACTLY 12 NEWS STORIES.
    
    CRITICAL INSTRUCTIONS (FAILURE TO FOLLOW WILL RESULT IN REJECTION):
    1. Your response MUST contain EXACTLY 12 stories - no more, no less.
    2. You MUST use the exact HTML structure specified below.
    3. Your response must be pure HTML ONLY with no explanatory text.
    4. Start directly with <h1> and end with the last </a> tag.
    
    CONTENT GUIDELINES:
    1. Choose 12 different news stories about Greek domestic affairs 
    2. Prioritize news occurring INSIDE Greece (not international news)
    3. For each story include: title, 2-3 sentence summary, source, and original URL
    4. Use only factual information from the articles (no opinions or creativity)
    5. Translate everything to English
    
    RESPONSE FORMAT - FOLLOW THIS EXACTLY WITHOUT DEVIATION:
    
    <h1>Greek Domestic News Summary</h1>
    
    <h2>1. [STORY TITLE]</h2>
    <p>[2-3 SENTENCE SUMMARY]</p>
    <p class="news-source">Source: [SOURCE NAME]</p>
    <a href="[EXACT_ORIGINAL_URL]" target="_blank" class="read-more">Read Full Article</a>
    
    <h2>2. [STORY TITLE]</h2>
    <p>[2-3 SENTENCE SUMMARY]</p>
    <p class="news-source">Source: [SOURCE NAME]</p>
    <a href="[EXACT_ORIGINAL_URL]" target="_blank" class="read-more">Read Full Article</a>
    
    [CONTINUE THIS EXACT PATTERN FOR ALL 12 STORIES]
    
    FINAL VERIFICATION STEPS - YOU MUST DO THESE:
    1. Count and ensure you have EXACTLY 12 <h2> tags with 12 article titles
    2. Verify all 12 <a> tags have complete and unmodified URLs
    3. Check that your output has no extra explanatory text
    4. Confirm your response is pure HTML starting with <h1> and ending with the last </a>
    """
    
    # Make the request to Mistral AI
    try:
        logger.debug("Sending request to Mistral AI")
        response = requests.post(
            MISTRAL_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MISTRAL_API_KEY}"
            },
            json={
                "model": "mistral-small",  # More reliable model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,  # Standard temperature
                "max_tokens": 4096   # Standard token limit
            },
            timeout=300  # Increased timeout for large responses with 12 articles
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.debug("Received response from Mistral AI")
        
        # Extract the summary content
        summary_content = result["choices"][0]["message"]["content"]
        
        # Clean and wrap the summary content to ensure it's well-formed HTML
        cleaned_summary = clean_html_content(summary_content)
        
        # Prepare the final output
        output = {
            "html_content": cleaned_summary,
            "article_count": len(selected_articles),
            "sources": list(set(article.get('source', '') for article in selected_articles))
        }
        
        return output
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to Mistral AI: {str(e)}")
        # Instead of raising, provide a fallback simple display of raw news
        return create_fallback_output(selected_articles, f"API Connection Error: {str(e)}")
    
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing Mistral AI response: {str(e)}")
        # Provide fallback on parsing errors
        return create_fallback_output(selected_articles, f"API Response Error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {str(e)}")
        # Provide fallback for any unexpected errors
        return create_fallback_output(selected_articles, f"Summarization Error: {str(e)}")
