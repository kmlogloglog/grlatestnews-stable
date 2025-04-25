import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Email configuration
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

def create_email_html(summarized_news: Dict[str, Any]) -> str:
    """
    Create the HTML content for the email.
    
    Args:
        summarized_news: Dictionary with summarized news data
        
    Returns:
        String with the HTML email content
    """
    html_content = summarized_news.get("html_content", "")
    
    # If html_content doesn't already have HTML structure, wrap it with proper HTML
    if not html_content.strip().startswith("<!DOCTYPE html>") and not html_content.strip().startswith("<html"):
        today_date = datetime.now().strftime("%A, %B %d, %Y")
        
        # Get sources info
        sources = summarized_news.get("sources", [])
        sources_text = ", ".join(sources) if sources else "Greek news sources"
        
        # Create full HTML email
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Greek News Summary</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #1a5276;
                    border-bottom: 2px solid #1a5276;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #2874a6;
                    margin-top: 20px;
                }}
                .date {{
                    color: #666;
                    font-style: italic;
                    margin-bottom: 20px;
                }}
                .source {{
                    color: #666;
                    font-style: italic;
                    font-size: 0.9em;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 15px;
                    border-top: 1px solid #ddd;
                    font-size: 0.9em;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1>Greek News Summary</h1>
            <div class="date">{today_date}</div>
            
            {html_content}
            
            <div class="footer">
                <p>This summary was generated from {sources_text}.</p>
                <p>The content was translated and summarized using Mistral AI.</p>
            </div>
        </body>
        </html>
        """
        return full_html
    else:
        # The content already has HTML structure
        return html_content

def send_email(recipient_email: str, summarized_news: Dict[str, Any]) -> None:
    """
    Send an email with the summarized news.
    
    Args:
        recipient_email: Email address to send to
        summarized_news: Dictionary with summarized news data
        
    Returns:
        None
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        logger.error("Email sender or password not found in environment variables")
        raise ValueError("Email configuration is incomplete. Please provide EMAIL_SENDER and EMAIL_PASSWORD.")
    
    # Validate recipient email
    if not recipient_email or '@' not in recipient_email:
        raise ValueError("Invalid recipient email address")
    
    # Validate summarized news
    if not summarized_news or not isinstance(summarized_news, dict):
        raise ValueError("Invalid summarized news data")
    
    if "html_content" not in summarized_news:
        raise ValueError("Missing HTML content in summarized news")
    
    try:
        # Create the email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Greek News Summary - {datetime.now().strftime('%B %d, %Y')}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = recipient_email
        
        # Create the HTML content
        html = create_email_html(summarized_news)
        
        # Attach parts to the message
        msg.attach(MIMEText(html, 'html'))
        
        # Send the email
        logger.debug(f"Connecting to SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipient_email, msg.as_string())
            logger.info(f"Email sent successfully to {recipient_email}")
            return
    
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed")
        raise Exception("Failed to authenticate with the email server. Please check the EMAIL_SENDER and EMAIL_PASSWORD credentials.")
    
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"Recipient email was refused: {recipient_email}")
        raise Exception("The email server refused to send to this recipient. Please check the email address and try again.")
    
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise Exception(f"Email server error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise Exception(f"Failed to send email: {str(e)}")
