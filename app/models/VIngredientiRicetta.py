from app.models import db

class VIngredientiRicetta(db.Model):
    __tablename__ = 'v_ingredienti_ricetta'
    __table_args__ = {'schema': 'dieta'}

    id_ricetta = db.Column(db.BigInteger, primary_key=True)
    id_alimento = db.Column(db.BigInteger, primary_key=True)
    qta = db.Column(db.Numeric)
    removed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.BigInteger)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}