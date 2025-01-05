from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey, Computed, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Numeric
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from . import db

# Definizione del modello per i dettagli dell utente
class Utente(db.Model):
    __tablename__ = 'utente'
    __table_args__ = (
        CheckConstraint("sesso = ANY (ARRAY['M', 'F'])", name='utente_sesso_check'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cognome = db.Column(db.String(255), nullable=False)
    sesso = db.Column(db.String(1), nullable=False)
    eta = db.Column(db.Integer, nullable=False)
    altezza = db.Column(db.Numeric(5, 2), nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False)
    tdee = db.Column(db.Numeric(4, 3), nullable=True)
    deficit_calorico = db.Column(db.Numeric(5, 2), nullable=True)
    bmi = db.Column(db.Numeric(5, 2), nullable=True)
    peso_ideale = db.Column(db.Numeric(5, 2), nullable=True)
    meta_basale = db.Column(db.Numeric(8, 2), nullable=True)
    meta_giornaliero = db.Column(db.Numeric(8, 2), nullable=True)
    calorie_giornaliere = db.Column(db.Numeric(8, 2), nullable=True)
    settimane_dieta = db.Column(db.String, nullable=True)
    carboidrati = db.Column(db.Integer, nullable=True)
    proteine = db.Column(db.Integer, nullable=True)
    grassi = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String, nullable=False)
    dieta = db.Column(db.String, nullable=True)

    # Relazione verso la vista VAlimento
    alimenti = db.relationship(
        'VAlimento',
        primaryjoin=(
                db.foreign(id) == func.coalesce(db.remote(VAlimento.user_id), id)
        ),
        viewonly=True  # La relazione è sola lettura
    )
    ingredienti_ricette = db.relationship(
        'VIngredientiRicetta',
        primaryjoin=(
                db.foreign(id) == func.coalesce(db.remote(VIngredientiRicetta.user_id), id)
        ),
        viewonly=True  # La relazione è sola lettura
    )
    menu_settimanale = db.relationship('MenuSettimanale', backref='utente', cascade='all, delete-orphan')
    registro_peso = db.relationship('RegistroPeso', backref='utente', cascade='all, delete-orphan')
    ricette = db.relationship(
        'VRicetta',
        primaryjoin=(
                db.foreign(id) == func.coalesce(db.remote(VRicetta.user_id), id)
        ),
        viewonly=True  # La relazione è sola lettura
    )
    auth = db.relationship('UtenteAuth', back_populates='utente', overlaps="utente_auth,utente_assoc")
    utente_auth = db.relationship('UtenteAuth', overlaps="auth,utente_assoc")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}