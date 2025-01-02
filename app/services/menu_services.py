#app/services/menu_services.py
import os
import random
from datetime import datetime, timedelta, date
from copy import deepcopy
import re
import math
from app.models.models import (db, Utente, MenuSettimanale, RegistroPeso )
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
from sqlalchemy import insert, update, and_, or_, case, func, exists, asc, String, true, false, select, desc, result_tuple
from collections import defaultdict
from decimal import Decimal

MAX_RETRY = int(os.getenv('MAX_RETRY'))

LIMITI_CONSUMO = {
    'uova': 4,          # Numero massimo di uova a settimana
    'pesce': 3,         # Porzioni di pesce a settimana
    'carne_rossa': 1,   # Porzioni di carne rossa a settimana
    'carne_bianca': 2,  # Porzioni di carne bianca a settimana
    'legumi': 4,        # Porzioni di legumi a settimana
    'pasta': 5          # Porzioni di pasta a settimana
}

def scegli_pietanza(settimana, giorno_settimana: str, pasto: str, tipo: str, ripetibile: bool,
                    controllo_macro_settimanale: bool, ricette, user_id, ids_specifici=None, skip_check=False):
    """
    Seleziona una pietanza dalla lista di ricette pre-caricate in memoria.
    Ora lascia che select_food determini la percentuale ottimale basata sui macronutrienti rimanenti.
    """
    # Filtra le ricette in base al tipo di pasto richiesto
    ricette_filtrate = [r for r in ricette if r[tipo]]

    # Moltiplica i valori nutrizionali per la percentuale, lascia che select_food lo faccia
    ricette_modificate = []
    for ricetta in ricette_filtrate:
        if ricetta['attiva']:
            ricetta_modificata = {
                'id': ricetta['id'],
                'nome_ricetta': ricetta['nome_ricetta'],
                'kcal': ricetta['kcal'],  # Lasciamo la quantità originale per la modifica in select_food
                'carboidrati': ricetta['carboidrati'],
                'proteine': ricetta['proteine'],
                'grassi': ricetta['grassi'],
                'colazione': ricetta['colazione'],
                'spuntino': ricetta['spuntino'],
                'principale': ricetta['principale'],
                'contorno': ricetta['contorno'],
                'ricetta': ricetta['ricetta']
            }
            ricette_modificate.append(ricetta_modificata)

    # Invoca select_food con le ricette modificate e gli ID specifici
    return select_food(ricette_modificate, settimana, giorno_settimana, pasto, ripetibile,
                       False, controllo_macro_settimanale, skip_check, user_id, ids_specifici)


def select_food(ricette, settimana, giorno_settimana, pasto, ripetibile, found, controllo_macro_settimanale, skip_check, user_id, ids_specifici=None):
    # Filtra gli ID disponibili in base alla ripetibilità e agli ID specifici
    if ids_specifici:
        ids_disponibili = [oggetto['id'] for oggetto in ricette if oggetto['id'] in ids_specifici and oggetto['id'] not in settimana['all_food']]
    else:
        ids_disponibili = [oggetto['id'] for oggetto in ricette if oggetto['id'] not in settimana['all_food']] if not ripetibile else [oggetto['id'] for oggetto in ricette if oggetto['id'] not in settimana['day'][giorno_settimana]['pasto'][pasto]['ids']]

    # Filtra ulteriormente le ricette disponibili in base ai macronutrienti e alle altre condizioni
    ricette_filtrate = [ricetta for ricetta in ricette if ricetta['id'] in ids_disponibili and (skip_check or check_macronutrienti(ricetta, settimana['day'][giorno_settimana], settimana['weekly'], controllo_macro_settimanale))]

    if not ricette_filtrate:
        return found

    random.shuffle(ricette_filtrate)

    for ricetta in ricette_filtrate:
        # Calcola la percentuale massima che può essere utilizzata per ogni macronutriente
        percentuali_possibili = []

        if ricetta['kcal'] > 0:
            percentuali_possibili.append(float(settimana['day'][giorno_settimana]['kcal']) / float(ricetta['kcal']))

        if ricetta['carboidrati'] > 0:
            percentuali_possibili.append(float(settimana['day'][giorno_settimana]['carboidrati']) / float(ricetta['carboidrati']))

        if ricetta['proteine'] > 0:
            percentuali_possibili.append(float(settimana['day'][giorno_settimana]['proteine']) / float(ricetta['proteine']))

        if ricetta['grassi'] > 0:
            percentuali_possibili.append(float(settimana['day'][giorno_settimana]['grassi']) / float(ricetta['grassi']))

        # Se nessuna percentuale è calcolabile, salta questa ricetta
        if not percentuali_possibili:
            continue

        # Prendi la percentuale minima trovata, limitata al range 0.5 - 1.0
        percentuale_effettiva = max(0.5, min(1.0, min(percentuali_possibili)))
        percentuale_effettiva = float(math.floor(percentuale_effettiva * 10) / 10)

        if percentuale_effettiva >= 0.5:  # Considera solo percentuali superiori o uguali al 50%
            id_selezionato = ricetta['id']
            ricetta_selezionata = next(oggetto for oggetto in ricette if oggetto['id'] == id_selezionato)

            mt = settimana.get('day').get(giorno_settimana).get('pasto').get(pasto)
            day = settimana.get('day').get(giorno_settimana)
            macronutrienti_settimali = settimana.get('weekly')

            if (skip_check or check_macronutrienti(ricetta_selezionata, settimana['day'][giorno_settimana], settimana['weekly'], controllo_macro_settimanale)):
                settimana.get('all_food').append(id_selezionato)
                mt.get('ids').append(id_selezionato)

                ingredienti_ricetta = recupera_ingredienti_ricetta(ricetta_selezionata.get('id'), user_id, percentuale_effettiva)

                r = {
                        'qta': percentuale_effettiva,
                        'id': ricetta_selezionata.get('id'),
                        'nome_ricetta': ricetta_selezionata.get('nome_ricetta'),
                        'ricetta': ingredienti_ricetta,
                        'kcal': ricetta_selezionata.get('kcal'),
                        'carboidrati': ricetta_selezionata.get('carboidrati'),
                        'proteine':  ricetta_selezionata.get('proteine'),
                        'grassi': ricetta_selezionata.get('grassi')
                    }
                mt.get('ricette').append(r)
                day['kcal'] = round(day.get('kcal') - (round(ricetta_selezionata.get('kcal') * percentuale_effettiva, 2)), 2)
                day['carboidrati'] = round(day.get('carboidrati') - (round(ricetta_selezionata.get('carboidrati') * percentuale_effettiva, 2)), 2)
                day['proteine'] = round(day.get('proteine') - (round(ricetta_selezionata.get('proteine') * percentuale_effettiva, 2)), 2)
                day['grassi'] = round(day.get('grassi') - (round(ricetta_selezionata.get('grassi') * percentuale_effettiva, 2)), 2)
                macronutrienti_settimali['kcal'] = round(macronutrienti_settimali.get('kcal') - (round(ricetta_selezionata.get('kcal') * percentuale_effettiva, 2)), 2)
                macronutrienti_settimali['carboidrati'] = round(macronutrienti_settimali.get('carboidrati') - (round(ricetta_selezionata.get('carboidrati') * percentuale_effettiva, 2)), 2)
                macronutrienti_settimali['proteine'] =round( macronutrienti_settimali.get('proteine') - (round(ricetta_selezionata.get('proteine') * percentuale_effettiva, 2)), 2)
                macronutrienti_settimali['grassi'] =round( macronutrienti_settimali.get('grassi') - (round(ricetta_selezionata.get('grassi') * percentuale_effettiva, 2)), 2)
                found = True
                break  # Esci dal ciclo una volta trovata una ricetta valida

    return found


def recupera_ingredienti_ricetta(ricetta_id, user_id, percentuale):

    ir = aliased(VIngredientiRicetta)
    r = aliased(VRicetta)
    a = aliased(VAlimento)

    ricetta_subquery = (
        db.session.query(
            func.string_agg(a.nome + ': ' + func.cast(ir.qta * percentuale, String) + 'g', ', ')
        ).distinct()
        .join(ir, ir.id_alimento == a.id)
        .join(r, ir.id_ricetta == r.id)
        .filter(ir.id_ricetta == ricetta_id)
        .filter(func.coalesce(ir.user_id, user_id) == user_id)
        .filter(ir.removed == False)
        .correlate(r)
        .label('ingredienti')
    )

    query = db.session.query(
        func.coalesce(ricetta_subquery, '').label('ricetta')
    )

    results = query.distinct().all()

    return results[0].ricetta


def check_macronutrienti(ricetta, day, weekly, controllo_macro_settimanale):
    return (
            float(day['kcal']) - ricetta['kcal'] > 0 and
            float(day['carboidrati']) - ricetta['carboidrati'] > 0 and
            float(day['proteine']) - ricetta['proteine'] > 0 and
            float(day['grassi']) - ricetta['grassi'] > 0
           ) or (controllo_macro_settimanale and
            float(weekly['kcal']) - ricetta['kcal'] > 0
            and float(weekly['carboidrati']) - ricetta['carboidrati'] > 0
            and float(weekly['proteine']) - ricetta['proteine'] > 0
            and float(weekly['grassi']) - ricetta['grassi'] > 0)


def carica_ricette(user_id, ids=None, stagionalita: bool=False, attive:bool=False, complemento=None, contorno=False, data_stagionalita=None):
    """
    Carica tutte le ricette disponibili dal database in memoria.
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
        func.coalesce(ricetta_subquery, '').label('ricetta')
    ).outerjoin(
        ir, (ir.id_ricetta == r.id)
    ).outerjoin(
        a, (ir.id_alimento == a.id)
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
            'ricetta': row.ricetta
        })

    return ricette


def ordina_settimana_per_kcal(settimana):
    """
    Ordina i giorni della settimana in base alle calorie giornaliere rimanenti in ordine decrescente.
    """
    giorni_ordinati = sorted(settimana['day'].keys(), key=lambda giorno: settimana['day'][giorno]['kcal'], reverse=True)

    # Crea una nuova struttura della settimana con i giorni ordinati
    settimana_ordinata = {
        'weekly': settimana['weekly'],
        'day': {giorno: settimana['day'][giorno] for giorno in giorni_ordinati},
        'all_food': settimana['all_food']
    }

    return settimana_ordinata

def numero_ricette(p, pasto, tipo_ricetta, ricette):
    cerca_ricette = [r for r in p[pasto]['ricette'] if r['id'] in [ricetta['id'] for ricetta in ricette if ricetta[tipo_ricetta]]]
    return len(cerca_ricette)

def genera_menu(settimana, controllo_macro_settimanale, ricette, user_id) -> None:
    for giorno in settimana['day']:
        for _ in range(MAX_RETRY):
            p = settimana['day'][giorno]['pasto']

            if numero_ricette(p, 'colazione', 'colazione', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'colazione', 'colazione', True, controllo_macro_settimanale, ricette, user_id)
                scegli_pietanza(settimana, giorno, 'colazione', 'colazione_sec', True, controllo_macro_settimanale, ricette, user_id)

            if numero_ricette(p, 'spuntino_mattina', 'spuntino', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'spuntino_mattina', 'spuntino', True, controllo_macro_settimanale, ricette, user_id)

            if numero_ricette(p, 'spuntino_pomeriggio', 'spuntino', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'spuntino_pomeriggio', 'spuntino', True, controllo_macro_settimanale, ricette, user_id)

            if numero_ricette(p, 'spuntino_sera', 'spuntino', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'spuntino_sera', 'spuntino', True, controllo_macro_settimanale, ricette, user_id)


            if numero_ricette(p, 'pranzo', 'principale', ricette) < 2:
                scegli_pietanza(settimana, giorno, 'pranzo', 'principale', False, controllo_macro_settimanale, ricette, user_id)

            if numero_ricette(p, 'cena', 'principale', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'cena', 'principale', False, controllo_macro_settimanale, ricette, user_id)

            if numero_ricette(p, 'pranzo', 'contorno', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'pranzo', 'contorno', True, controllo_macro_settimanale, ricette, user_id)

            if numero_ricette(p, 'cena', 'contorno', ricette) < 1:
                scegli_pietanza(settimana, giorno, 'cena', 'contorno', True, controllo_macro_settimanale, ricette, user_id)


def definisci_calorie_macronutrienti(user_id) -> Utente:
    """Calcola le calorie e i macronutrienti giornalieri e li restituisce."""
    rows = Utente.query.filter_by(id=user_id).one()

    return rows


def stampa_lista_della_spesa(user_id: int, menu: dict, print_macro: bool = False) -> list[dict]:
    """
    Genera una lista della spesa basata sul menu settimanale.

    Args:
        user_id (int): ID dell'utente.
        menu (dict): Menu settimanale.
        print_macro (bool): Se vero, include i macronutrienti nella lista.

    Returns:
        list[dict]: Lista della spesa con ingredienti e quantità.
    """

    # Alias per le tabelle
    ir = aliased(VIngredientiRicetta)
    a = aliased(VAlimento)
    r = aliased(VRicetta)

    results = (db.session.query(
        (r.id).label('id_ricetta'),
        (a.nome).label('nome'),
        func.sum(ir.qta).label('qta_totale')
    ).join(a, a.id == ir.id_alimento)
               .join(r, r.id == ir.id_ricetta)
               .filter(ir.removed == False)
               #.filter(func.coalesce(a.user_id, 1) == func.coalesce(ir.user_id,1))
               #.filter(func.coalesce(r.user_id, 1) == func.coalesce(ir.user_id, 1))
               .filter(func.coalesce(ir.user_id, user_id) == user_id)
               .filter(ir.id_ricetta.in_(menu['all_food']))
               .group_by(r.id, a.nome ).order_by(a.nome).all())

    ingredient_totals = defaultdict(float)
    ricetta_qta = []
    # Itera sui giorni
    for day, day_data in menu["day"].items():
        # Itera sui pasti del giorno
        for meal_name, meal_data in day_data["pasto"].items():
            # Itera sulle ricette del pasto
            for ricetta in meal_data["ricette"]:
                # Nome dell'ingrediente e quantità (moltiplicata per il fattore `qta`)
                ricetta_id = ricetta["id"]
                qta = ricetta["qta"]

                # Aggiungi la quantità al totale dell'ingrediente
                ingredient_totals[ricetta_id] += qta

    # Stampa le quantità totali per ogni ingrediente
    for ingredient, total in ingredient_totals.items():
        ricetta_qta.append({"id": ingredient, "qta": total})

    qta_map = {item['id']: item['qta'] for item in ricetta_qta}

    # Crea un dizionario per aggregare le quantità degli ingredienti
    ingredienti_totali = {}

    # Itera attraverso i risultati
    for result in results:
        ricetta_id, ingrediente_nome, quantita = result

        # Moltiplica la quantità per il moltiplicatore corrispondente
        if ricetta_id in qta_map:
            quantita_moltiplicata = quantita * Decimal(qta_map[ricetta_id])

            # Aggiungi o somma la quantità moltiplicata nel dizionario degli ingredienti totali
            if ingrediente_nome in ingredienti_totali:
                ingredienti_totali[ingrediente_nome] += quantita_moltiplicata
            else:
                ingredienti_totali[ingrediente_nome] = quantita_moltiplicata

    # Trasforma i risultati in una lista di dizionari
    lista_della_spesa = [{'alimento': ingrediente, 'qta_totale': float(qta_totale)}
                         for ingrediente, qta_totale in ingredienti_totali.items()
                         if float(qta_totale) > 0]

    return lista_della_spesa


def salva_menu(menu, user_id, period: dict = None):

    if not period:
        period = {}
        last_menu = MenuSettimanale.query.filter_by(user_id=user_id).order_by(desc(MenuSettimanale.data_fine)).first()
        period['data_inizio'] = last_menu.data_inizio + timedelta(days=7)
        period['data_fine'] = last_menu.data_fine + timedelta(days=7)


    # Inserisce un nuovo menu per la prossima settimana
    new_menu_settimanale = MenuSettimanale(
        data_inizio=period['data_inizio'],
        data_fine=period['data_fine'],
        menu=menu,
        user_id=user_id
    )

    db.session.add(new_menu_settimanale)
    db.session.commit()


def get_menu(user_id: int, period: dict = None, ids: int = None):
    query = db.session.query(
        MenuSettimanale.menu.label('menu'),
        MenuSettimanale.data_fine.label('data_fine')
    ).filter_by(user_id=user_id)

    if ids:
        query = query.filter(MenuSettimanale.id == ids)
    else:
        query = query.filter(and_(MenuSettimanale.data_inizio == period['data_inizio'],
                                  MenuSettimanale.data_fine == period['data_fine']))

    result = query.first()

    # Restituisci i valori se il risultato esiste
    if result:
        return {'menu': result.menu, 'data_fine': result.data_fine}
    else:
        return None  # Nessun risultato trovato


def get_settimane_salvate(user_id, show_old_week: bool = False):
    # Ottieni la data odierna
    oggi = datetime.now().date()

    query = MenuSettimanale.query.order_by(asc(MenuSettimanale.data_inizio))

    if not show_old_week:
        query = query.filter(MenuSettimanale.data_fine >= oggi)

    settimane = query.filter(MenuSettimanale.user_id == user_id).all()

    return settimane

def save_weight(data, user_id):

    utente = Utente.query.filter_by(id=user_id).one()

    if utente.peso_ideale is None:
        return False

    registro_peso = RegistroPeso.query.order_by(desc(RegistroPeso.data_rilevazione)).filter(RegistroPeso.data_rilevazione <= data['date'], RegistroPeso.user_id==user_id).first()

    if registro_peso and registro_peso.data_rilevazione == datetime.now().date():
        registro_peso.peso = data['weight'] or None
        registro_peso.vita = data['vita'] or None
        registro_peso.fianchi = data['fianchi'] or None
    else:

        peso_ideale_successivo = RegistroPeso.query.order_by(asc(RegistroPeso.data_rilevazione)).filter(
            RegistroPeso.data_rilevazione >= data['date'], RegistroPeso.user_id == user_id).first()

        print(registro_peso.peso_ideale)

        print(peso_ideale_successivo.peso_ideale)

        print((registro_peso.data_rilevazione - datetime.strptime(data['date'], '%Y-%m-%d').date()).days)

        peso_ideale_calcolato = registro_peso.peso_ideale - (((registro_peso.peso_ideale - peso_ideale_successivo.peso_ideale) / 7) * (registro_peso.data_rilevazione - datetime.strptime(data['date'], '%Y-%m-%d').date()).days )

        registro_peso = RegistroPeso(
            data_rilevazione=data['date'],
            peso=data['weight'] or None,
            vita=data['vita'] or None,
            fianchi=data['fianchi'] or None,
            peso_ideale=round(peso_ideale_calcolato, 1),
            user_id=user_id
        )

    db.session.add(registro_peso)
    db.session.commit()

    return True


def get_peso_hist(user_id):
    results = RegistroPeso.query.filter_by(user_id=user_id).order_by(asc(RegistroPeso.data_rilevazione)).all()
    peso = [record.to_dict() for record in results]
    return peso


def get_settimana(macronutrienti: Utente):
    ricetta = {'ids': [], 'ricette': []}

    pasto = {'colazione': deepcopy(ricetta),
             'spuntino_mattina': deepcopy(ricetta),
             'pranzo': deepcopy(ricetta),
             'spuntino_pomeriggio': deepcopy(ricetta),
             'cena': deepcopy(ricetta),
             'spuntino_sera': deepcopy(ricetta)
             }

    macronutrienti_giornalieri = {
        'carboidrati': float(macronutrienti.carboidrati),
        'proteine': float(macronutrienti.proteine),
        'grassi': float(macronutrienti.grassi),
        'kcal': float(macronutrienti.calorie_giornaliere),
        'pasto': deepcopy(pasto)
    }

    macronutrienti_settimali = {
        'carboidrati': float(macronutrienti.carboidrati) * 7,
        'proteine': float(macronutrienti.proteine) * 7,
        'grassi': float(macronutrienti.grassi) * 7,
        'kcal': float(macronutrienti.calorie_giornaliere) * 7
    }

    consumi_settimanali = {key: 0 for key in LIMITI_CONSUMO.keys()}  # Inizializza i consumi settimanali

    return {'weekly': macronutrienti_settimali,
            'day': {
                'lunedi': deepcopy(macronutrienti_giornalieri),
                'martedi': deepcopy(macronutrienti_giornalieri),
                'mercoledi': deepcopy(macronutrienti_giornalieri),
                'giovedi': deepcopy(macronutrienti_giornalieri),
                'venerdi': deepcopy(macronutrienti_giornalieri),
                'sabato': deepcopy(macronutrienti_giornalieri),
                'domenica': deepcopy(macronutrienti_giornalieri)
            },
            'all_food': [],
            'consumi': consumi_settimanali  # Aggiungi il contatore settimanale
            }


def aggiorna_ricetta(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id):
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

def attiva_o_disattiva_ricetta(ricetta_id, user_id):
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


def get_ricette(recipe_id, user_id):

    ir = aliased(VIngredientiRicetta)
    r = aliased(VRicetta)
    a = aliased(VAlimento)

    results = (db.session.query(a.id, a.nome, r.id.label('id_ricetta'), r.nome_ricetta, ir.qta)
               .join(a, and_(a.id == ir.id_alimento))
               .join(r, and_(r.id == ir.id_ricetta))
               .filter(func.coalesce(ir.user_id, user_id) == user_id)
               .filter(ir.id_ricetta == recipe_id)
               .filter(ir.removed == False).all())

    r = []
    for res in results:
        r.append({
            "id": res.id,
            "nome": res.nome,
            "nome_ricetta": res.nome_ricetta,
            "qta": res.qta,
            "id_ricetta": res.id_ricetta
        })

    return r


def elimina_ingredienti(ingredient_id: int, recipe_id: int, user_id: int):
    ingredienti_ricetta = (IngredientiRicetta.query.filter(IngredientiRicetta.id_ricetta_base == recipe_id,
                                                           IngredientiRicetta.id_alimento_base == ingredient_id,
                                                           IngredientiRicetta.user_id == user_id)).first()

    if not ingredienti_ricetta:
        ingredienti_ricetta = IngredientiRicetta(
            id_alimento_base=ingredient_id,
            id_ricetta_base=recipe_id,
            user_id=user_id,
            removed=True
        )
    else:
        ingredienti_ricetta.id_alimento_base = ingredient_id
        ingredienti_ricetta.id_ricetta_base = recipe_id
        ingredienti_ricetta.user_id = user_id
        ingredienti_ricetta.removed = True

    db.session.add(ingredienti_ricetta)
    db.session.commit()


def salva_utente_dieta(id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                       meta_basale, meta_giornaliero, calorie_giornaliere, settimane_dieta, carboidrati,
                       proteine, grassi, dieta):

    utente = Utente.query.filter_by(id=id).first()

    utente.nome = nome
    utente.cognome = cognome
    utente.sesso = sesso
    utente.eta = eta
    utente.peso = peso
    utente.altezza = altezza
    utente.tdee = tdee
    utente.deficit_calorico = deficit_calorico
    utente.bmi = bmi
    utente.peso_ideale = peso_ideale
    utente.meta_basale = meta_basale
    utente.meta_giornaliero = meta_giornaliero
    utente.calorie_giornaliere = calorie_giornaliere
    utente.settimane_dieta = settimane_dieta
    utente.carboidrati = carboidrati
    utente.proteine = proteine
    utente.grassi = grassi
    utente.dieta = dieta

    db.session.add(utente)

    # cancello tutti i record che hanno il peso ideale valorizzato e peso/vita/fianchi null
    db.session.query(RegistroPeso).filter(
        RegistroPeso.user_id == id,
        RegistroPeso.peso_ideale.isnot(None),
        RegistroPeso.peso.is_(None),
        RegistroPeso.vita.is_(None),
        RegistroPeso.fianchi.is_(None),
    ).delete()

    # calcolo la data di fine dieta
    match = re.match(r"^(.*?)\s*\(", settimane_dieta)
    oggi = datetime.now()
    giorni_indietro = (oggi.weekday() - 0) % 7
    lunedi_corrente = oggi - timedelta(days=giorni_indietro)
    settimane = int(match.group(1))
    data_fine_dieta = lunedi_corrente + (timedelta(days=7*int(match.group(1))))

    # calcolo la differenza di peso per ogni settimana
    peso_iniziale = utente.peso  # o il peso registrato più recentemente
    perdita_peso_totale = peso_iniziale - peso_ideale
    perdita_peso_settimanale = perdita_peso_totale / settimane

    for settimana in range(0, settimane):
        data_intermedia = lunedi_corrente + timedelta(days=7 * settimana)
        peso_ideale_intermedio = peso_iniziale - perdita_peso_settimanale * settimana
        registro_intermedio = RegistroPeso.query.filter_by(user_id=id, data_rilevazione=data_intermedia.date()).first()
        if not registro_intermedio:
            # Inserisci il punto intermedio nel database
            registro_intermedio = RegistroPeso(
                user_id=id,
                data_rilevazione=data_intermedia.date(),
                peso=peso_iniziale if settimana == 0 else None,
                peso_ideale=round(peso_ideale_intermedio, 1)
            )
            db.session.add(registro_intermedio)
        else:
            registro_intermedio.peso = peso_iniziale if settimana == 0 else None
            registro_intermedio.peso_ideale = round(peso_ideale_intermedio, 1)


    # cerco se esiste già un record con la data di fine dieta
    new_peso = RegistroPeso.query.filter_by(user_id=id, data_rilevazione=data_fine_dieta).first()

    # se c'è aggiorno solo il peso ideale
    if new_peso:
        new_peso.peso_ideale = peso_ideale
    else:
        # altrimento creo la riga
        new_peso = RegistroPeso(
            user_id=id,
            data_rilevazione=data_fine_dieta,
            peso_ideale=peso_ideale
        )
        db.session.add(new_peso)

    db.session.commit()


def salva_nuova_ricetta(name, breakfast, snack, main, side, second_breakfast, complemento, user_id):

    ricetta = Ricetta(
        id=get_sequence_value('dieta.seq_id_ricetta'),
        nome_ricetta_override=name.upper(),
        colazione_override=breakfast,
        spuntino_override=snack,
        principale_override=main,
        contorno_override=side,
        colazione_sec_override=second_breakfast,
        complemento_override=complemento,
        enabled=True,
        user_id=user_id
    )

    db.session.add(ricetta)
    db.session.commit()

def salva_ingredienti(recipe_id, ingredient_id, quantity, user_id):

    ingredienti_ricetta = (IngredientiRicetta.query.filter(IngredientiRicetta.id_ricetta_base == recipe_id,
                                                                 IngredientiRicetta.id_alimento_base == ingredient_id,
                                                                 IngredientiRicetta.user_id == user_id)).first()

    if not ingredienti_ricetta:
        ingredienti_ricetta = IngredientiRicetta(
            id_alimento_base=ingredient_id,
            id_ricetta_base=recipe_id,
            user_id=user_id,
            qta_override=quantity,
            removed=False
        )
    else:
        ingredienti_ricetta.id_alimento_base = ingredient_id
        ingredienti_ricetta.id_ricetta_base = recipe_id
        ingredienti_ricetta.user_id = user_id
        ingredienti_ricetta.qta_override = quantity
        ingredienti_ricetta.removed = False


    db.session.add(ingredienti_ricetta)
    db.session.commit()


def get_dati_utente(user_id):
    results = Utente.query.filter_by(id=user_id).first()
    return results.to_dict()


def calcola_macronutrienti_rimanenti(menu: json):
    remaining_macronutrienti = {}
    if menu:
        for giorno, dati_giorno in menu['day'].items():
            remaining_kcal = round(dati_giorno['kcal'],2)
            remaining_carboidrati = round(dati_giorno['carboidrati'],2)
            remaining_proteine = round(dati_giorno['proteine'],2)
            remaining_grassi = round(dati_giorno['grassi'],2)

            remaining_macronutrienti[giorno] = {
                'kcal': remaining_kcal,
                'carboidrati': remaining_carboidrati,
                'proteine': remaining_proteine,
                'grassi': remaining_grassi
            }
    return remaining_macronutrienti


def carica_alimenti(user_id):
    results = (db.session.query(
        VAlimento.id,
        VAlimento.nome,
        VAlimento.carboidrati,
        VAlimento.proteine,
        VAlimento.grassi,
        VAlimento.fibre,
        VAlimento.kcal,
        VAlimento.vegan,
        VAlimento.confezionato,
        GruppoAlimentare.nome.label("gruppo")
    )
    .join(GruppoAlimentare, VAlimento.id_gruppo == GruppoAlimentare.id, isouter=True)
    .filter(func.coalesce(VAlimento.user_id, user_id) == user_id)
    .order_by(VAlimento.nome)
    ).all()

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
        'gruppo': r.gruppo or "N/A"
    } for r in results]
    return alimenti


def update_alimento(id, nome, carboidrati, proteine, grassi, fibre, confezionato, vegan, id_gruppo, user_id):
    alimento_base = (VAlimento.query.filter(VAlimento.id==id, func.coalesce(VAlimento.user_id, user_id)==user_id)).first()
    alimento = Alimento.query.filter_by(id=alimento_base.id, user_id=user_id).first()
    if not alimento:
        alimento = Alimento(
            id=id,
            id_alimento_base=id,
            nome_override=nome.upper(),
            carboidrati_override=carboidrati,
            proteine_override=proteine,
            grassi_override=grassi,
            fibre_override=fibre,
            confezionato_override=confezionato,
            vegan_override=vegan,
            id_gruppo_override = alimento_base.id_gruppo,
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


def elimina_alimento(alimento_id, user_id):
    Alimento.query.filter_by(id=alimento_id, user_id=user_id).delete()
    db.session.commit()


def get_sequence_value(seq_name):

    # Creare una query per ottenere il valore successivo dalla sequenza
    nextval_query = select(func.nextval(seq_name))

    # Eseguire la query con il metodo session.execute()
    result = db.session.execute(nextval_query)

    # Estrarre il valore dal risultato
    nextval = result.scalar()

    return nextval


def salva_nuovo_alimento(name, carboidrati, proteine, grassi, fibre, confezionato, vegan, gruppo, user_id):

    alimento = Alimento(
        id=get_sequence_value('dieta.seq_id_alimento'),
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
    db.session.commit()

    alimento_id = alimento.id

    if confezionato:
        ricetta_id = get_sequence_value('dieta.seq_id_ricetta')
        ricetta = Ricetta(
            id=ricetta_id,
            nome_ricetta=name.upper(),
            user_id=user_id
        )

        db.session.add(ricetta)
        db.session.commit()

        ingredienti_ricetta = IngredientiRicetta(
            id_ricetta=ricetta_id,
            id_alimento=alimento_id,
            qta=100,
            user_id=user_id
        )

        db.session.add(ingredienti_ricetta)
        db.session.commit()


def aggiungi_ricetta_al_menu(menu, day, meal, meal_id, user_id):
    ricetta = carica_ricette(user_id, ids=meal_id)
    ricetta[0]['qta'] = 1
    menu['all_food'].append(ricetta[0]['id'])
    menu['day'][day]['pasto'][meal]['ids'].append(ricetta[0]['id'])
    menu['day'][day]['pasto'][meal]['ricette'].append({
        'id': ricetta[0]['id'],
        'nome_ricetta': ricetta[0]['nome_ricetta'],
        'qta': ricetta[0]['qta'],
        'ricetta': ricetta[0]['ricetta'],
        'kcal':ricetta[0]['kcal'],
        'carboidrati': ricetta[0]['carboidrati'],
        'grassi': ricetta[0]['grassi'],
        'proteine': ricetta[0]['proteine']
    })
    aggiorna_macronutrienti(menu, day, ricetta[0])


def update_menu_corrente(menu, week_id, user_id):
    menu_settimanale = MenuSettimanale.query.filter_by(id=week_id, user_id=user_id).first()
    menu_settimanale.menu = menu
    db.session.commit()


def rimuovi_pasto_dal_menu(menu, day, meal, meal_id):
    # Trova la ricetta da rimuovere
    ricetta_da_rimuovere = None
    for ricetta in menu['day'][day]['pasto'][meal]['ricette']:
        if int(ricetta['id']) == int(meal_id):
            ricetta_da_rimuovere = ricetta

    if ricetta_da_rimuovere:
        menu['all_food'].remove(ricetta_da_rimuovere['id'])
        menu['day'][day]['pasto'][meal]['ids'].remove(ricetta_da_rimuovere['id'])
        menu['day'][day]['pasto'][meal]['ricette'].remove(ricetta_da_rimuovere)
        aggiorna_macronutrienti(menu, day, ricetta_da_rimuovere, True)


def cancella_tutti_pasti_menu(settimana, day, meal_type):
    for ricetta in settimana['day'][day]['pasto'][meal_type]["ricette"]:
        settimana['all_food'].remove(ricetta['id'])
        aggiorna_macronutrienti(settimana, day, ricetta, True)

    settimana['day'][day]['pasto'][meal_type] = {"ids": [], "ricette": []}


def aggiorna_macronutrienti(menu, day, ricetta, rimuovi=False):
    moltiplicatore = 1 if rimuovi else -1
    for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
        menu['day'][day][macro] += moltiplicatore * ricetta[macro] * ricetta['qta']
        menu['weekly'][macro] += moltiplicatore * ricetta[macro] * ricetta['qta']

def delete_week_menu(week_id, user_id):
    MenuSettimanale.query.filter_by(id=week_id, user_id=user_id).delete()
    db.session.commit()


def is_valid_email(email):
    # Definizione dell'espressione regolare per validare l'email
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

    # Utilizzo di re.match per verificare se l'email è valida
    if re.match(email_regex, email):
        return True
    else:
        return False


def copia_alimenti_ricette(user_id: int, ricette_vegane: bool, ricette_carne: bool, ricette_pesce: bool):
    # 1. Copia dati dalla tabella alimento_base a alimento
    subquery_alimento = db.session.query(
        AlimentoBase.id,
        AlimentoBase.nome,
        AlimentoBase.carboidrati,
        AlimentoBase.proteine,
        AlimentoBase.grassi,
        AlimentoBase.frutta,
        AlimentoBase.carne_bianca,
        AlimentoBase.carne_rossa,
        AlimentoBase.stagionalita,
        AlimentoBase.verdura,
        AlimentoBase.confezionato,
        AlimentoBase.vegan,
        AlimentoBase.pesce,
        user_id
    ).distinct()

    db.session.execute(
        insert(Alimento).from_select(
            [
                Alimento.id,
                Alimento.nome,
                Alimento.carboidrati,
                Alimento.proteine,
                Alimento.grassi,
                Alimento.frutta,
                Alimento.carne_bianca,
                Alimento.carne_rossa,
                Alimento.stagionalita,
                Alimento.verdura,
                Alimento.confezionato,
                Alimento.vegan,
                Alimento.pesce,
                Alimento.user_id
            ],
            subquery_alimento
        )
    )

    # 2. Copia dati dalla tabella ricetta_base a ricetta
    subquery_ricetta = db.session.query(
        RicettaBase.id,
        RicettaBase.nome_ricetta,
        RicettaBase.colazione,
        RicettaBase.spuntino,
        RicettaBase.principale,
        RicettaBase.contorno,
        false(),  # Set enabled to False
        RicettaBase.colazione_sec,
        RicettaBase.complemento,
        user_id
    )

    db.session.execute(
        insert(Ricetta).from_select(
            [
                Ricetta.id,
                Ricetta.nome_ricetta,
                Ricetta.colazione,
                Ricetta.spuntino,
                Ricetta.principale,
                Ricetta.contorno,
                Ricetta.enabled,
                Ricetta.colazione_sec,
                Ricetta.complemento,
                Ricetta.user_id
            ],
            subquery_ricetta
        )
    )

    # 3. Copia dati dalla tabella ingredienti_ricetta_base a ingredienti_ricetta
    subquery_ingredienti = db.session.query(
        IngredientiRicettaBase.id_ricetta,
        IngredientiRicettaBase.id_alimento,
        IngredientiRicettaBase.qta,
        user_id
    )

    db.session.execute(
        insert(IngredientiRicetta).from_select(
            [
                IngredientiRicetta.id_ricetta,
                IngredientiRicetta.id_alimento,
                IngredientiRicetta.qta,
                IngredientiRicetta.user_id
            ],
            subquery_ingredienti
        )
    )

    # 4. Logica per l'abilitazione delle ricette vegane, con carne, o con pesce
    if ricette_vegane:
        subquery_ricette_vegane = db.session.query(
            RicettaBase.id
        ).join(
            IngredientiRicettaBase, RicettaBase.id == IngredientiRicettaBase.id_ricetta
        ).join(
            AlimentoBase, IngredientiRicettaBase.id_alimento == AlimentoBase.id
        ).group_by(
            RicettaBase.id, RicettaBase.nome_ricetta
        ).having(
            func.count() == func.sum(
                case(
                    (AlimentoBase.vegan == true(), 1),
                    else_=0
                )
            )
        ).subquery()

        db.session.execute(
            update(Ricetta).where(
                and_(Ricetta.id.in_(subquery_ricette_vegane), Ricetta.user_id == user_id)
            ).values(enabled=True)
        )
    else:
        if ricette_carne and ricette_pesce:
            db.session.execute(
                update(Ricetta).where(
                    Ricetta.user_id == user_id
                ).values(enabled=True)
            )
        elif ricette_carne and not ricette_pesce:
            subquery_no_pesce = db.session.query(
                RicettaBase.id
            ).filter(~exists().where(
                and_(
                    IngredientiRicettaBase.id_ricetta == RicettaBase.id,
                    AlimentoBase.id == IngredientiRicettaBase.id_alimento,
                    AlimentoBase.pesce == True
                )
            )).subquery()

            db.session.execute(
                update(Ricetta).where(
                    and_(Ricetta.id.in_(subquery_no_pesce), Ricetta.user_id == user_id)
                ).values(enabled=True)
            )
        elif not ricette_carne and ricette_pesce:
            subquery_no_carne = db.session.query(
                RicettaBase.id
            ).filter(~exists().where(
                and_(
                    IngredientiRicettaBase.id_ricetta == RicettaBase.id,
                    AlimentoBase.id == IngredientiRicettaBase.id_alimento,
                    (AlimentoBase.carne_bianca == True) | (AlimentoBase.carne_rossa == True)
                )
            )).subquery()

            db.session.execute(
                update(Ricetta).where(
                    and_(Ricetta.id.in_(subquery_no_carne), Ricetta.user_id == user_id)
                ).values(enabled=True)
            )

    db.session.commit()


def recupera_ricette_per_alimento(alimento_id, user_id):
    ir = aliased(VIngredientiRicetta)
    r = aliased(VRicetta)

    ricette = (db.session.query(r.nome_ricetta)
               .select_from(ir)
               .join(r, and_(r.id == ir.id_ricetta))
               .filter(func.coalesce(ir.user_id, user_id) == user_id)
               .filter(ir.id_alimento == alimento_id)
               .filter(ir.removed == False).all())

    ricette_data = [{'nome_ricetta': r.nome_ricetta} for r in ricette]
    return ricette_data


def copia_menu(menu_from, week_to, user_id):
    menu_destinazione = MenuSettimanale.query.filter_by(user_id=user_id, id=week_to).one()

    if menu_destinazione:
        menu_destinazione.menu = menu_from

    db.session.commit()


def recupera_settimane(user_id):
    weeks = get_settimane_salvate(user_id, show_old_week=True)
    return [
        {'id': week.id, 'name': f"Settimana {index + 1} dal {week.data_inizio.strftime('%Y-%m-%d')} al {week.data_fine.strftime('%Y-%m-%d')}"}
        for index, week in enumerate(weeks)
    ]

def get_gruppi_data():
    gruppi = GruppoAlimentare.query.all()
    gruppi_data = [{'id': g.id, 'nome': g.nome} for g in gruppi]
    return gruppi_data