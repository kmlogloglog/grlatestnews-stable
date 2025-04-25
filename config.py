import os

# Web scraping settings
MAX_ARTICLES_PER_SOURCE = 3
MAX_TOTAL_ARTICLES = 50
SCRAPING_TIMEOUT = 60  # seconds

# Mistral AI settings
MISTRAL_MODEL = "mistral-small"
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# Email settings
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))

# News sources
NEWS_SOURCES = [
    "https://www.protothema.gr/",
    "https://www.newsit.gr/",
    "https://www.newsbomb.gr/",
    "https://www.in.gr/",
    "https://www.iefimerida.gr/",
    "https://www.kathimerini.gr/",
    "https://www.news247.gr/",
    "https://www.naftemporiki.gr/",
    "https://www.tanea.gr/",
    "https://www.gazzetta.gr/",
    "https://www.policenet.gr/"
]
