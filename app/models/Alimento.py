from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Query

from app.models import db


class Alimento(db.Model):
    __tablename__ = 'alimento'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('dieta.utente.id', ondelete="CASCADE"), nullable=False, primary_key=True)
    nome_override = db.Column(db.String(200))
    carboidrati_override = db.Column(db.Numeric)
    proteine_override = db.Column(db.Numeric)
    grassi_override = db.Column(db.Numeric)
    fibre_override = db.Column(db.Numeric, default=0)
    stagionalita_override = db.Column(ARRAY(db.BigInteger), default=lambda: [1, 2, 3,4,5,6,7,8,9,10,11,12])
    surgelato_override = db.Column(db.Boolean, default=False)
    vegan_override = db.Column(db.Boolean, default=False)
    macro_override = db.Column(db.String(1), Computed("""
        CASE
            WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
            WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
            WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
            ELSE NULL
        END
        """, persisted=True))
    kcal_override = db.Column(db.Numeric, Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))", persisted=True))
    id_gruppo_override = db.Column(db.BigInteger, db.ForeignKey('dieta.gruppo_alimentare.id', ondelete="CASCADE"))
    removed = db.Column(db.Boolean, default=False)

    gruppo_alimentare = db.relationship(
        'GruppoAlimentare',
        primaryjoin='GruppoAlimentare.id == Alimento.id_gruppo_override',
        back_populates='alimenti',
        lazy='joined'
    )


    @classmethod
    def get_by_id_and_user(cls, alimento_id, user_id) -> Query:
        """
        Recupera un record di Alimento basato su ID e user_id.

        Args:
            alimento_id (int): ID dell'alimento.
            user_id (int): ID dell'utente.

        Returns:
            Query: Record di Alimento o None.
        """
        return cls.query.filter(
            cls.id == alimento_id,
            cls.user_id == user_id
        ).first()