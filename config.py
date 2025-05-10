import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key' # Change this in production!
    MACID_USER = os.environ.get('MACID_USER')
    MACID_PASS = os.environ.get('MACID_PASS')
    # Add other configurations here as needed
    # For example, path to credentials.json if not in root, or default start/end dates
    CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
    TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')
