#app/models/models.py
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey, Computed, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Numeric
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from . import db

# class Alimento(db.Model):
#     __tablename__ = 'alimento'
#     __table_args__ = (
#         UniqueConstraint('id', 'user_id', name='alimento_unique'),
#         {'schema': 'dieta'}
#     )
#
#     id = db.Column(db.BigInteger, primary_key=True)
#     nome = db.Column(db.String(200))
#     carboidrati = db.Column(db.Numeric)
#     proteine = db.Column(db.Numeric)
#     grassi = db.Column(db.Numeric)
#     fibre = db.Column(db.Numeric)
#     kcal = db.Column(Numeric, Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))", persisted=True))
#     macro = db.Column(db.String(1), Computed("""
#     CASE
#         WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
#         WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
#         WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
#         ELSE NULL
#     END
#     """, persisted=True))
#     frutta = db.Column(db.Boolean, default=False)
#     carne_bianca = db.Column(db.Boolean, default=False)
#     carne_rossa = db.Column(db.Boolean, default=False)
#     pane = db.Column(db.Boolean, default=False)
#     stagionalita = db.Column(ARRAY(db.BigInteger))
#     verdura = db.Column(db.Boolean, default=False)
#     confezionato = db.Column(db.Boolean, default=False)
#     vegan = db.Column(db.Boolean, default=False)
#     pesce = db.Column(db.Boolean, default=False)
#     user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)
#
#     ingredienti = db.relationship('IngredientiRicetta', back_populates='alimento')
#
#     def to_dict(self):
#         return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# class IngredientiRicetta(db.Model):
#     __tablename__ = 'ingredienti_ricetta'
#     __table_args__ = (
#         UniqueConstraint('id_ricetta', 'id_alimento', 'user_id', name='ingredienti_ricetta_unique'),
#         {'schema': 'dieta'}
#     )
#
#     id_ricetta = db.Column(db.BigInteger, ForeignKey('dieta.ricetta.id', ondelete='CASCADE'), primary_key=True)
#     id_alimento = db.Column(db.BigInteger, ForeignKey('dieta.alimento.id', ondelete='CASCADE'), primary_key=True)
#     qta = db.Column(db.Numeric)
#     user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)
#
#     alimento = db.relationship('Alimento', back_populates='ingredienti')
#     ricetta = db.relationship('Ricetta', back_populates='ricetta')
#
#     def add_meal(self, meal):
#         self.meals.append(meal)
#         db.session.add(self)


# class Ricetta(db.Model):
#     __tablename__ = 'ricetta'
#     __table_args__ = (
#         UniqueConstraint('id', 'user_id', name='ricetta_unique'),
#         {'schema': 'dieta'}
#     )
#
#     id = db.Column(db.BigInteger, primary_key=True)
#     nome_ricetta = db.Column(db.Text)
#     colazione = db.Column(db.Boolean, default=False)
#     spuntino = db.Column(db.Boolean, default=False)
#     principale = db.Column(db.Boolean, default=False)
#     contorno = db.Column(db.Boolean, default=False)
#     enabled = db.Column(db.Boolean, default=True)
#     colazione_sec = db.Column(db.Boolean, default=False)
#     pane = db.Column(db.Boolean, default=False)
#     complemento = db.Column(db.Boolean, default=False)
#     user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)
#
#     ricetta = db.relationship('IngredientiRicetta', back_populates='ricetta')
#
#     def to_dict(self):
#         return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# class AlimentoBase(db.Model):
#     __tablename__ = 'alimento_base'
#     __table_args__ = (
#         UniqueConstraint('id', name='alimento_base_pkey'),
#         {'schema': 'dieta'}
#     )
#
#     id = db.Column(db.BigInteger, primary_key=True)
#     nome = db.Column(db.String(200))
#     carboidrati = db.Column(db.Numeric)
#     proteine = db.Column(db.Numeric)
#     grassi = db.Column(db.Numeric)
#     fibre = db.Column(db.Numeric)
#     kcal = db.Column(Numeric, Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))", persisted=True))
#     macro = db.Column(db.String(1), Computed("""
#     CASE
#         WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
#         WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
#         WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
#         ELSE NULL
#     END
#     """, persisted=True))
#     frutta = db.Column(db.Boolean, default=False)
#     carne_bianca = db.Column(db.Boolean, default=False)
#     carne_rossa = db.Column(db.Boolean, default=False)
#     pane = db.Column(db.Boolean, default=False)
#     stagionalita = db.Column(ARRAY(db.BigInteger))
#     verdura = db.Column(db.Boolean, default=False)
#     confezionato = db.Column(db.Boolean, default=False)
#     vegan = db.Column(db.Boolean, default=False)
#     pesce = db.Column(db.Boolean, default=False)
#
#     def to_dict(self):
#         return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# class RicettaBase(db.Model):
#     __tablename__ = 'ricetta_base'
#     __table_args__ = (
#         UniqueConstraint('id', name='ricetta_base_pkey'),
#         {'schema': 'dieta'}
#     )
#
#     id = db.Column(db.BigInteger, primary_key=True)
#     nome_ricetta = db.Column(db.Text)
#     colazione = db.Column(db.Boolean, default=False)
#     spuntino = db.Column(db.Boolean, default=False)
#     principale = db.Column(db.Boolean, default=False)
#     contorno = db.Column(db.Boolean, default=False)
#     enabled = db.Column(db.Boolean, default=True)
#     colazione_sec = db.Column(db.Boolean, default=False)
#     pane = db.Column(db.Boolean, default=False)
#     complemento = db.Column(db.Boolean, default=False)
#
#     def to_dict(self):
#         return {c.name: getattr(self, c.name) for c in self.__table__.columns}
#
#
# class IngredientiRicettaBase(db.Model):
#     __tablename__ = 'ingredienti_ricetta_base'
#     __table_args__ = (
#         UniqueConstraint('id_ricetta', 'id_alimento', name='ingredienti_ricetta_base_pkey'),
#         {'schema': 'dieta'}
#     )
#
#     id_ricetta = db.Column(db.BigInteger, ForeignKey('dieta.ricetta.id', ondelete='CASCADE'), primary_key=True)
#     id_alimento = db.Column(db.BigInteger, ForeignKey('dieta.alimento.id', ondelete='CASCADE'), primary_key=True)
#     qta = db.Column(db.Numeric)