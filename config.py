"""
AI Stock Technical Analyzer - Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
SERVERCHAN_KEY = os.getenv("SERVERCHAN_KEY", "")

# Default settings
DEFAULT_PERIOD = "6mo"  # Default data period
DEFAULT_MODEL = "gemini"  # Default AI model

# Chart settings
CHART_STYLE = "nightclouds"  # mplfinance style
CHART_DPI = 150

# Flask settings
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
HOST = os.getenv("FLASK_HOST", "0.0.0.0")
PORT = int(os.getenv("FLASK_PORT", 5000))
