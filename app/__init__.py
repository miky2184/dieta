from flask_caching import Cache
from flask import Flask, request, redirect, url_for
from flask_login import LoginManager, current_user
from dotenv import load_dotenv
from app.models.models import db, UtenteAuth, Utenti

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

    @app.before_request
    def log_before_request():
        if request.endpoint != 'static':  # Escludi richieste ai file statici
            print(f"Requested URL: {request.url}")
            if not current_user.is_authenticated and request.endpoint != 'auth.login':
                print("User is not authenticated, redirecting to login.")
                return redirect(url_for('auth.login', next=request.url))

    # Configura Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return UtenteAuth.query.get(int(user_id))


    with app.app_context():
        cache.clear()
        from .auth import auth as auth_blueprint
        from .views import views
        from .admin import admin
        app.register_blueprint(views)
        app.register_blueprint(auth_blueprint)
        app.register_blueprint(admin)

    return app
