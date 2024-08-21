from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Crea un'istanza di SQLAlchemy
db = SQLAlchemy()

# Definizione del modello per gli utenti con autenticazione
class UtenteAuth(UserMixin, db.Model):
    __tablename__ = 'utenti_auth'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('dieta.utenti.id'), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Definizione del modello per i dettagli degli utenti
class Utenti(db.Model):
    __tablename__ = 'utenti'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cognome = db.Column(db.String(255), nullable=False)
    sesso = db.Column(db.String(1), nullable=False)
    eta = db.Column(db.Integer, nullable=True)
    altezza = db.Column(db.Numeric(5, 2), nullable=True)
    peso = db.Column(db.Numeric(5, 2), nullable=True)
    tdee = db.Column(db.Numeric(4, 3), nullable=True)
    deficit_calorico = db.Column(db.Numeric(5, 2), nullable=True)
    bmi = db.Column(db.Numeric(5, 2), nullable=True)
    peso_ideale = db.Column(db.Numeric(5, 2), nullable=True)
    meta_basale = db.Column(db.Numeric(8, 2), nullable=True)
    meta_giornaliero = db.Column(db.Numeric(8, 2), nullable=True)
    calorie_giornaliere = db.Column(db.Numeric(8, 2), nullable=True)
    calorie_settimanali = db.Column(db.Numeric(8, 2), nullable=True)
    carboidrati = db.Column(db.Integer, nullable=True)
    proteine = db.Column(db.Integer, nullable=True)
    grassi = db.Column(db.Integer, nullable=True)

    auth = db.relationship('UtenteAuth', backref='utente', uselist=False)
