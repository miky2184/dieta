from app.models import db

class RicettaBase(db.Model):
    __tablename__ = 'ricetta_base'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome_ricetta = db.Column(db.Text)
    colazione = db.Column(db.Boolean, default=False)
    spuntino = db.Column(db.Boolean, default=False)
    principale = db.Column(db.Boolean, default=False)
    contorno = db.Column(db.Boolean, default=False)
    colazione_sec = db.Column(db.Boolean, default=False)
    complemento = db.Column(db.Boolean, default=False)

    @classmethod
    def get_by_id(cls, ricetta_id):
        """
        Recupera un record di RicettaBase dal database usando il suo ID.

        Args:
            ricetta_id (int): ID della Ricetta base.

        Returns:
            RicettaBase: Istanza del modello RicettaBase se trovata, altrimenti None.
        """
        return cls.query.filter(cls.id == ricetta_id).first()