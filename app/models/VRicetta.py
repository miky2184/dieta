from email.policy import default

from sqlalchemy import or_, and_, exists, not_
from sqlalchemy.orm import aliased

from app.models import db


class VRicetta(db.Model):
    __tablename__ = 'v_ricetta'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome_ricetta = db.Column(db.String)
    colazione = db.Column(db.Boolean)
    spuntino = db.Column(db.Boolean)
    principale = db.Column(db.Boolean)
    contorno = db.Column(db.Boolean)
    colazione_sec = db.Column(db.Boolean)
    complemento = db.Column(db.Boolean)
    enabled = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.BigInteger)
    removed = db.Column(db.Boolean, default=False)

    @classmethod
    def filtro_ricette(cls, user_id, alias=None):
        """
        Genera un filtro per selezionare le ricette in base all'utente e alla visibilità.

        Args:
            user_id (int): ID dell'utente corrente.
            alias (sqlalchemy.orm.aliased, opzionale): Alias per la tabella. Default è None.

        Returns:
            sqlalchemy.sql.elements.BooleanClauseList: Filtro SQL.
        """
        # Alias per la tabella (se non fornito, usa il modello originale)
        table = alias or cls

        # Alias per la subquery
        vr_sub = aliased(cls)

        # Subquery per la clausola NOT EXISTS
        not_exists_clause = ~exists().where(
            and_(
                vr_sub.id == table.id,
                vr_sub.user_id == user_id
            )
        )

        # Costruisci il filtro combinando le due condizioni
        filtro = or_(
            and_(table.user_id == user_id, not_(table.removed)),
            and_(table.user_id == 0, not_exists_clause)
        )

        return filtro