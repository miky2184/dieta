from flask_sqlalchemy import SQLAlchemy
from . import db

class RicettaBase(db.Model):
    __tablename__ = 'ricetta_base'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome_ricetta = db.Column(db.Text)
    colazione = db.Column(db.Boolean, default=False)
    spuntino = db.Column(db.Boolean, default=False)
    principale = db.Column(db.Boolean, default=False)
    contorno = db.Column(db.Boolean, default=False)
    colazione_sec = db.Column(db.Boolean, default=False)
    pane = db.Column(db.Boolean, default=False)
    complemento = db.Column(db.Boolean, default=False)