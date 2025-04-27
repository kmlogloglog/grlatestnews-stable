import os
import logging
from flask import Flask, render_template, request, jsonify
from scraper import scrape_news
from summarizer import summarize_news
import config
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")
# Allow all hosts for proxy/browser preview compatibility
app.config['SERVER_NAME'] = None
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    """Render the landing page."""
    return render_template('index.html')

@app.route('/process_news', methods=['POST'])
def process_news():
    try:
        print("/process_news endpoint called")
        response_headers = {"Content-Type": "application/json"}
        logger.info("Starting news processing with extended timeout...")
        # Step 1: Scrape news from Greek websites
        logger.info("Starting web scraping...")
        try:
            news_data = scrape_news(
                max_articles_per_source=config.MAX_ARTICLES_PER_SOURCE,
                total_articles_target=config.MAX_TOTAL_ARTICLES
            )
            if not news_data or len(news_data) == 0:
                return jsonify({
                    "status": "error",
                    "message": "No news articles could be scraped."
                }), 500, response_headers
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Error retrieving news content: {str(e)}"
            }), 500, response_headers
        logger.info(f"Passing {len(news_data)} articles to summarizer...")
        try:
            summarized_news = summarize_news(news_data)
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Error during summarization: {str(e)}"
            }), 500, response_headers
        return jsonify({
            "status": "success",
            "message": "News processed successfully!",
            "html_content": summarized_news["html_content"]
        }), 200, response_headers
    except Exception as e:
        import traceback
        print('Exception in /process_news:', e)
        traceback.print_exc()
        logger.error(f"Unexpected error in process_news: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred. Please try again later.",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500
