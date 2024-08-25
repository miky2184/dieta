#config.py
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '2a1ca5c0eda9a548321057ce98a95d84a5f604726ba627ecba27270f1248d501')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False')

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('POOL_SIZE', 10)),
        'max_overflow': int(os.getenv('MAX_OVERFLOW', 5)),
        'pool_timeout': int(os.getenv('POOL_TIMEOUT', 30)),
        'pool_recycle': int(os.getenv('POOL_RECYCLE', 1800)),
        'pool_pre_ping': True
    }

    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300