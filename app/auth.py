from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.models import db, UtenteAuth, Utenti
from app.services.menu_services import save_weight, is_valid_email
from datetime import datetime
from flask import jsonify, request

auth = Blueprint('auth', __name__)


@auth.route('/check_username', methods=['POST'])
def check_username():
    username = request.json.get('username')
    user = UtenteAuth.query.filter_by(username=username.lower()).first()
    if user:
        return jsonify({'exists': True})
    return jsonify({'exists': False})


@auth.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')

    if not is_valid_email(email):
        return jsonify({'bad': True})

    user = Utenti.query.filter_by(email=email.lower()).first()
    if user:
        return jsonify({'exists': True})
    return jsonify({'exists': False})

@auth.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = UtenteAuth.query.filter_by(username=username.lower()).first()

        if not user or not check_password_hash(user.password_hash, password):
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect(url_for('views.dashboard'))

    return render_template('auth.html')

@auth.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    nome = request.form.get('nome')
    cognome = request.form.get('cognome')
    sesso = request.form.get('sesso')
    eta = request.form.get('eta')
    altezza = request.form.get('altezza')
    peso = request.form.get('peso')
    email = request.form.get('email')

    user = UtenteAuth.query.filter_by(username=username.lower()).first()

    if user:
        return redirect(url_for('auth.login'))

    # Crea l'utente nella tabella Utenti
    new_user_details = Utenti(
        nome=nome.upper(),
        cognome=cognome.upper(),
        sesso=sesso,
        eta=eta,
        altezza=altezza,
        peso=peso,
        email=email
    )

    db.session.add(new_user_details)
    db.session.commit()

    # Ora l'ID dell'utente è disponibile
    user_id = new_user_details.id

    new_user_auth = UtenteAuth()
    new_user_auth.username = username.lower()
    new_user_auth.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    new_user_auth.user_id = user_id

    db.session.add(new_user_auth)
    db.session.commit()

    save_weight(datetime.now().date(), peso, user_id)

    current_app.cache.delete(f'view//get_data_utente')
    return redirect(url_for('auth.login'))

@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    current_app.cache.clear()
    return redirect(url_for('auth.login'))
