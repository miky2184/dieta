from sqlalchemy import CheckConstraint

from app.models import db


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
    dieta = db.Column(db.String, nullable=True)

    menu_settimanale = db.relationship('MenuSettimanale', backref='utente', cascade='all, delete-orphan')
    registro_peso = db.relationship('RegistroPeso', backref='utente', cascade='all, delete-orphan')

    auth = db.relationship('UtenteAuth', back_populates='utente', overlaps="utente_auth,utente_assoc")
    utente_auth = db.relationship('UtenteAuth', overlaps="auth,utente_assoc")

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def get_by_email(cls, email: str):
        """
        Recupera un utente dal database in base all'email.

        Args:
            email (str): Email dell'utente.

        Returns:
            Utente: Istanza del modello Utente o None se non trovato.
        """
        return cls.query.filter_by(email=email.lower()).first()

    @classmethod
    def get_by_id(cls, user_id: int):
        """
        Recupera un utente dal database in base al id.

        Args:
            user_id (int): Email dell'utente.

        Returns:
            Utente: Istanza del modello Utente o None se non trovato.
        """
        return cls.query.filter_by(id=user_id).first()
