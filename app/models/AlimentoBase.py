from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import ARRAY

from app.models import db


class AlimentoBase(db.Model):
    __tablename__ = 'alimento_base'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String(200))
    carboidrati = db.Column(db.Numeric)
    proteine = db.Column(db.Numeric)
    grassi = db.Column(db.Numeric)
    stagionalita = db.Column(ARRAY(db.BigInteger))
    surgelato = db.Column(db.Boolean, default=False)
    vegan = db.Column(db.Boolean, default=False)
    macro = db.Column(db.String(1), Computed("""
            CASE
                WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
                WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
                WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
                ELSE NULL
            END
            """, persisted=True))
    fibre = db.Column(db.Numeric, default=0)
    kcal = db.Column(db.Numeric,
                              Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))",
                                       persisted=True))

    id_gruppo = db.Column(db.BigInteger, db.ForeignKey('dieta.gruppo_alimentare.id', ondelete="CASCADE"))

    # Relazione con GruppoAlimentare
    gruppo_alimentare = db.relationship(
        'GruppoAlimentare',
        primaryjoin='GruppoAlimentare.id == AlimentoBase.id_gruppo',
        back_populates='alimenti_base',
        lazy='joined'
    )

    @classmethod
    def get_by_id(cls, alimento_id):
        """
        Recupera un record di AlimentoBase dal database usando il suo ID.

        Args:
            alimento_id (int): ID dell'alimento base.

        Returns:
            AlimentoBase: Istanza del modello AlimentoBase se trovata, altrimenti None.
        """
        return cls.query.filter(cls.id == alimento_id).first()