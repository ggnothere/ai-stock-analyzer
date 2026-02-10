"""
PythonAnywhere WSGI Configuration
Copy the content of this file into PythonAnywhere's WSGI configuration file
"""
import sys
import os

# Add your project directory to the path
# Replace 'yourusername' with your PythonAnywhere username
project_home = '/home/yourusername/ai_stock_analyzer'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['GEMINI_API_KEY'] = 'your_gemini_api_key_here'
os.environ['ALPHA_VANTAGE_API_KEY'] = 'your_alpha_vantage_key_here'
os.environ['SERVERCHAN_KEY'] = ''  # Optional

# Import your Flask app
from app import app as application  # noqa
