import os
import logging
import json
import requests
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

# Mistral AI API configuration
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

def clean_html_content(html_content):
    """
    Clean and process the HTML content to ensure it's well-formed.
    
    Args:
        html_content: Raw HTML content from the API
        
    Returns:
        Cleaned and properly formatted HTML content
    """
    try:
        # Don't manipulate the content at all if already in HTML format
        if html_content.strip().startswith('<'):
            # Just add minimal safety attributes to links without changing URLs
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Only add target="_blank" to links without changing the URLs
            for a_tag in soup.find_all('a'):
                if 'href' in a_tag.attrs:
                    a_tag['target'] = '_blank'
                    
            # Add title if missing
            if not soup.find('h1'):
                title_div = soup.new_tag('h1')
                title_div.string = 'Greek Domestic News Summary'
                soup.insert(0, title_div)
                
            return str(soup)
        else:
            # If not HTML, just wrap in simple tags
            return f"<div class='news-summary'><h1>Greek Domestic News Summary</h1><p>{html_content}</p></div>"
    except Exception as e:
        logger.error(f"Error cleaning HTML content: {str(e)}")
        # If there's an error in cleaning, return original content
        return html_content

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
    
    Your output should be structured in HTML format with proper formatting and include a link to the original article.
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
        
        # Limit content length to avoid token limits
        content = article.get('content', '')
        if content:
            if len(content) > 1500:
                content = content[:1500] + "..."
            user_prompt += f"Content:\n{content}\n\n"
        else:
            user_prompt += "Content: [No content available]\n\n"
    
    user_prompt += """
    Please analyze these articles and provide:
    1. EXACTLY 12 news stories about Greek domestic affairs in English. You must ALWAYS include 12 stories, not less.
    2. For each story include: a title, 2-3 sentence summary, source, and URL to original article
    3. Format the output as HTML with proper styling and formatting
    4. For each article, ALWAYS include the EXACT and COMPLETE URL from the article data, formatted exactly like this:
       <a href="THE_EXACT_COMPLETE_URL" target="_blank" class="read-more">Read Full Article</a>
    5. Make absolutely sure to retain the EXACT URLs as provided without modification, do not change them at all
    6. Do not modify or rewrite any URLs, even if they appear to be incorrect
    7. Prioritize news occurring INSIDE Greece and avoid international news unless it directly affects Greece
    8. Only include factual information from the articles
    9. Your response MUST have exactly 12 stories, please check your work carefully
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
                "model": "mistral-small",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,  # Low temperature for factual responses
                "max_tokens": 3072  # Increased token limit for 12 stories with details
            },
            timeout=120  # Increased timeout for potentially large responses
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
        raise Exception(f"Failed to connect to Mistral AI: {str(e)}")
    
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing Mistral AI response: {str(e)}")
        raise Exception(f"Failed to parse Mistral AI response: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {str(e)}")
        raise Exception(f"Summarization failed: {str(e)}")
