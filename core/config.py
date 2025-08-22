# Configuration constants
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = 'gemini-1.5-flash'
    GEMINI_TIMEOUT = 30
    
    # Database Settings
    DATABASE_PATH = 'database/schedule.db'
    CONNECTION_TIMEOUT = 10
    
    # Google Calendar
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'core/OAuth/credentials.json')
    GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar']
    TOKEN_PATH = 'token.pickle'
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL') 
    AUTO_GOOGLE_SYNC = 'true'
    NGROK_AUTHTOKEN = os.getenv('NGROK_AUTHTOKEN')
    PERIODIC_SYNC_INTERVAL = 300  # seconds (5 minutes)
    
    # SMTP Settings
    SMTP_CONFIG = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'user': os.getenv('SMTP_USER', ''),
        'password': os.getenv('SMTP_PASSWORD', '')
    }
    
    # Time Settings
    WORK_TIME = (8, 17)
    LUNCH_TIME = (12, 13)
    DEFAULT_DURATION = 60
    TIMEZONE = 'Asia/Ho_Chi_Minh'  # Vietnam timezone
    TIMEZONE_OFFSET = '+07:00'     # GMT+7
    
    # Notification Settings
    SCAN_INTERVAL = 60  # seconds
    REMINDER_MINUTES = 15  # minutes
