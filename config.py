#config.py
import os


class Config:
    LOG_LEVEL = os.getenv('LOG_LEVEL')
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', False)

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('POOL_SIZE', 10)),
        'max_overflow': int(os.getenv('MAX_OVERFLOW', 5)),
        'pool_timeout': int(os.getenv('POOL_TIMEOUT', 30)),
        'pool_recycle': int(os.getenv('POOL_RECYCLE', 1800)),
        'pool_pre_ping': True
    }

    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300