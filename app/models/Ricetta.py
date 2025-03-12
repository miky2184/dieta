from email.policy import default

from sqlalchemy.orm import Query

from app.models import db


class Ricetta(db.Model):
    __tablename__ = 'ricetta'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('dieta.utente.id', ondelete="CASCADE"), nullable=False, primary_key=True)
    nome_ricetta_override = db.Column(db.String)
    colazione_override = db.Column(db.Boolean, default=False)
    spuntino_override = db.Column(db.Boolean, default=False)
    principale_override = db.Column(db.Boolean, default=False)
    contorno_override = db.Column(db.Boolean, default=False)
    colazione_sec_override = db.Column(db.Boolean, default=False)
    complemento_override = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=True)
    removed = db.Column(db.Boolean, default=False)

    #ricetta_base = db.relationship('RicettaBase', backref='varianti')
    #utente = db.relationship('Utente', backref='ricette')

    @classmethod
    def get_by_id_and_user(cls, ricetta_id, user_id) -> Query:
        """
        Recupera un record di Alimento basato su ID e user_id.

        Args:
            ricetta_id (int): ID della ricetta.
            user_id (int): ID dell'utente.

        Returns:
            Query: Record di Alimento o None.
        """
        return cls.query.filter(
            cls.id == ricetta_id,
            cls.user_id == user_id
        ).first()