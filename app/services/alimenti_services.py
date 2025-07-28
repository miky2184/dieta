from app.models import db
from app.models.Alimento import Alimento
from app.models.AlimentoBase import AlimentoBase
from app.models.IngredientiRicetta import IngredientiRicetta
from app.models.IngredientiRicettaBase import IngredientiRicettaBase
from app.models.VAlimento import VAlimento
from app.services.db_services import get_sequence_value


def create_alimento_service(name, carboidrati, proteine, grassi, fibre, vegan, surgelato, gruppo, user_id):
    seq_id = get_sequence_value('dieta.seq_id_alimento')

    alimento = Alimento(
        id=seq_id,
        nome_override=name.upper(),
        carboidrati_override=carboidrati,
        proteine_override=proteine,
        grassi_override=grassi,
        fibre_override=fibre,
        vegan_override=vegan,
        surgelato_override=surgelato,
        id_gruppo_override=gruppo,
        user_id=user_id
    )

    db.session.add(alimento)
    db.session.commit()

def get_alimenti_service(user_id):
    filtro = VAlimento.filtro_alimenti(user_id)

    # Query con filtro
    query = db.session.query(VAlimento).filter(filtro).order_by(VAlimento.nome)

    results = query.all()

    alimenti = [{
        'id': r.id,
        'nome': r.nome,
        'carboidrati': r.carboidrati,
        'proteine': r.proteine,
        'grassi': r.grassi,
        'fibre': r.fibre,
        'kcal': r.kcal,
        'vegan': r.vegan,
        'surgelato': r.surgelato,
        'gruppo': r.nome_gruppo,
        'stagionalita': r.stagionalita
    } for r in results]
    return alimenti


def update_alimento_service(alimento_id, nome, carboidrati, proteine, grassi, fibre, vegan, surgelato, id_gruppo, stagionalita, user_id):
    alimento_base = AlimentoBase.get_by_id(alimento_id)
    if alimento_base:
        alimento_id = alimento_base.id
    alimento = Alimento.get_by_id_and_user(alimento_id, user_id)

    if not alimento:
        alimento = Alimento(
            id=alimento_id,
            nome_override=nome.upper(),
            carboidrati_override=carboidrati,
            proteine_override=proteine,
            grassi_override=grassi,
            fibre_override=fibre,
            vegan_override=vegan,
            surgelato_override=surgelato,
            stagionalita_override=stagionalita if stagionalita is not None else alimento_base.stagionalita,
            id_gruppo_override = id_gruppo if id_gruppo is not None else alimento_base.id_gruppo,
            user_id=user_id
        )
        db.session.add(alimento)
    else:
        alimento.nome_override = nome.upper()
        alimento.carboidrati_override = carboidrati
        alimento.proteine_override = proteine
        alimento.grassi_override = grassi
        alimento.fibre_override = fibre
        alimento.vegan_override = vegan
        alimento.surgelato_override = surgelato
        alimento.stagionalita_override = stagionalita if stagionalita is not None else alimento.stagionalita_override
        alimento.id_gruppo_override = id_gruppo if id_gruppo is not None else alimento.id_gruppo_override

    db.session.commit()


def delete_alimento_service(alimento_id, user_id):
    alimento_base = AlimentoBase.get_by_id(alimento_id)
    if alimento_base:
        alimento_id = alimento_base.id
    alimento = Alimento.get_by_id_and_user(alimento_id, user_id)

    if not alimento:
        alimento = Alimento(
            id=alimento_id,
            nome_override=alimento_base.nome.upper(),
            carboidrati_override=alimento_base.carboidrati,
            proteine_override=alimento_base.proteine,
            grassi_override=alimento_base.grassi,
            fibre_override=alimento_base.fibre,
            vegan_override=alimento_base.vegan,
            surgelato_override=alimento_base.surgelato,
            stagionalita_override=alimento_base.stagionalita,
            id_gruppo_override = alimento_base.id_gruppo,
            removed = True,
            user_id=user_id
        )
        db.session.add(alimento)
    else:
        alimento.removed = True

    ingredienti_ricetta = IngredientiRicetta.query.filter_by(id_alimento_base=alimento_id, user_id=user_id).all()

    for ir in ingredienti_ricetta:
        ir.removed = True

    ingredienti_ricetta_base = IngredientiRicettaBase.query.filter_by(id_alimento=alimento_id).all()

    for irb in ingredienti_ricetta_base:
        ingredienti_ricetta = IngredientiRicetta.query.filter(
        IngredientiRicetta.id_ricetta_base == irb.id_ricetta,
        IngredientiRicetta.id_alimento_base == irb.id_alimento,
        Alimento.user_id == user_id).first()

        if not ingredienti_ricetta:
            i = IngredientiRicetta(
            id_ricetta_base=irb.id_ricetta,
            id_alimento_base = irb.id_alimento,
            user_id = user_id,
            qta_override = irb.qta,
            removed = True)
            db.session.add(i)

    db.session.commit()


