import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key-123')
    DATABASE_URL = os.environ.get('DATABASE_URL')
