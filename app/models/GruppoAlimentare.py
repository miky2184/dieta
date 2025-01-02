from flask_sqlalchemy import SQLAlchemy
from . import db

class GruppoAlimentare(db.Model):
    __tablename__ = 'gruppo_alimentare'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String, nullable=True)
    descrizione = db.Column(db.String, nullable=True)

    # Relazione con AlimentoBase
    alimenti_base = db.relationship(
        'AlimentoBase',
        primaryjoin='GruppoAlimentare.id == AlimentoBase.id_gruppo',
        back_populates='gruppo_alimentare',
        lazy='select'
    )