from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
from . import db

class VRicetta(db.Model):
    __tablename__ = 'v_ricetta'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome_ricetta = db.Column(db.String)
    colazione = db.Column(db.Boolean)
    spuntino = db.Column(db.Boolean)
    principale = db.Column(db.Boolean)
    contorno = db.Column(db.Boolean)
    colazione_sec = db.Column(db.Boolean)
    pane = db.Column(db.Boolean)
    complemento = db.Column(db.Boolean)
    enabled = db.Column(db.Boolean)
    user_id = db.Column(db.BigInteger)