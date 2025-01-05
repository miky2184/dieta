import os
import random
from datetime import datetime, timedelta, date
from copy import deepcopy
import re
import sqlalchemy
from app.models import db
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from app.models.GruppoAlimentare import GruppoAlimentare
from app.models.Alimento import Alimento
from app.models.AlimentoBase import AlimentoBase
from app.models.Ricetta import Ricetta
from app.models.RicettaBase import RicettaBase
from app.models.IngredientiRicetta import IngredientiRicetta
from app.models.IngredientiRicettaBase import IngredientiRicettaBase
from sqlalchemy.orm import aliased
from sqlalchemy.sql import extract
from sqlalchemy.dialects.postgresql import insert
import json
from sqlalchemy import insert, update, and_, or_, case, func, exists, asc, String, true, false, select, desc
from collections import defaultdict
from decimal import Decimal
from app.services.util_services import printer
from app.services.common_db_service import get_sequence_value

def create_alimento_service(name, carboidrati, proteine, grassi, fibre, confezionato, vegan, gruppo, user_id):
    seq_id = get_sequence_value('dieta.seq_id_alimento')

    alimento = Alimento(
        id=seq_id,
        nome_override=name.upper(),
        carboidrati_override=carboidrati,
        proteine_override=proteine,
        grassi_override=grassi,
        fibre_override=fibre,
        confezionato_override=confezionato,
        vegan_override=vegan,
        id_gruppo_override=gruppo,
        user_id=user_id
    )

    db.session.add(alimento)

    alimento_id = alimento.id

    if confezionato:
        ricetta_id = get_sequence_value('dieta.seq_id_ricetta')
        ricetta = Ricetta(
            id=ricetta_id,
            nome_ricetta_override=name.upper(),
            user_id=user_id
        )

        db.session.add(ricetta)

        ingredienti_ricetta = IngredientiRicetta(
            id_ricetta_base=ricetta_id,
            id_alimento_base=alimento_id,
            qta_override=100,
            user_id=user_id
        )

        db.session.add(ingredienti_ricetta)

    db.session.commit()

def get_alimenti_service(user_id):
    filtro = VAlimento.filtro_alimenti(user_id)

    # Query con filtro
    query = db.session.query(VAlimento).filter(filtro).order_by(VAlimento.nome)

    results = query.all()

    printer(str(query.statement.compile(compile_kwargs={"literal_binds": True})), "DEBUG")

    alimenti = [{
        'id': r.id,
        'nome': r.nome,
        'carboidrati': r.carboidrati,
        'proteine': r.proteine,
        'grassi': r.grassi,
        'fibre': r.fibre,
        'kcal': r.kcal,
        'vegan': r.vegan,
        'confezionato': r.confezionato,
        'gruppo': r.nome_gruppo
    } for r in results]
    return alimenti


def update_alimento_service(id, nome, carboidrati, proteine, grassi, fibre, confezionato, vegan, id_gruppo, user_id):
    alimento_base = (AlimentoBase.query.filter(AlimentoBase.id==id)).first()
    alimento = Alimento.query.filter(
        Alimento.id == (id if alimento_base is None else alimento_base.id),
        Alimento.user_id == user_id
    ).first()

    if not alimento:
        alimento = Alimento(
            id=id,
            nome_override=nome.upper(),
            carboidrati_override=carboidrati,
            proteine_override=proteine,
            grassi_override=grassi,
            fibre_override=fibre,
            confezionato_override=confezionato,
            vegan_override=vegan,
            stagionalita_override=alimento_base.stagionalita,
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
        alimento.confezionato_override = confezionato
        alimento.vegan_override = vegan
        alimento.id_gruppo_override = id_gruppo

    db.session.commit()


def delete_alimento_service(alimento_id, user_id):
    alimento_base = (AlimentoBase.query.filter(AlimentoBase.id==alimento_id)).first()
    alimento = Alimento.query.filter(
        Alimento.id == (alimento_id if alimento_base is None else alimento_base.id),
        Alimento.user_id == user_id
    ).first()

    if not alimento:
        alimento = Alimento(
            id=alimento_id,
            nome_override=alimento_base.nome.upper(),
            carboidrati_override=alimento_base.carboidrati,
            proteine_override=alimento_base.proteine,
            grassi_override=alimento_base.grassi,
            fibre_override=alimento_base.fibre,
            confezionato_override=alimento_base.confezionato,
            vegan_override=alimento_base.vegan,
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


