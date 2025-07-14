# app/__init__.py
from dotenv import load_dotenv
from flask import Flask, send_from_directory, render_template
from flask_caching import Cache
from flask_login import LoginManager

from app.models import db
from app.models.Utente import Utente
from app.models.UtenteAuth import UtenteAuth


def create_app():
    # Carica le variabili d'ambiente dal file .env
    load_dotenv()
    app = Flask(__name__, static_url_path='/static')
    # Configura l'applicazione
    app.config.from_object('config.Config')

    # Configura il cache
    cache = Cache(app)
    app.cache = cache

    # Inizializza il database con l'app
    db.init_app(app)

    # Configura Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return UtenteAuth.query.get(int(user_id))

    # ===== ROUTE PWA =====
    @app.route('/manifest.json')
    def manifest():
        return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

    @app.route('/sw.js')
    def service_worker():
        return send_from_directory('static', 'sw.js', mimetype='application/javascript')

    # ===== FINE ROUTE PWA =====

    with app.app_context():
        cache.clear()
        from .auth_route import auth as auth_blueprint
        from .views_route import views
        from .admin_route import admin
        from .alimenti_route import alimenti
        from .ricette_route import ricette
        from .menu_route import menu
        from .modifica_pasti_route import pasti
        from .common_route import common
        app.register_blueprint(views)
        app.register_blueprint(auth_blueprint)
        app.register_blueprint(admin)
        app.register_blueprint(alimenti)
        app.register_blueprint(ricette)
        app.register_blueprint(menu)
        app.register_blueprint(pasti)
        app.register_blueprint(common)
    return app
