from sqlalchemy import UniqueConstraint, ForeignKey

from app.models import db


class PesoIdeale(db.Model):
    __tablename__ = 'peso_ideale'
    __table_args__ = (
        UniqueConstraint('data', 'user_id', name='peso_ideale_unique'),
        {'schema': 'dieta'}
    )

    data = db.Column(db.Date, primary_key=True)
    peso_ideale = db.Column(db.Numeric)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}