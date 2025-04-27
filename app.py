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
                print("No news articles were successfully scraped")
                logger.warning("No news articles were successfully scraped")
                return jsonify({
                    "status": "error",
                    "message": "No news articles could be found for today or as latest. Please try again later, or relax the filter."
                }), 200, response_headers
            logger.info(f"Successfully scraped {len(news_data)} articles")
        except Exception as e:
            print(f"Error during web scraping: {str(e)}")
            logger.error(f"Error during web scraping: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Error retrieving news content: {str(e)}"
            }), 500, response_headers
        # Limit the number of articles to process (for memory safety)
        news_data = news_data[:3]
        # Step 2: Summarize news using Mistral AI
        logger.info("Starting summarization with Mistral AI...")
        try:
            summarized_news = summarize_news(news_data)
            if not summarized_news or "html_content" not in summarized_news:
                print("News summarization failed or returned invalid data")
                logger.warning("News summarization failed or returned invalid data")
                return jsonify({
                    "status": "error",
                    "message": "Failed to summarize news content. Please try again later."
                }), 500, response_headers
            logger.info("News summarization completed successfully")
        except Exception as e:
            print(f"Error during summarization: {str(e)}")
            logger.error(f"Error during summarization: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Error summarizing news: {str(e)}"
            }), 500, response_headers
        print("News processed successfully!")
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
