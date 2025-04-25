import os
import logging
from flask import Flask, render_template, request, jsonify
from scraper import scrape_news
from summarizer import summarize_news
import config

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

@app.route('/')
def index():
    """Render the landing page."""
    return render_template('index.html')

@app.route('/process_news', methods=['POST'])
def process_news():
    """Process news from Greek websites and display the summary."""
    try:
        # Always set content type to ensure proper JSON parsing
        response_headers = {"Content-Type": "application/json"}
        
        # Set a longer timeout for the entire request (5 minutes)
        logger.info("Starting news processing with extended timeout...")
        
        # Step 1: Scrape news from Greek websites
        logger.info("Starting web scraping...")
        try:
            news_data = scrape_news()
            if not news_data or len(news_data) == 0:
                logger.warning("No news articles were successfully scraped")
                return jsonify({
                    "status": "error", 
                    "message": "Could not retrieve news articles. Please try again later."
                }), 500, response_headers
            logger.info(f"Successfully scraped {len(news_data)} articles")
        except Exception as e:
            logger.error(f"Error during web scraping: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": f"Error retrieving news content: {str(e)}"
            }), 500, response_headers
        
        # Step 2: Summarize news using Mistral AI
        logger.info("Starting summarization with Mistral AI...")
        try:
            summarized_news = summarize_news(news_data)
            if not summarized_news or "html_content" not in summarized_news:
                logger.warning("News summarization failed or returned invalid data")
                return jsonify({
                    "status": "error", 
                    "message": "Failed to summarize news content. Please try again later."
                }), 500, response_headers
            logger.info("News summarization completed successfully")
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": f"Error summarizing news: {str(e)}"
            }), 500, response_headers
        
        # Return the summarized content
        return jsonify({
            "status": "success",
            "message": "News processed successfully!",
            "html_content": summarized_news["html_content"]
        }), 200, response_headers
            
    except Exception as e:
        logger.error(f"Unexpected error in process_news: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": "An unexpected error occurred. Please try again later."
        }), 500, response_headers
