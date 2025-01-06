from sqlalchemy import or_, and_, exists, not_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import aliased

from app.models import db


class VAlimento(db.Model):
    __tablename__ = 'v_alimento'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String(200))
    carboidrati = db.Column(db.Numeric)
    proteine = db.Column(db.Numeric)
    grassi = db.Column(db.Numeric)
    fibre = db.Column(db.Numeric)
    stagionalita = db.Column(ARRAY(db.BigInteger))
    confezionato = db.Column(db.Boolean)
    vegan = db.Column(db.Boolean)
    macro = db.Column(db.String(1))
    kcal = db.Column(db.Numeric)
    id_gruppo = db.Column(db.BigInteger)
    nome_gruppo = db.Column(db.String)
    user_id = db.Column(db.Integer, nullable=True)
    removed = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    @classmethod
    def filtro_alimenti(cls, user_id, alias=None):
        # Alias per la tabella (se non fornito, usa il modello originale)
        table = alias or cls

        # Alias per la tabella interna nella clausola NOT EXISTS
        va2 = aliased(cls)

        # Subquery per la clausola NOT EXISTS
        not_exists_clause = ~exists().where(
            and_(
                va2.id == table.id,  # Confronta l'ID dell'alimento
                va2.user_id == user_id  # Confronta con l'utente corrente
            )
        )

        # Costruisci il filtro combinando le due condizioni
        filtro = or_(
            and_(table.user_id == user_id, not_(table.removed)),  # user_id = 2 AND not removed
            and_(table.user_id == 0, not_exists_clause)  # user_id = 0 AND NOT EXISTS(...)
        )

        return filtro
