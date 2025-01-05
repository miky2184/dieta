from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey, Computed, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Numeric
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from . import db


class RegistroPeso(db.Model):
    __tablename__ = 'registro_peso'
    __table_args__ = (
        UniqueConstraint('data_rilevazione', 'user_id', name='registro_peso_unique'),
        {'schema': 'dieta'}
    )

    data_rilevazione = db.Column(db.Date, primary_key=True)
    peso = db.Column(db.Numeric)
    vita = db.Column(db.Numeric)
    fianchi = db.Column(db.Numeric)
    peso_ideale = db.Column(db.Numeric)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}