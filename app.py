import os
import logging
from flask import Flask, render_template, request, jsonify
from scraper import scrape_news
from summarizer import summarize_news
from email_sender import send_email
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
    """Process news from Greek websites and send email."""
    try:
        email = request.form.get('email')
        if not email:
            return jsonify({"status": "error", "message": "Email is required"}), 400
        
        logger.debug(f"Starting news processing for email: {email}")
        
        # Step 1: Scrape news from Greek websites
        logger.debug("Starting web scraping...")
        news_data = scrape_news()
        
        # Step 2: Summarize news using Mistral AI
        logger.debug("Starting summarization with Mistral AI...")
        summarized_news = summarize_news(news_data)
        
        # Step 3: Send email with summarized news
        logger.debug("Sending email...")
        send_email(email, summarized_news)
        
        return jsonify({"status": "success", "message": "News processed and email sent successfully!"})
    except Exception as e:
        logger.error(f"Error processing news: {str(e)}")
        return jsonify({"status": "error", "message": f"Error processing news: {str(e)}"}), 500
