from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.models import db, UtenteAuth, Utenti

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = UtenteAuth.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Credenziali non valide. Riprova.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        current_app.cache.clear()
        return redirect(next_page or url_for('views.dashboard'))

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

    user = UtenteAuth.query.filter_by(username=username).first()

    if user:
        flash('Username già esistente. Per favore, usa un altro username.')
        return redirect(url_for('auth.login'))

    new_user_auth = UtenteAuth(username=username, password=generate_password_hash(password, method='sha256'))
    db.session.add(new_user_auth)
    db.session.commit()

    new_user_details = Utenti(
        id=new_user_auth.id,
        nome=nome,
        cognome=cognome,
        sesso=sesso,
        eta=eta,
        altezza=altezza,
        peso=peso
    )
    db.session.add(new_user_details)
    db.session.commit()

    flash('Registrazione completata. Ora puoi effettuare il login.')
    return redirect(url_for('auth.login'))

@auth.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    current_app.cache.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
