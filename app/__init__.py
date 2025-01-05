# app/__init__.py
from flask_caching import Cache
from flask import Flask, request, redirect, url_for
from flask_login import LoginManager, current_user
from dotenv import load_dotenv
from app.models.models import db, UtenteAuth, Utente


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

    with app.app_context():
        cache.clear()
        from .auth_route import auth as auth_blueprint
        from .views_route import views
        from .admin_route import admin
        from .alimenti_route import alimenti
        from .ricette_route import ricette
        app.register_blueprint(views)
        app.register_blueprint(auth_blueprint)
        app.register_blueprint(admin)
        app.register_blueprint(alimenti)
        app.register_blueprint(ricette)

    return app
