from app.models import db

class GruppoAlimentare(db.Model):
    __tablename__ = 'gruppo_alimentare'
    __table_args__ = {'schema': 'dieta'}

    id = db.Column(db.BigInteger, primary_key=True)
    nome = db.Column(db.String, nullable=True)
    descrizione = db.Column(db.String, nullable=True)

    # Relazione con AlimentoBase
    alimenti_base = db.relationship(
        'AlimentoBase',
        primaryjoin='GruppoAlimentare.id == AlimentoBase.id_gruppo',
        back_populates='gruppo_alimentare',
        lazy='select'
    )

    # Relazione con Alimento
    alimenti = db.relationship(
        'Alimento',
        primaryjoin='GruppoAlimentare.id == Alimento.id_gruppo_override',
        back_populates='gruppo_alimentare',
        lazy='select'
    )

    @classmethod
    def get_all(cls):
        """
        Recupera tutti i record di GruppoAlimentare dal database.

        Returns:
            list[dict]: Una lista di dizionari con i dati dei gruppi alimentari.
        """
        gruppi = cls.query.all()
        return [{'id': g.id, 'nome': g.nome} for g in gruppi]