from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import JSON

from . import db


class MenuSettimanale(db.Model):
    __tablename__ = 'menu_settimanale'
    __table_args__ = (
        UniqueConstraint('data_inizio', 'data_fine', 'user_id', name='menu_settimanale_data_inizio_data_fine_key'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, nullable=False)
    data_inizio = db.Column(db.Date, nullable=False, primary_key=True)
    data_fine = db.Column(db.Date, nullable=False, primary_key=True)
    menu = db.Column(JSON, nullable=False)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)