#app/models/models.py
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKey, Computed, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, JSON
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Numeric
db = SQLAlchemy()


# Definizione del modello per utente con autenticazione
class UtenteAuth(UserMixin, db.Model):
    __tablename__ = 'utente_auth'
    __table_args__ = (
        UniqueConstraint('username', name='utente_auth_username_key'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('dieta.utente.id'), nullable=False)
    tutorial_completed = db.Column(db.Boolean, default=False)

    utente = db.relationship('Utente', back_populates='auth', overlaps="utente_auth,utente_assoc")
    utente_assoc = db.relationship('Utente', overlaps="auth,utente_auth")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Definizione del modello per i dettagli dell utente
class Utente(db.Model):
    __tablename__ = 'utente'
    __table_args__ = (
        CheckConstraint("sesso = ANY (ARRAY['M', 'F'])", name='utente_sesso_check'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    cognome = db.Column(db.String(255), nullable=False)
    sesso = db.Column(db.String(1), nullable=False)
    eta = db.Column(db.Integer, nullable=False)
    altezza = db.Column(db.Numeric(5, 2), nullable=False)
    peso = db.Column(db.Numeric(5, 2), nullable=False)
    tdee = db.Column(db.Numeric(4, 3), nullable=True)
    deficit_calorico = db.Column(db.Numeric(5, 2), nullable=True)
    bmi = db.Column(db.Numeric(5, 2), nullable=True)
    peso_ideale = db.Column(db.Numeric(5, 2), nullable=True)
    meta_basale = db.Column(db.Numeric(8, 2), nullable=True)
    meta_giornaliero = db.Column(db.Numeric(8, 2), nullable=True)
    calorie_giornaliere = db.Column(db.Numeric(8, 2), nullable=True)
    settimane_dieta = db.Column(db.String, nullable=True)
    carboidrati = db.Column(db.Integer, nullable=True)
    proteine = db.Column(db.Integer, nullable=True)
    grassi = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String, nullable=False)
    diet = db.Column(db.String, nullable=True)

    alimenti = db.relationship('Alimento', backref='utente', cascade='all, delete-orphan')
    ingredienti_ricette = db.relationship('IngredientiRicetta', backref='utente', cascade='all, delete-orphan')
    menu_settimanale = db.relationship('MenuSettimanale', backref='utente', cascade='all, delete-orphan')
    registro_peso = db.relationship('RegistroPeso', backref='utente', cascade='all, delete-orphan')
    ricette = db.relationship('Ricetta', backref='utente', cascade='all, delete-orphan')
    auth = db.relationship('UtenteAuth', back_populates='utente', overlaps="utente_auth,utente_assoc")
    utente_auth = db.relationship('UtenteAuth', overlaps="auth,utente_assoc")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Alimento(db.Model):
    __tablename__ = 'alimento'
    __table_args__ = (
        UniqueConstraint('id', 'user_id', name='alimento_unique'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String(200))
    carboidrati = db.Column(db.Numeric)
    proteine = db.Column(db.Numeric)
    grassi = db.Column(db.Numeric)
    fibre = db.Column(db.Numeric)
    kcal = db.Column(Numeric, Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))", persisted=True))
    macro = db.Column(db.String(1), Computed("""
    CASE
        WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
        WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
        WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
        ELSE NULL
    END
    """, persisted=True))
    frutta = db.Column(db.Boolean, default=False)
    carne_bianca = db.Column(db.Boolean, default=False)
    carne_rossa = db.Column(db.Boolean, default=False)
    pane = db.Column(db.Boolean, default=False)
    stagionalita = db.Column(ARRAY(db.BigInteger))
    verdura = db.Column(db.Boolean, default=False)
    confezionato = db.Column(db.Boolean, default=False)
    vegan = db.Column(db.Boolean, default=False)
    pesce = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    ingredienti = db.relationship('IngredientiRicetta', back_populates='alimento')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class IngredientiRicetta(db.Model):
    __tablename__ = 'ingredienti_ricetta'
    __table_args__ = (
        UniqueConstraint('id_ricetta', 'id_alimento', 'user_id', name='ingredienti_ricetta_unique'),
        {'schema': 'dieta'}
    )

    id_ricetta = db.Column(db.BigInteger, ForeignKey('dieta.ricetta.id', ondelete='CASCADE'), primary_key=True)
    id_alimento = db.Column(db.BigInteger, ForeignKey('dieta.alimento.id', ondelete='CASCADE'), primary_key=True)
    qta = db.Column(db.Numeric)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    alimento = db.relationship('Alimento', back_populates='ingredienti')
    ricetta = db.relationship('Ricetta', back_populates='ricetta')

    def add_meal(self, meal):
        self.meals.append(meal)
        db.session.add(self)


class MenuSettimanale(db.Model):
    __tablename__ = 'menu_settimanale'
    __table_args__ = (
        UniqueConstraint('data_inizio', 'data_fine', 'user_id', name='menu_settimanale_data_inizio_data_fine_key'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.Integer, primary_key=True)
    data_inizio = db.Column(db.Date, nullable=False)
    data_fine = db.Column(db.Date, nullable=False)
    menu = db.Column(JSON, nullable=False)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'))

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
    peso_ideale = db.Column(db.Numeric)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Ricetta(db.Model):
    __tablename__ = 'ricetta'
    __table_args__ = (
        UniqueConstraint('id', 'user_id', name='ricetta_unique'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.BigInteger, primary_key=True)
    nome_ricetta = db.Column(db.Text)
    colazione = db.Column(db.Boolean, default=False)
    spuntino = db.Column(db.Boolean, default=False)
    principale = db.Column(db.Boolean, default=False)
    contorno = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=True)
    colazione_sec = db.Column(db.Boolean, default=False)
    pane = db.Column(db.Boolean, default=False)
    complemento = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.BigInteger, ForeignKey('dieta.utente.id', ondelete='CASCADE'), primary_key=True)

    ricetta = db.relationship('IngredientiRicetta', back_populates='ricetta')

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class AlimentoBase(db.Model):
    __tablename__ = 'alimento_base'
    __table_args__ = (
        UniqueConstraint('id', name='alimento_base_pkey'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String(200))
    carboidrati = db.Column(db.Numeric)
    proteine = db.Column(db.Numeric)
    grassi = db.Column(db.Numeric)
    fibre = db.Column(db.Numeric)
    kcal = db.Column(Numeric, Computed("((carboidrati * 4) + (proteine * 4) + (grassi * 9) + (fibre * 2))", persisted=True))
    macro = db.Column(db.String(1), Computed("""
    CASE
        WHEN (carboidrati * 4) >= (proteine * 4) AND (carboidrati * 4) >= (grassi * 9) THEN 'C'
        WHEN (proteine * 4) >= (carboidrati * 4) AND (proteine * 4) >= (grassi * 9) THEN 'P'
        WHEN (grassi * 9) >= (proteine * 4) AND (grassi * 9) >= (carboidrati * 4) THEN 'G'
        ELSE NULL
    END
    """, persisted=True))
    frutta = db.Column(db.Boolean, default=False)
    carne_bianca = db.Column(db.Boolean, default=False)
    carne_rossa = db.Column(db.Boolean, default=False)
    pane = db.Column(db.Boolean, default=False)
    stagionalita = db.Column(ARRAY(db.BigInteger))
    verdura = db.Column(db.Boolean, default=False)
    confezionato = db.Column(db.Boolean, default=False)
    vegan = db.Column(db.Boolean, default=False)
    pesce = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class RicettaBase(db.Model):
    __tablename__ = 'ricetta_base'
    __table_args__ = (
        UniqueConstraint('id', name='ricetta_base_pkey'),
        {'schema': 'dieta'}
    )

    id = db.Column(db.BigInteger, primary_key=True)
    nome_ricetta = db.Column(db.Text)
    colazione = db.Column(db.Boolean, default=False)
    spuntino = db.Column(db.Boolean, default=False)
    principale = db.Column(db.Boolean, default=False)
    contorno = db.Column(db.Boolean, default=False)
    enabled = db.Column(db.Boolean, default=True)
    colazione_sec = db.Column(db.Boolean, default=False)
    pane = db.Column(db.Boolean, default=False)
    complemento = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class IngredientiRicettaBase(db.Model):
    __tablename__ = 'ingredienti_ricetta_base'
    __table_args__ = (
        UniqueConstraint('id_ricetta', 'id_alimento', name='ingredienti_ricetta_base_pkey'),
        {'schema': 'dieta'}
    )

    id_ricetta = db.Column(db.BigInteger, ForeignKey('dieta.ricetta.id', ondelete='CASCADE'), primary_key=True)
    id_alimento = db.Column(db.BigInteger, ForeignKey('dieta.alimento.id', ondelete='CASCADE'), primary_key=True)
    qta = db.Column(db.Numeric)