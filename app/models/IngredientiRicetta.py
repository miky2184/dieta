from app.models import db

class IngredientiRicetta(db.Model):
    __tablename__ = 'ingredienti_ricetta'
    __table_args__ = {'schema': 'dieta'}

    id_ricetta_base = db.Column(db.BigInteger, primary_key=True)
    id_alimento_base = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, primary_key=True)
    qta_override = db.Column(db.Numeric, nullable=True)
    removed = db.Column(db.Boolean, default=False)

    #ricetta_base = db.relationship('RicettaBase', back_populates='ingredienti_personalizzati')
    #alimento_base = db.relationship('AlimentoBase', back_populates='ingredienti_personalizzati')
    #utente = db.relationship('Utente', back_populates='ingredienti')

    def to_dict(self):
        return {
            'id_ricetta_base': self.id_ricetta_base,
            'id_alimento_base': self.id_alimento_base,
            'user_id': self.user_id,
            'qta_override': self.qta_override
        }