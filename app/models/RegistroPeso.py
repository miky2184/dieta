from sqlalchemy import UniqueConstraint, ForeignKey

from app.models import db


class RegistroPeso(db.Model):
    __tablename__ = 'registro_peso'
    __table_args__ = (
        UniqueConstraint('data_rilevazione', 'user_id', name='registro_peso_unique'),
        {'schema': 'dieta'}
    )

    data_rilevazione = db.Column(db.Date, primary_key=True)
    peso = db.Column(db.Numeric)
    vita = db.Column(db.Numeric)
    fianchi = db.Column(db.Numeric)
    perc_massa_grassa = db.Column(db.Numeric)
    vo2 = db.Column(db.Numeric)
    #peso_ideale = db.Column(db.Numeric)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}