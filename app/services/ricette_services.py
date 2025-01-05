import os
import random
from datetime import datetime, timedelta, date
from copy import deepcopy
import re
import sqlalchemy
from app.models import db
from app.models.Utente import Utente
from app.models.MenuSettimanale import MenuSettimanale
from app.models.RegistroPeso import RegistroPeso
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
from sqlalchemy import insert, update, and_, or_, not_, case, func, exists, asc, String, true, false, select, desc
from collections import defaultdict
from decimal import Decimal
from app.services.util_services import printer
from app.services.common_db_service import get_sequence_value

def get_ricette_service(user_id, ids=None, stagionalita: bool=False, attive:bool=False, complemento=None, contorno=False, data_stagionalita=None) -> list[dict]:
    """
    Carica tutte le ricette disponibili dal database, arricchendole con informazioni nutrizionali e ingredienti.

    Args:
        user_id (int): ID dell'utente per il quale caricare le ricette.
        ids (list[int], optional): Filtra le ricette con gli ID specificati.
        stagionalita (bool, optional): Se True, applica un filtro per la stagionalità degli ingredienti.
        attive (bool, optional): Se True, filtra le ricette che sono attive.
        complemento (bool, optional): Se specificato, filtra le ricette con o senza il flag `complemento`.
        contorno (bool, optional): Se True, filtra le ricette con il flag `contorno` attivo.
        data_stagionalita (date, optional): Data specifica per applicare il filtro di stagionalità (predefinito è la data corrente).

    Returns:
        list[dict]: Lista di ricette arricchite con informazioni nutrizionali, stagionalità e ingredienti.
    """
    # Alias per le tabelle
    ir = aliased(VIngredientiRicetta)
    a = aliased(VAlimento)
    r = aliased(VRicetta)

    # Subquery per calcolare 'ricetta' con COALESCE per gestire informazioni base e override
    ricetta_subquery = (
        db.session.query(
            func.string_agg(a.nome + ': ' + func.cast(ir.qta, String) + 'g', ', ')
        ).distinct()
        .join(ir, ir.id_alimento == a.id)
        .filter(ir.id_ricetta == r.id)
        .filter(func.coalesce(ir.user_id, user_id) == user_id)
        .filter(ir.removed == False)
        .correlate(r)
        .label('ricetta')
    )

    # Subquery per gli ingredienti della ricetta
    ingredienti_subquery = (
        db.session.query(
            ir.id_ricetta.label("id_ricetta"),
            a.id_gruppo.label("id_gruppo"),
            func.sum(ir.qta).label("qta_totale")
        )
        .join(a, ir.id_alimento == a.id)
        .filter(func.coalesce(ir.user_id, user_id) == user_id, ir.removed == False)
        .group_by(ir.id_ricetta, a.id_gruppo)
        .subquery()
    )

    # Base query
    query = db.session.query(
        r.user_id,
        r.id,
        r.nome_ricetta,
        func.ceil(func.sum(
            (a.carboidrati / 100 * ir.qta * 4) +
            (a.proteine / 100 * ir.qta * 4) +
            (a.grassi / 100 * ir.qta * 9) +
            (a.fibre / 100 * ir.qta * 2)
        ).over(partition_by=r.id)).label('kcal'),
        func.round(func.sum(a.carboidrati / 100 * ir.qta).over(partition_by=r.id), 2).label('carboidrati'),
        func.round(func.sum(a.proteine / 100 * ir.qta).over(partition_by=r.id), 2).label('proteine'),
        func.round(func.sum(a.grassi / 100 * ir.qta).over(partition_by=r.id), 2).label('grassi'),
        func.round(func.sum(a.fibre / 100 * ir.qta).over(partition_by=r.id), 2).label('fibre'),
        r.colazione,
        r.spuntino,
        r.principale,
        r.contorno,
        r.colazione_sec,
        r.complemento,
        r.enabled.label('attiva'),
        func.coalesce(ricetta_subquery, '').label('ricetta'),
        func.cast(
            func.json_agg(
                func.json_build_object(
                    'id_gruppo', ingredienti_subquery.c.id_gruppo,
                    'qta_totale', ingredienti_subquery.c.qta_totale
                )
            ), String
        ).label("ingredienti")
    ).outerjoin(
        ir, ir.id_ricetta == r.id
    ).outerjoin(
        a, ir.id_alimento == a.id
    ).outerjoin(
        ingredienti_subquery, ingredienti_subquery.c.id_ricetta == r.id
    ).filter(
        func.coalesce(r.user_id, user_id) == user_id
    )

    # Applicazione dei filtri
    if stagionalita:
        data = func.current_date()
        if data_stagionalita:
            data = data_stagionalita

        query = query.filter(
            or_(
                and_(
                    a.id_gruppo == 6, (extract('month', data) == func.any(a.stagionalita))
                ),
                (
                        a.id_gruppo != 6)
                )
        )

    if ids:
        query = query.filter(r.id == ids)

    if attive:
        query = query.filter(r.enabled.is_(True), func.coalesce(r.user_id, user_id) == user_id)

    if complemento:
        query = query.filter(r.complemento.is_(True), func.coalesce(r.user_id, user_id) == user_id)
    elif complemento is False:
        query = query.filter(r.complemento.is_(False), func.coalesce(r.user_id, user_id) == user_id)

    if contorno:
        query = query.filter(r.contorno.is_(True), func.coalesce(r.user_id, user_id) == user_id)

    # Raggruppamento e ordinamento
    query = query.group_by(
        r.user_id,
        r.id,
        r.nome_ricetta,
        a.carboidrati,
        a.proteine,
        a.grassi,
        a.fibre,
        ir.qta,
        r.colazione,
        r.spuntino,
        r.principale,
        r.contorno,
        r.colazione_sec,
        r.complemento,
        r.enabled
    ).order_by(
        r.enabled.desc(),
        r.nome_ricetta
    )

    # Esecuzione della query
    results = query.distinct().all()
    # Conversione dei risultati in una lista di dizionari serializzabili in JSON
    ricette = []
    for row in results:
        ricette.append({
            'user_id': row.user_id,
            'id': row.id,
            'nome_ricetta': row.nome_ricetta,
            'kcal': float(row.kcal or 0),
            'carboidrati': float(row.carboidrati or 0),
            'proteine': float(row.proteine or 0),
            'grassi': float(row.grassi or 0),
            'fibre': float(row.fibre or 0),
            'colazione': row.colazione,
            'spuntino': row.spuntino,
            'principale': row.principale,
            'contorno': row.contorno,
            'colazione_sec': row.colazione_sec,
            'complemento': row.complemento,
            'attiva': row.attiva,
            'ricetta': row.ricetta,
            'ingredienti': json.loads(row.ingredienti) if row.ingredienti else []  # Include gli ingredienti
        })

    printer(str(query.statement.compile(compile_kwargs={"literal_binds": True})), "DEBUG")
    return ricette


def create_ricetta_service(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id):
    ricetta_base = VRicetta.query.filter(VRicetta.id==ricetta_id).filter(func.coalesce(VRicetta.user_id, user_id)==user_id).first()
    ricetta = Ricetta.query.filter_by(id=ricetta_base.id, user_id=user_id).first()

    if not ricetta:
        ricetta = Ricetta(
            id = ricetta_base.id,
            nome_ricetta_override = nome.upper(),
            colazione_override = colazione,
            colazione_sec_override = colazione_sec,
            spuntino_override = spuntino,
            principale_override = principale,
            contorno_override = contorno,
            complemento_override = complemento,
            user_id=user_id
        )
    else:
        ricetta.nome_ricetta_override = nome.upper()
        ricetta.colazione_override = colazione
        ricetta.colazione_sec_override = colazione_sec
        ricetta.spuntino_override = spuntino
        ricetta.principale_override = principale
        ricetta.contorno_override = contorno
        ricetta.complemento_override = complemento

    db.session.add(ricetta)
    db.session.commit()


def attiva_disattiva_ricetta_service(ricetta_id, user_id):
    ricetta = (Ricetta.query.filter(Ricetta.id == ricetta_id)
               .filter(Ricetta.user_id == user_id)).first()

    if not ricetta:
        ricetta = Ricetta(
            id=ricetta_id,
            user_id=user_id,
            enabled=False
        )
    else:
        ricetta.id = ricetta_id
        ricetta.user_id = user_id
        ricetta.enabled = not ricetta.enabled

    db.session.add(ricetta)
    db.session.commit()


def get_ingredienti_ricetta_service(recipe_id, user_id):

    vir = aliased(VIngredientiRicetta)
    vr = aliased(VRicetta)
    va = aliased(VAlimento)

    # Sottoquery EXISTS
    subquery = (
        db.session.query(vr.id)
        .filter(and_(vr.id == recipe_id, vr.user_id == user_id))
        .exists()
    )

    # Query principale
    query = (
        db.session.query(
            va.id.label("id_alimento"),
            va.nome.label("nome_alimento"),
            vr.id.label("id_ricetta"),
            vr.nome_ricetta.label("nome_ricetta"),
            vir.qta.label("quantita")
        )
        .join(va, and_(va.id == vir.id_alimento, vir.user_id == va.user_id))
        .join(vr, and_(vr.id == vir.id_ricetta, vir.user_id == vr.user_id))
        .filter(
            and_(
                vr.id == recipe_id,
                or_(
                    and_(vr.user_id == user_id, not_(vr.removed)),
                    and_(vr.user_id == 0, not_(subquery))
                )
            )
        )
    )

    results = query.all()

    r = []
    for res in results:
        r.append({
            "id": res.id_alimento,
            "nome": res.nome_alimento,
            "nome_ricetta": res.nome_ricetta,
            "qta": res.quantita,
            "id_ricetta": res.id_ricetta
        })

    return r