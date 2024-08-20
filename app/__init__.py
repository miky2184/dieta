from flask import Flask
from flask_caching import Cache


def create_app():
    app = Flask(__name__)

    # Configura la cache (in questo caso, SimpleCache che utilizza la memoria locale)
    app.config['CACHE_TYPE'] = 'SimpleCache'  # Puoi usare 'RedisCache', 'MemcachedCache', ecc.
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # Timeout predefinito per la cache (in secondi)
    cache = Cache(app)
    app.cache = cache  # Aggiungi l'oggetto cache all'app

    with app.app_context():
        cache.clear()
        from .views import views
        app.register_blueprint(views)

    return app