from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey, Computed, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Numeric
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from . import db

class MenuSettimanale(db.Model):
    __tablename__ = 'menu_settimanale'
    __table_args__ = (
        UniqueConstraint('data_inizio', 'data_fine', 'user_id', name='menu_settimanale_data_inizio_data_fine_key'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, primary_key=True)
    data_inizio = db.Column(db.Date, nullable=False)
    data_fine = db.Column(db.Date, nullable=False)
    menu = db.Column(JSON, nullable=False)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'))