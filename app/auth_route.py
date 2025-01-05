# app/auth.py
from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.models import db
from app.models.Utente import Utente
from app.models.UtenteAuth import UtenteAuth
from app.services.menu_services import is_valid_email, copia_alimenti_ricette
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

    user = Utente.query.filter_by(email=email.lower()).first()
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
    vegane = request.form.get('include_vegan')
    carne = request.form.get('include_carne')
    pesce = request.form.get('include_pesce')

    # Crea l'utente nella tabella Utenti
    new_user_details = Utente(
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

    #copia_alimenti_ricette(user_id, bool(vegane), bool(carne), bool(pesce))

    # Logga automaticamente l'utente appena registrato
    login_user(new_user_auth, remember=True)

    current_app.cache.delete(f'get_data_utente_{user_id}')
    return redirect(url_for('views.dashboard'))

@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    current_app.cache.clear()
    return redirect(url_for('auth.login'))


@auth.route('/forgot_password', methods=['POST'])
def forgot_password():
    pass
