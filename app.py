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
        # Always set content type to ensure proper JSON parsing
        response_headers = {"Content-Type": "application/json"}
        
        # Get email from form
        email = request.form.get('email')
        if not email:
            logger.warning("Form submission missing email")
            return jsonify({"status": "error", "message": "Email address is required"}), 400, response_headers
        
        # Validate email format
        from email_validator import validate_email, EmailNotValidError
        try:
            validate_email(email)
        except EmailNotValidError as e:
            logger.warning(f"Invalid email format: {email}")
            return jsonify({"status": "error", "message": f"Invalid email address: {str(e)}"}), 400, response_headers
            
        logger.info(f"Starting news processing for email: {email}")
        
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
        
        # Step 3: Send email with summarized news
        email_sent = False
        email_error = None
        
        logger.info(f"Attempting to send email to {email}...")
        try:
            send_email(email, summarized_news)
            logger.info(f"Email sent successfully to {email}")
            email_sent = True
        except Exception as e:
            email_error = str(e)
            logger.error(f"Error sending email: {email_error}")
            # Continue with fallback instead of returning error immediately
        
        # Prepare response
        if email_sent:
            # Email sent successfully
            return jsonify({
                "status": "success",
                "message": "News processed and email sent successfully! Please check your inbox (and spam folder) for the Greek news summary."
            }), 200, response_headers
        else:
            # Email failed - return content for fallback display
            logger.info("Email sending failed. Returning HTML content for fallback display.")
            return jsonify({
                "status": "error",
                "message": f"Could not send email: {email_error}. Displaying summary below instead.",
                "html_content": summarized_news["html_content"]
            }), 200, response_headers
            
    except Exception as e:
        logger.error(f"Unexpected error in process_news: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": "An unexpected error occurred. Please try again later."
        }), 500, response_headers
