from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import func
from sqlalchemy.orm import foreign
from . import db


class VAlimento(db.Model):
    __tablename__ = 'v_alimento'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String(200))
    carboidrati = db.Column(db.Numeric)
    proteine = db.Column(db.Numeric)
    grassi = db.Column(db.Numeric)
    fibre = db.Column(db.Numeric)
    frutta = db.Column(db.Boolean)
    carne_bianca = db.Column(db.Boolean)
    carne_rossa = db.Column(db.Boolean)
    pane = db.Column(db.Boolean)
    stagionalita = db.Column(ARRAY(db.BigInteger))
    verdura = db.Column(db.Boolean)
    confezionato = db.Column(db.Boolean)
    vegan = db.Column(db.Boolean)
    pesce = db.Column(db.Boolean)
    macro = db.Column(db.String(1))
    kcal = db.Column(db.Numeric)
    id_gruppo = db.Column(db.BigInteger)
    user_id = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
