import os
import logging
import json
import requests
import re
import html
import traceback
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# Configure logging (ensure this matches or is configured globally)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mistral AI API configuration
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# --- HTML Cleaning Function (Keep as is, it's good) ---
def clean_html_content(html_content: str) -> str:
    """Clean and process the HTML content from the API response."""
    try:
        is_likely_html = '<' in html_content and '>' in html_content
        if not is_likely_html:
             logger.warning("Response doesn't seem to contain HTML tags. Wrapping raw content.")
             clean_content = html.escape(html_content)
             return f"<h1>Greek Domestic News Summary</h1><p>The content received from the AI was not in the expected HTML format. Displaying raw response:</p><pre>{clean_content}</pre>"

        html_start_index = -1
        potential_starts = ['<h1', '<div', '<p', '<h2']
        for tag_start in potential_starts:
            html_start_index = html_content.find(tag_start)
            if html_start_index != -1: break

        if html_start_index > 0:
            logger.info(f"Detected potential introductory text. Extracting from index {html_start_index}.")
            html_content = html_content[html_start_index:]
        elif html_start_index == -1:
             logger.warning("Could not find standard starting HTML tags. Processing content as is.")

        soup = BeautifulSoup(html_content, 'html.parser')

        for a_tag in soup.find_all('a'):
            if a_tag.has_attr('href'):
                a_tag['target'] = '_blank'
                a_tag['class'] = 'read-more'

        h1_tag = soup.find('h1')
        if not h1_tag:
            logger.warning("No H1 title found. Adding a default title.")
            new_h1 = soup.new_tag('h1')
            new_h1.string = 'Greek Domestic News Summary'
            body_tag = soup.find('body')
            if body_tag: body_tag.insert(0, new_h1)
            else: soup.insert(0, new_h1)

        h2_tags = soup.find_all('h2')
        logger.info(f"Found {len(h2_tags)} news items (H2 tags) in cleaned HTML.")

        if not h2_tags:
            logger.warning("Cleaned HTML does not contain any H2 tags (news items). Returning message.")
            fallback_soup = BeautifulSoup("<h1>Greek Domestic News Summary</h1>", 'html.parser')
            p_tag = fallback_soup.new_tag('p')
            p_tag.string = "The AI response did not contain formatted news items as expected."
            fallback_soup.append(p_tag)
            pre_tag = fallback_soup.new_tag('pre')
            pre_tag.string = html.escape(html_content[:1000]) + ("..." if len(html_content) > 1000 else "")
            fallback_soup.append(pre_tag)
            return str(fallback_soup)

        return str(soup)

    except Exception as e:
        logger.error(f"Error cleaning HTML content: {str(e)}", exc_info=True)
        return f"<h1>Greek Domestic News Summary</h1><p>There was an error processing the news content received from the AI. Details: {html.escape(str(e))}</p>"


# --- Direct Output Fallback (Keep as is, maybe slight wording tweaks) ---
def create_direct_output(news_data: List[Dict[str, Any]], error_message: Optional[str] = None) -> Dict[str, Any]:
    """Creates HTML output directly from raw news data when API/translation fails."""
    logger.info(f"Creating direct output. Reason: {error_message or 'Summarization not attempted'}")
    soup = BeautifulSoup("<h1>Greek Domestic News Summary</h1>", 'html.parser')

    note_p = soup.new_tag("p", style="font-style: italic; margin-bottom: 15px;")
    note_p.string = "Displaying the latest raw news articles from Greek sources:"
    soup.append(note_p)

    if error_message:
        error_p = soup.new_tag("p", style="color: #e74c3c; font-weight: bold; margin-bottom: 20px; border: 1px solid #e74c3c; padding: 10px; background-color: #fadedb;")
        # Make error messages slightly more user-friendly
        if "API Key" in error_message:
             display_error = "AI Summarization failed: Invalid API Key."
        elif "API Error 429" in error_message:
             display_error = "AI Summarization failed: Rate limit reached. Please try again later."
        elif "API Error 5" in error_message: # Catch 5xx errors
             display_error = "AI Summarization failed: Temporary server issue. Please try again later."
        elif "Network Timeout" in error_message:
             display_error = "AI Summarization failed: Network connection timed out."
        elif "Network Error" in error_message:
             display_error = "AI Summarization failed: Could not connect to the AI service."
        elif "format issue" in error_message or "invalid" in error_message.lower():
             display_error = f"AI Summarization failed: Unexpected response format. ({error_message})"
        else:
             display_error = f"AI Summarization failed. ({error_message})"
        error_p.string = f"Note: {display_error}"
        soup.append(error_p)

    if not news_data:
        no_data_p = soup.new_tag("p")
        no_data_p.string = "No news articles were found to display."
        soup.append(no_data_p)
    else:
        limit = min(12, len(news_data))
        logger.info(f"Displaying {limit} out of {len(news_data)} available articles directly.")
        for i, article in enumerate(news_data[:limit], 1):
            title = article.get('title', 'Untitled Article')
            h2 = soup.new_tag("h2")
            h2.string = f"{i}. {title}"
            soup.append(h2)

            content = article.get('content', '')
            if content:
                sentences = re.split(r'(?<=[.!?])\s+', content)
                excerpt = '. '.join(sentences[:2]).strip()
                if len(excerpt) < 50 and len(sentences) > 2: excerpt = '. '.join(sentences[:3]).strip()
                if not excerpt: excerpt = content[:250].strip() + ("..." if len(content) > 250 else "")
                p = soup.new_tag("p")
                p.string = excerpt
                soup.append(p)

            source = article.get('source', 'Unknown Source')
            source_p = soup.new_tag("p", attrs={"class": "news-source"})
            source_p.string = f"Source: {source}"
            soup.append(source_p)

            url = article.get('url', '')
            if url:
                a = soup.new_tag("a", href=url, target="_blank", attrs={"class": "read-more"})
                a.string = "Read Full Article (Original Source)"
                soup.append(a)

    return {
        "html_content": str(soup),
        "article_count": len(news_data),
        "sources": list(set(article.get('source', '') for article in news_data if article.get('source'))),
        "direct_mode": True,
        "error": error_message
    }


# --- Main Summarization Function (Simplified API Logic) ---
def summarize_news(news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarizes and translates Greek news using Mistral AI. Uses direct output as fallback.

    Args:
        news_data: List of dictionaries containing news articles.

    Returns:
        Dictionary with summarized/translated HTML content or direct output on failure.
    """
    if not news_data:
        logger.warning("No news data provided to summarize.")
        return create_direct_output([], "No articles found to process.")

    if not MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY environment variable not set or empty.")
        return create_direct_output(news_data, "Missing Mistral API Key") # Clearer message
    else:
        logger.info(f"Mistral API Key found (masked: ...{MISTRAL_API_KEY[-4:] if len(MISTRAL_API_KEY) > 4 else '****'})")
        # Removed the pre-validation call

    response = None # Initialize response
    try:
        # --- Prepare Prompt (Keep the detailed instructions) ---
        system_prompt = """
        You are an expert translator and news summarizer. Translate Greek news articles into English and format them as clean HTML.
        Follow the user's instructions precisely. Output *only* the HTML structure requested, starting with <h1> and ending with the last </a> tag. No extra text.
        """
        user_prompt = "Translate the following Greek news articles into English and create a summary HTML page.\n\n"
        max_articles_to_send = 20
        selected_articles = news_data[:min(max_articles_to_send, len(news_data))]
        logger.info(f"Preparing {len(selected_articles)} articles for the API request.")

        for i, article in enumerate(selected_articles, 1):
            user_prompt += f"--- ARTICLE {i} ---\n"
            user_prompt += f"TITLE_GR: {article.get('title', 'No Title Provided')}\n"
            user_prompt += f"SOURCE: {article.get('source', 'Unknown Source')}\n"
            user_prompt += f"URL: {article.get('url', 'No URL Provided')}\n"
            content = article.get('content', '')
            snippet = (content[:250].strip() + "...") if len(content) > 250 else content.strip()
            user_prompt += f"CONTENT_SNIPPET_GR: {snippet if snippet else '[No Content Snippet]'}\n\n"

        user_prompt += """
--- INSTRUCTIONS ---
1. Translate TITLE_GR to English.
2. Write a concise 2-3 sentence English summary based on TITLE_GR and CONTENT_SNIPPET_GR.
3. Format output as *pure HTML*, with exactly 12 news entries (use first 12 articles provided).
4. Use this exact structure for each entry:
   <h2>[NUMBER]. [TRANSLATED_ENGLISH_TITLE]</h2>
   <p>[CONCISE_ENGLISH_SUMMARY]</p>
   <p class="news-source">Source: [ORIGINAL_SOURCE_NAME]</p>
   <a href="[EXACT_ORIGINAL_URL]" target="_blank" class="read-more">Read Full Article</a>
5. Start response *directly* with: <h1>Greek Domestic News Summary</h1>
6. Ensure exactly 12 entries with the h2, p, p, a structure. Use exact original URLs.
7. No text before <h1> or after the final </a>.
8. Double-check: Output must be valid HTML, one <h1>, twelve <h2> sections.
"""
        # --- Make API Call ---
        logger.info("Sending request to Mistral API...")
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {MISTRAL_API_KEY}"}
        payload = {
            "model": "mistral-large-latest",
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.3,
            "max_tokens": 4096,
            "response_format": {"type": "text"}
        }
        api_url = "https://api.mistral.ai/v1/chat/completions"

        response = requests.post(api_url, headers=headers, json=payload, timeout=120) # Single attempt

        logger.info(f"Received response from Mistral API. Status Code: {response.status_code}")

        # --- Process Response ---
        # Raise HTTPError for bad responses (4xx or 5xx) - caught by RequestException handler below
        response.raise_for_status()

        # Status is 200 if we reach here
        response_data = response.json() # Parse JSON

        if not response_data.get("choices") or not response_data["choices"][0].get("message"):
            logger.error(f"API response missing expected fields. Data: {response_data}")
            return create_direct_output(news_data, "API response structure was invalid.")

        summary_content = response_data["choices"][0]["message"]["content"]
        finish_reason = response_data["choices"][0].get("finish_reason", "unknown")
        logger.info(f"API call finished. Reason: {finish_reason}")
        if finish_reason == "length": logger.warning("API response may be truncated (finish_reason='length').")

        logger.debug(f"Raw API Response Content:\n----\n{summary_content[:500]}...\n----")

        cleaned_summary_html = clean_html_content(summary_content)

        soup_check = BeautifulSoup(cleaned_summary_html, 'html.parser')
        story_count = len(soup_check.find_all('h2'))
        min_expected_stories = 5

        if story_count >= min_expected_stories:
            logger.info(f"Successfully processed API response. Found {story_count} stories.")
            return {
                "html_content": cleaned_summary_html,
                "article_count": story_count,
                "sources": list(set(a.get('source', '') for a in selected_articles if a.get('source'))),
                "translated": True,
                "error": None
            }
        else:
            logger.warning(f"API response parsing yielded only {story_count} stories (< {min_expected_stories}). Falling back.")
            return create_direct_output(news_data, f"API response format issue (found {story_count} stories)")

    # --- Exception Handling (Catches network errors, status errors, JSON errors) ---
    except requests.exceptions.Timeout:
        logger.error("Network error: Request to Mistral API timed out.")
        return create_direct_output(news_data, "Network Timeout") # Simpler message
    except requests.exceptions.HTTPError as e:
        # Handle non-200 status codes here
        status_code = e.response.status_code
        error_body_text = e.response.text[:500] # Get snippet of error body
        logger.error(f"Mistral API HTTP error: Status Code: {status_code} - Body: {error_body_text}")
        fallback_msg = f"API Error {status_code}"
        if status_code == 401: fallback_msg = "Invalid Mistral API Key" # Specific message
        if status_code == 429: fallback_msg += " (Rate Limit Reached)"
        if status_code >= 500: fallback_msg += " (Server Issue)"
        return create_direct_output(news_data, fallback_msg)
    except requests.exceptions.RequestException as e:
        # Handle other network errors (connection, SSL, etc.)
        logger.error(f"Network error connecting to Mistral API: {e}")
        return create_direct_output(news_data, f"Network Error") # Simpler message
    except json.JSONDecodeError as e:
        # Handle errors parsing the successful (200) response body
        logger.error(f"Error decoding JSON response from API (Status 200 likely): {e}")
        raw_response = response.text[:500] if response else "Response object unavailable"
        logger.error(f"Raw response snippet causing JSON error: {raw_response}")
        return create_direct_output(news_data, "Invalid JSON response from AI service")
    except Exception as e:
        # Catch any other unexpected errors
        logger.exception(f"Unexpected error during Mistral AI processing: {e}") # Use logger.exception for traceback
        return create_direct_output(news_data, f"Unexpected Error: {type(e).__name__}")


# --- Example Usage ---
if __name__ == '__main__':
    # Assume scrape_news is imported from news_scraper
    from news_scraper import scrape_news

    logger.info("Starting summarizer test...")
    # 1. Scrape news first
    logger.info("Running scraper...")
    scraped_articles = scrape_news(max_articles_per_source=3, total_articles_target=15) # Adjust params if needed

    # 2. Summarize the scraped news
    if scraped_articles:
        logger.info(f"Scraping finished, {len(scraped_articles)} articles found. Attempting summarization...")
        summary_result = summarize_news(scraped_articles)

        print("\n--- Summarizer Test Result ---")
        if summary_result.get("error"): print(f"Error Message: {summary_result['error']}")
        if summary_result.get("direct_mode"): print("Mode: Direct Output (Fallback)")
        else: print("Mode: AI Summarized Output")
        print(f"Article Count Displayed: {summary_result.get('article_count')}")
        print(f"Sources Included: {summary_result.get('sources')}")
        print("\n--- HTML Content Snippet ---")
        html_output = summary_result.get("html_content", "No HTML content generated.")
        print(html_output[:1000] + ('...' if len(html_output) > 1000 else ''))
        # Optionally save full HTML
        # with open("summary_output.html", "w", encoding="utf-8") as f:
        #     f.write(html_output)
        # print("\nFull HTML content saved to summary_output.html")
    else:
        print("\n--- Summarizer Test Result ---")
        print("Scraping failed to find any articles. Cannot summarize.")

    logger.info("Summarizer test finished.")