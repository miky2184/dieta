from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
from . import db

class AlimentoBase(db.Model):
    __tablename__ = 'alimento_base'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String(200))
    carboidrati = db.Column(db.Numeric)
    proteine = db.Column(db.Numeric)
    grassi = db.Column(db.Numeric)
    fibre = db.Column(db.Numeric, default=0)
    frutta = db.Column(db.Boolean, default=False)
    carne_bianca = db.Column(db.Boolean, default=False)
    carne_rossa = db.Column(db.Boolean, default=False)
    pane = db.Column(db.Boolean, default=False)
    stagionalita = db.Column(ARRAY(db.BigInteger))
    verdura = db.Column(db.Boolean, default=False)
    confezionato = db.Column(db.Boolean, default=False)
    vegan = db.Column(db.Boolean, default=False)
    pesce = db.Column(db.Boolean, default=False)
    macro = db.Column(db.String(1))  # Generato
    kcal = db.Column(db.Numeric)  # Generato
    id_gruppo = db.Column(db.BigInteger, db.ForeignKey('dieta.gruppo_alimentare.id', ondelete="CASCADE"))

    # Relazione con GruppoAlimentare
    gruppo_alimentare = db.relationship(
        'GruppoAlimentare',
        primaryjoin='GruppoAlimentare.id == AlimentoBase.id_gruppo',
        back_populates='alimenti_base',
        lazy='joined'
    )