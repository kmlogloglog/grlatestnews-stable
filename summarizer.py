import os
import logging
import json
import requests
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Mistral AI API configuration
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

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
    1. The top 12 most important and UNIQUE news stories about Greek domestic affairs in English
    2. For each story include: a title, 2-3 sentence summary, source, and URL to original article
    3. Format the output as HTML with proper styling and formatting
    4. For each article, include a clearly visible "Read Full Article" link that opens the original URL in a new window
    5. Prioritize news occurring INSIDE Greece and avoid international news unless it directly affects Greece
    6. Avoid duplicate stories across different sources
    7. Only include factual information from the articles
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
        
        # Prepare the final output
        output = {
            "html_content": summary_content,
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
