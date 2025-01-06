from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Query

from app.models import db


class MenuSettimanale(db.Model):
    __tablename__ = 'menu_settimanale'
    __table_args__ = (
        UniqueConstraint('data_inizio', 'data_fine', 'user_id', name='menu_settimanale_data_inizio_data_fine_key'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, nullable=False)
    data_inizio = db.Column(db.Date, nullable=False, primary_key=True)
    data_fine = db.Column(db.Date, nullable=False, primary_key=True)
    menu = db.Column(JSON, nullable=False)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)


    @classmethod
    def get_by_id_and_user(cls, menu_id, user_id) -> Query:
        """
        Recupera un record di MenuSettimanale basato su ID e user_id.

        Args:
            menu_id (int): ID dell'alimento.
            user_id (int): ID dell'utente.

        Returns:
            Query: Record di MenuSettimanale o None.
        """
        return cls.query.filter(
            cls.id == menu_id,
            cls.user_id == user_id
        ).first()