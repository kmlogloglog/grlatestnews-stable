import os

# Web scraping settings
MAX_ARTICLES_PER_SOURCE = 6
MAX_TOTAL_ARTICLES = 60
SCRAPING_TIMEOUT = 120  # seconds (increased for more articles)

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
    "https://www.protothema.gr/greece/",
    "https://www.newsit.gr/category/ellada/",
    "https://www.newsbomb.gr/",
    "https://www.in.gr/greece/",
    "https://www.iefimerida.gr/ellada",
    "https://www.kathimerini.gr/society/",
    "https://www.kathimerini.gr/politics/",
    "https://www.news247.gr/ellada/",
    "https://www.naftemporiki.gr/",
    "https://www.tanea.gr/",
    "https://www.gazzetta.gr/",
    "https://www.policenet.gr/"
]
