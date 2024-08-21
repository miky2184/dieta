import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '2a1ca5c0eda9a548321057ce98a95d84a5f604726ba627ecba27270f1248d501')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    UPLOAD_FOLDER = '/tmp/fantafighettino'
    ALLOWED_EXTENSIONS = {'csv'}
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=120)

    CACHE_TYPE = 'null'
    CACHE_DEFAULT_TIMEOUT = 300

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 40,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800
    }