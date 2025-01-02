from flask_sqlalchemy import SQLAlchemy
from . import db

class Ricetta(db.Model):
    __tablename__ = 'ricetta'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('dieta.utente.id', ondelete="CASCADE"), nullable=False)
    nome_ricetta_override = db.Column(db.String)
    colazione_override = db.Column(db.Boolean)
    spuntino_override = db.Column(db.Boolean)
    principale_override = db.Column(db.Boolean)
    contorno_override = db.Column(db.Boolean)
    colazione_sec_override = db.Column(db.Boolean)
    pane_override = db.Column(db.Boolean)
    complemento_override = db.Column(db.Boolean)
    enabled = db.Column(db.Boolean)

    #ricetta_base = db.relationship('RicettaBase', backref='varianti')
    #utente = db.relationship('Utente', backref='ricette')