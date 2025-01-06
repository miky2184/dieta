from app.models import db
from sqlalchemy.orm import aliased
from sqlalchemy import or_, and_, exists, not_

class VIngredientiRicetta(db.Model):
    __tablename__ = 'v_ingredienti_ricetta'
    __table_args__ = {'schema': 'dieta'}

    id_ricetta = db.Column(db.BigInteger, primary_key=True)
    id_alimento = db.Column(db.BigInteger, primary_key=True)
    qta = db.Column(db.Numeric)
    removed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.BigInteger)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def filtro_ingredienti(cls, user_id, alias=None):
        """
        Genera un filtro per selezionare gli ingredienti in base all'utente e alla visibilità.

        Args:
            user_id (int): ID dell'utente corrente.
            alias (sqlalchemy.orm.aliased, opzionale): Alias per la tabella. Default è None.

        Returns:
            sqlalchemy.sql.elements.BooleanClauseList: Filtro SQL.
        """
        # Alias per la tabella (se non fornito, usa il modello originale)
        table = alias or cls

        # Alias per la subquery
        vir_sub = aliased(cls)

        # Subquery per la clausola NOT EXISTS
        not_exists_clause = ~exists().where(
            and_(
                vir_sub.id_ricetta == table.id_ricetta,
                vir_sub.id_alimento == table.id_alimento,
                vir_sub.user_id == user_id
            )
        )

        # Costruisci il filtro combinando le due condizioni
        filtro = or_(
            and_(table.user_id == user_id, not_(table.removed)),
            and_(table.user_id == 0, not_exists_clause)
        )

        return filtro