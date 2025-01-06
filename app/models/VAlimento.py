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

    def filtro_alimenti(user_id):
        # Alias per la tabella VAlimento
        va2 = aliased(VAlimento)

        # Subquery per la clausola NOT EXISTS
        not_exists_clause = ~exists().where(
            and_(
                va2.id == VAlimento.id,  # Confronta l'ID dell'alimento
                va2.user_id == user_id  # Confronta con l'utente corrente
            )
        )

        # Costruisci il filtro combinando le due condizioni
        filtro = or_(
            and_(VAlimento.user_id == user_id, not_(VAlimento.removed)),  # user_id = 2 AND not removed
            and_(VAlimento.user_id == 0, not_exists_clause)  # user_id = 0 AND NOT EXISTS(...)
        )

        return filtro
