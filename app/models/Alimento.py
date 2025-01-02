from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Computed
from . import db

class Alimento(db.Model):
    __tablename__ = 'alimento'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    id_alimento_base = db.Column(db.BigInteger, db.ForeignKey('dieta.alimento_base.id', ondelete="CASCADE"))
    user_id = db.Column(db.BigInteger, db.ForeignKey('dieta.utente.id', ondelete="CASCADE"), nullable=False)
    nome_override = db.Column(db.String(200))
    carboidrati_override = db.Column(db.Numeric)
    proteine_override = db.Column(db.Numeric)
    grassi_override = db.Column(db.Numeric)
    fibre_override = db.Column(db.Numeric, default=0)
    confezionato_override = db.Column(db.Boolean, default=False)
    vegan_override = db.Column(db.Boolean, default=False)
    kcal_override = db.Column(db.Numeric,
                     Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))", persisted=True))
    macro_override = db.Column(db.String(1), Computed("""
        CASE
            WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
            WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
            WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
            ELSE NULL
        END
        """, persisted=True))
    id_gruppo_override = db.Column(db.BigInteger, db.ForeignKey('dieta.gruppo_alimentare.id', ondelete="CASCADE"))

    #alimento_base = db.relationship('AlimentoBase', backref='varianti')
    #utente = db.relationship('Utente', backref='alimenti')