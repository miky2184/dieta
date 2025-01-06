from . import db

class IngredientiRicettaBase(db.Model):
    __tablename__ = 'ingredienti_ricetta_base'
    __table_args__ = {'schema': 'dieta'}

    id_ricetta = db.Column(db.BigInteger, db.ForeignKey('dieta.ricetta_base.id'), primary_key=True)
    id_alimento = db.Column(db.BigInteger, db.ForeignKey('dieta.alimento_base.id'), primary_key=True)
    qta = db.Column(db.Numeric, nullable=True)

    #ricetta = db.relationship('RicettaBase', back_populates='ingredienti')
    #alimento = db.relationship('AlimentoBase', back_populates='ingredienti')

    def to_dict(self):
        return {
            'id_ricetta': self.id_ricetta,
            'id_alimento': self.id_alimento,
            'qta': self.qta
        }