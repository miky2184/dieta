from flask_login import UserMixin
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


# Definizione del modello per utente con autenticazione
class UtenteAuth(UserMixin, db.Model):
    __tablename__ = 'utente_auth'
    __table_args__ = (
        UniqueConstraint('username', name='utente_auth_username_key'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('dieta.utente.id'), nullable=False)
    tutorial_completed = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)

    utente = db.relationship('Utente', back_populates='auth', overlaps="utente_auth,utente_assoc")
    utente_assoc = db.relationship('Utente', overlaps="auth,utente_auth")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)