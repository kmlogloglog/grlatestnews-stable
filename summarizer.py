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
    You are an expert news analyst and translator. Your task is to:
    
    1. Analyze a collection of Greek news articles
    2. Summarize and translate the content to English
    3. Select the top 10 most important news stories
    4. For each story, provide a concise title and a 2-3 sentence summary
    5. Focus only on facts, no opinions or creativity
    6. Group related stories together
    7. Include the source website for each story
    
    Your output should be structured in HTML format with proper formatting.
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
    1. The top 10 most important news stories in English
    2. For each story include: a title, 2-3 sentence summary, and source
    3. Format the output as HTML that can be sent via email
    4. Group related stories when appropriate
    5. Only include factual information from the articles
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
                "max_tokens": 2048
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
