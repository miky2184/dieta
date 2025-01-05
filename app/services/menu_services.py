#app/services/menu_services.py
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
from sqlalchemy import insert, update, and_, or_, case, func, exists, asc, String, true, false, select, desc
from collections import defaultdict
from decimal import Decimal
from app.services.util_services import printer
from app.services.common_db_service import get_sequence_value
from app.services.ricette_services import get_ricette_service

MAX_RETRY = int(os.getenv('MAX_RETRY'))

LIMITI_CONSUMO = {
    '1': 240,   # Uova (2-4 a settimana)
    '2': 0,     # Pesce (2-3 porzioni settimanali)
    '4': 150,   # Carne Rossa (1 porzione settimanale)
    '3': 350,   # Carne Bianca (1-2 porzioni settimanali)
    '5': 800,   # Legumi (2-4 porzioni settimanali)
    '8': 800,   # Cereali (100-120 g al giorno)
    '12': 150,  # Frutta secca (20-30 g al giorno)
    '15': 150   # Olio o grassi da condimento (20-30 g al giorno)
}

pasti_config = [
    {'pasto': 'colazione', 'tipo': 'colazione', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'colazione', 'tipo': 'colazione_sec', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'spuntino_mattina', 'tipo': 'spuntino', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'spuntino_pomeriggio', 'tipo': 'spuntino', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'spuntino_sera', 'tipo': 'spuntino', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'pranzo', 'tipo': 'principale', 'ripetibile': False, 'min_ricette': 2},
    {'pasto': 'cena', 'tipo': 'principale', 'ripetibile': False, 'min_ricette': 1},
    {'pasto': 'pranzo', 'tipo': 'contorno', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'cena', 'tipo': 'contorno', 'ripetibile': True, 'min_ricette': 1},
]

def genera_menu_utente(user_id, cache) -> dict:
    """
    Genera il menu settimanale per l'utente. Include la settimana corrente, successiva
    e una nuova settimana successiva all'ultima presente, se necessario.

    Args:
        user_id (int): ID dell'utente.
        cache (Cache): Istanza della cache per gestire i dati temporanei.

    Returns:
        dict: Stato dell'operazione e progressione completata.
    """
    macronutrienti = get_utente(user_id)
    if not macronutrienti.calorie_giornaliere:
        raise ValueError('Macronutrienti non definiti!')

    # Trova l'ultima settimana presente nel database
    with db.session() as session:
        ultima_settimana = session.query(MenuSettimanale).filter_by(user_id=user_id).order_by(
            desc(MenuSettimanale.data_fine)).first()

    periodi = []
    oggi = datetime.now().date()
    giorni_indietro = (oggi.weekday() - 0) % 7
    lunedi_corrente = oggi - timedelta(days=giorni_indietro)
    domenica_corrente = lunedi_corrente + timedelta(days=6)

    if ultima_settimana:
        nuova_settimana_inizio = ultima_settimana.data_fine + timedelta(days=1)
        nuova_settimana_fine = nuova_settimana_inizio + timedelta(days=6)
        periodi.append({"data_inizio": nuova_settimana_inizio, "data_fine": nuova_settimana_fine})
    else:
        lunedi_prossimo = lunedi_corrente + timedelta(days=7)
        domenica_prossima = lunedi_prossimo + timedelta(days=6)
        periodi.extend([
            {"data_inizio": lunedi_corrente, "data_fine": domenica_corrente},
            {"data_inizio": lunedi_prossimo, "data_fine": domenica_prossima}
        ])

    # Genera menu per i periodi definiti
    for period in periodi:
        genera_e_salva_menu(user_id, period, macronutrienti)

    # Invalida la cache
    cache.delete(f'dashboard_{user_id}')
    return {'status': 'success', 'progress': 100}


def genera_e_salva_menu(user_id, period, macronutrienti):
    """
    Genera e salva il menu per un periodo specifico, se non già esistente.

    Args:
        user_id (int): ID dell'utente.
        period (dict): Periodo con data_inizio e data_fine.
        macronutrienti (dict): Dati sui macronutrienti dell'utente.

    Returns:
        None
    """
    ricette_menu = get_ricette_service(user_id, stagionalita=True, data_stagionalita=period["data_fine"])
    if not get_menu(user_id, period=period):
        settimana = deepcopy(get_settimana(macronutrienti))
        genera_menu(settimana, False, ricette_menu, user_id)

        # Ordina la settimana per kcal rimanenti
        settimana_ordinata = ordina_settimana_per_kcal(settimana)
        genera_menu(settimana_ordinata, True, ricette_menu, user_id)
        salva_menu(settimana_ordinata, user_id, period=period)

def verifica_e_seleziona(settimana, giorno, pasto, tipo, ripetibile, min_ricette, controllo_macro, ricette, user_id):
    """
    Verifica se un pasto specifico ha il numero minimo di ricette richiesto e, se necessario, ne aggiunge altre.

    Args:
        settimana (dict): La struttura del menu settimanale.
        giorno (str): Il giorno della settimana in cui verificare/aggiungere ricette.
        pasto (str): Il tipo di pasto (es. 'colazione', 'pranzo').
        tipo (str): La categoria del pasto (es. 'colazione', 'spuntino', 'principale').
        ripetibile (bool): Indica se le ricette possono essere ripetute nei pasti.
        min_ricette (int): Numero minimo di ricette richiesto per il pasto.
        controllo_macro (bool): Indica se controllare i macronutrienti durante la selezione.
        ricette (list): Lista delle ricette disponibili.
        user_id (int): ID dell'utente.

    Returns:
        None
    """
    p = settimana['day'][giorno]['pasto']
    if numero_ricette(p, pasto, tipo, ricette) < min_ricette:
        for _ in range(min_ricette - numero_ricette(p, pasto, tipo, ricette)):
            scegli_pietanza(settimana, giorno, pasto, tipo, ripetibile, controllo_macro, ricette, user_id)


def genera_menu(settimana, controllo_macro_settimanale, ricette, user_id) -> None:
    """
    Genera un menu settimanale distribuendo ricette su pasti giornalieri.

    Args:
        settimana (dict): La struttura del menu settimanale.
        controllo_macro_settimanale (bool): Indica se controllare i macronutrienti settimanali.
        ricette (list): Lista delle ricette disponibili.
        user_id (int): ID dell'utente.

    Returns:
        None
    """

    for giorno in settimana['day']:
        for config in pasti_config:
            verifica_e_seleziona(settimana, giorno, config['pasto'], config['tipo'], config['ripetibile'], config['min_ricette'], controllo_macro_settimanale, ricette, user_id)


def scegli_pietanza(settimana, giorno_settimana: str, pasto: str, tipo: str, ripetibile: bool,
                    controllo_macro_settimanale: bool, ricette, user_id, ids_specifici=None, skip_check=False) -> bool:
    """
    Seleziona una pietanza dalla lista di ricette pre-caricate in memoria e la aggiunge al pasto corrispondente.

    Args:
        settimana (dict): La struttura del menu settimanale.
        giorno_settimana (str): Il giorno della settimana in cui aggiungere la pietanza.
        pasto (str): Il tipo di pasto (es. 'colazione', 'pranzo').
        tipo (str): La categoria del pasto (es. 'colazione', 'spuntino', 'principale').
        ripetibile (bool): Indica se la pietanza può essere ripetuta nei pasti.
        controllo_macro_settimanale (bool): Indica se controllare i macronutrienti settimanali durante la selezione.
        ricette (list): Lista delle ricette disponibili. Ogni ricetta è un dizionario con informazioni nutrizionali.
        user_id (int): ID dell'utente per il quale il menu viene generato.
        ids_specifici (list, opzionale): Lista di ID di ricette specifiche da considerare. Default è None.
        skip_check (bool, opzionale): Se True, ignora i controlli nutrizionali e di limiti durante la selezione. Default è False.

    Returns:
        bool: True se è stata selezionata una pietanza, False altrimenti.
    """

    ricette_filtrate = [r for r in ricette if r[tipo] and r['attiva']]

    if not ricette_filtrate:
        printer(f"Nessuna ricetta trovata per {giorno_settimana}, pasto: {pasto}, tipo: {tipo}", "WARNING")

    # Prepara le ricette modificate
    ricette_modificate = [
        {k: r[k] for k in ['id', 'nome_ricetta', 'kcal', 'carboidrati', 'proteine', 'grassi',
                           'colazione', 'spuntino', 'principale', 'contorno', 'ricetta', 'ingredienti']}
        for r in ricette_filtrate
    ]

    # Chiama select_food per selezionare la pietanza
    return select_food(ricette_modificate, settimana, giorno_settimana, pasto, ripetibile, controllo_macro_settimanale, skip_check, user_id, ids_specifici)


def select_food(ricette, settimana, giorno_settimana, pasto, ripetibile, controllo_macro_settimanale, skip_check, user_id, ids_specifici=None) -> bool:
    """
    Seleziona una ricetta ottimale in base ai criteri nutrizionali, ai limiti settimanali e alle preferenze dell'utente.

    Args:
        ricette (list): Lista delle ricette disponibili. Ogni ricetta è rappresentata come un dizionario contenente informazioni nutrizionali, ingredienti e altro.
        settimana (dict): Struttura contenente informazioni sul menu settimanale, inclusi i giorni, i pasti e i consumi.
        giorno_settimana (str): Il giorno della settimana in cui aggiungere la ricetta (es. 'lunedi', 'martedi').
        pasto (str): Il tipo di pasto (es. 'colazione', 'pranzo', 'cena').
        ripetibile (bool): Indica se la stessa ricetta può essere ripetuta durante i pasti.
        controllo_macro_settimanale (bool): Indica se controllare i macronutrienti settimanali durante la selezione.
        skip_check (bool): Se True, salta i controlli nutrizionali e di limiti.
        user_id (int): ID dell'utente per il quale il menu viene generato.
        ids_specifici (list, opzionale): Lista di ID di ricette specifiche da considerare. Default è None.

    Returns:
        bool: True se una ricetta è stata selezionata, False altrimenti.
    """

    found = False
    # Determina gli ID disponibili
    ids_disponibili = determina_ids_disponibili(ricette, settimana, giorno_settimana, pasto, ripetibile, ids_specifici)

    # Filtra le ricette in base agli ID disponibili e ai criteri nutrizionali
    ricette_filtrate = [
        ricetta for ricetta in ricette
        if ricetta['id'] in ids_disponibili
           and (skip_check or controlla_limiti_macronutrienti(ricetta, settimana['day'][giorno_settimana], settimana['weekly'],
                                                              controllo_macro_settimanale))
           and check_limiti_consumo_ricetta(ricetta, settimana['consumi'])
    ]

    if not ricette_filtrate:
        printer(f"Nessuna ricetta valida trovata per giorno: {giorno_settimana}, pasto: {pasto}")
        return found

    random.shuffle(ricette_filtrate)

    for ricetta in ricette_filtrate:
        percentuale_effettiva = calcola_percentuale_effettiva(ricetta, settimana['day'][giorno_settimana])
        if percentuale_effettiva >= 0.5:
            aggiorna_settimana(settimana, giorno_settimana, pasto, ricetta, percentuale_effettiva, user_id)
            found = True
            break

    return found


def calcola_percentuale_effettiva(ricetta, day) -> float:
    """
    Calcola la percentuale massima utilizzabile di una ricetta,
    rispettando i limiti giornalieri dei macronutrienti e delle calorie.

    Args:
        ricetta (dict): Dizionario contenente valori di macronutrienti e calorie della ricetta.
        day (dict): Dizionario contenente valori rimanenti di macronutrienti e calorie per il giorno.

    Returns:
        float: Percentuale massima utilizzabile, compresa tra 0.5 e 1.0. Restituisce 0 se non calcolabile.
    """
    try:
        # Calcola le percentuali possibili per ciascun macronutriente
        percentuali_possibili = [
            day[macro] / ricetta[macro]
            for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']
            if ricetta.get(macro, 0) > 0
        ]

        # Se nessuna percentuale è calcolabile, restituisci 0
        if not percentuali_possibili:
            return 0

        # Restituisci la percentuale effettiva limitata al range [0.5, 1.0]
        return max(0.5, min(1.0, min(percentuali_possibili)))

    except KeyError as e:
        raise ValueError(f"Chiave mancante nei dati: {e}")
    except Exception as e:
        raise RuntimeError(f"Errore durante il calcolo della percentuale: {str(e)}")


def aggiorna_settimana(settimana, giorno_settimana, pasto, ricetta, percentuale, user_id) -> None:
    """
        Aggiorna la struttura del menu settimanale aggiungendo una ricetta al giorno e al pasto specificati.
        Regola i macronutrienti e i consumi settimanali in base alla percentuale della ricetta utilizzata.

        Args:
            settimana (dict): Struttura del menu settimanale.
            giorno_settimana (str): Giorno della settimana (es. "lunedi").
            pasto (str): Nome del pasto (es. "colazione").
            ricetta (dict): Informazioni sulla ricetta selezionata.
            percentuale (float): Percentuale di utilizzo della ricetta.
            user_id (int): ID dell'utente.

        Returns:
            None
        """
    # Validazione preliminare
    if giorno_settimana not in settimana['day']:
        raise KeyError(f"Giorno '{giorno_settimana}' non trovato nella struttura settimanale.")
    if pasto not in settimana['day'][giorno_settimana]['pasto']:
        raise KeyError(f"Pasto '{pasto}' non trovato nel giorno '{giorno_settimana}'.")

    # Ottenere riferimenti al giorno e alla settimana
    mt = settimana['day'][giorno_settimana]['pasto'][pasto]
    day = settimana['day'][giorno_settimana]
    weekly = settimana['weekly']

    # Aggiungi l'ID della ricetta a 'all_food'
    settimana['all_food'].append(ricetta['id'])

    # Aggiungi la ricetta al menu del pasto
    mt['ids'].append(ricetta['id'])
    mt['ricette'].append({
        'qta': percentuale,
        'id': ricetta['id'],
        'nome_ricetta': ricetta['nome_ricetta'],
        'ricetta': recupera_ingredienti_ricetta(ricetta['id'], user_id, percentuale),
        'kcal': ricetta['kcal'],
        'carboidrati': ricetta['carboidrati'],
        'proteine': ricetta['proteine'],
        'grassi': ricetta['grassi']
    })

    # Aggiorna i macronutrienti giornalieri e settimanali
    for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
        day[macro] -= round(ricetta[macro] * percentuale, 2)
        weekly[macro] -= round(ricetta[macro] * percentuale, 2)

    # Aggiorna i consumi settimanali per i gruppi alimentari
    aggiorna_limiti_gruppi(ricetta, settimana['consumi'])

def determina_ids_disponibili(ricette, settimana, giorno_settimana, pasto, ripetibile, ids_specifici) -> list:
    """
    Determina gli ID delle ricette disponibili in base ai criteri forniti.

    Args:
        ricette (list): Lista di ricette disponibili, ciascuna con almeno una chiave `'id'`.
        settimana (dict): Struttura del menu settimanale.
        giorno_settimana (str): Giorno della settimana (es. "lunedi").
        pasto (str): Nome del pasto (es. "colazione").
        ripetibile (bool): Se True, consente di ripetere ricette nello stesso pasto.
        ids_specifici (list o None): Lista opzionale di ID ricette da considerare.

    Returns:
        list: Lista di ID ricette disponibili.

    Raises:
        KeyError: Se `giorno_settimana` o `pasto` non sono presenti nella struttura `settimana`.
        ValueError: Se la lista `ricette` è vuota o non valida.
    """
    try:
        if not ricette:
            raise ValueError("La lista delle ricette è vuota o non valida.")

        # Controlla che le chiavi esistano
        if giorno_settimana not in settimana['day']:
            raise KeyError(f"Giorno '{giorno_settimana}' non trovato in 'settimana'.")
        if pasto not in settimana['day'][giorno_settimana]['pasto']:
            raise KeyError(f"Pasto '{pasto}' non trovato nel giorno '{giorno_settimana}'.")

        if ids_specifici:
            return [
                r['id'] for r in ricette
                if r['id'] in ids_specifici and r['id'] not in settimana['all_food']
            ]
        if ripetibile:
            return [
                r['id'] for r in ricette
                if r['id'] not in settimana['day'][giorno_settimana]['pasto'][pasto]['ids']
            ]
        return [
            r['id'] for r in ricette
            if r['id'] not in settimana['all_food']
        ]
    except KeyError as e:
        raise KeyError(f"Errore nella struttura 'settimana': {e}")
    except Exception as e:
        raise RuntimeError(f"Errore durante la determinazione degli ID disponibili: {str(e)}")


def check_limiti_consumo_ricetta(ricetta, consumi) -> bool:
    """
    Verifica se una ricetta rispetta i limiti di consumo settimanale.

    Args:
        ricetta (dict): Ricetta contenente una lista di ingredienti con quantità totali e ID di gruppo.
        consumi (dict): Dizionario dei limiti di consumo rimanenti per ogni gruppo alimentare.

    Returns:
        bool: True se la ricetta rispetta i limiti, False altrimenti.

    Raises:
        KeyError: Se 'ingredienti' manca in 'ricetta'.
        ValueError: Se i dati in 'ricetta' o 'consumi' non sono validi.
    """
    if 'ingredienti' not in ricetta:
        raise KeyError("La chiave 'ingredienti' è mancante nella ricetta.")
    if not isinstance(consumi, dict):
        raise ValueError("Il parametro 'consumi' deve essere un dizionario.")

    try:
        for gruppo in ricetta['ingredienti']:
            id_gruppo = str(gruppo.get('id_gruppo'))
            qta = gruppo.get('qta_totale', 0)

            if id_gruppo in consumi and qta > consumi[id_gruppo]:
                return False  # Supera il limite
        return True
    except Exception as e:
        raise RuntimeError(f"Errore durante il controllo dei limiti di consumo: {str(e)}")


def aggiorna_limiti_gruppi(ricetta, consumi, rimuovi: bool = False):
    """
    Aggiorna i consumi rimanenti per i gruppi alimentari in base agli ingredienti di una ricetta.

    Args:
        ricetta (dict): Ricetta contenente una lista di ingredienti con quantità totali e ID di gruppo.
        consumi (dict): Dizionario dei consumi rimanenti per ciascun gruppo alimentare.
        rimuovi (bool, opzionale): Indica se aggiungere (`True`) o sottrarre (`False`) le quantità.

    Raises:
        KeyError: Se la chiave 'ingredienti' manca nella ricetta.
        ValueError: Se i dati nella ricetta o in consumi non sono validi.
    """
    if 'ingredienti' not in ricetta:
        raise KeyError("La chiave 'ingredienti' è mancante nella ricetta.")
    if not isinstance(consumi, dict):
        raise ValueError("Il parametro 'consumi' deve essere un dizionario.")

    moltiplicatore = 1 if rimuovi else -1
    try:
        for gruppo in ricetta['ingredienti']:
            id_gruppo = gruppo.get('id_gruppo')
            qta = gruppo.get('qta_totale', 0)

            if str(id_gruppo) in consumi:
                consumi[str(id_gruppo)] += moltiplicatore * qta
    except Exception as e:
        raise RuntimeError(f"Errore durante l'aggiornamento dei limiti dei gruppi: {str(e)}")


def recupera_ingredienti_ricetta(ricetta_id, user_id, percentuale) -> str:
    """
    Recupera gli ingredienti di una ricetta e calcola le quantità basate su una percentuale specifica.

    Args:
        ricetta_id (int): ID della ricetta di cui recuperare gli ingredienti.
        user_id (int): ID dell'utente che ha creato o ha accesso alla ricetta.
        percentuale (float): Percentuale da applicare alle quantità degli ingredienti.

    Returns:
        str: Una stringa che rappresenta gli ingredienti e le quantità della ricetta, formattata come:
             "Ingrediente1: Quantità1g, Ingrediente2: Quantità2g, ..."
    """
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
        .label('ingredienti')
    )

    query = db.session.query(
        func.coalesce(ricetta_subquery, '').label('ricetta')
    )

    results = query.distinct().all()

    if not results or not results[0].ricetta:
        return "Ingredienti non disponibili"

    return results[0].ricetta


def controlla_limiti_macronutrienti(ricetta, day, weekly, controllo_macro_settimanale) -> bool:
    """
    Verifica se i macronutrienti di una ricetta possono essere aggiunti senza superare i limiti giornalieri o settimanali.

    Args:
        ricetta (dict): Informazioni nutrizionali della ricetta, contenente i valori di calorie, carboidrati, proteine e grassi.
        day (dict): Valori dei macronutrienti rimanenti per il giorno corrente.
        weekly (dict): Valori dei macronutrienti rimanenti per la settimana corrente.
        controllo_macro_settimanale (bool): Se True, verifica anche i limiti settimanali oltre a quelli giornalieri.

    Returns:
        bool: True se la ricetta può essere aggiunta senza superare i limiti, False altrimenti.
    """
    try:
        def sufficienti_macronutrienti(limiti) -> bool:
            return (
                limiti['kcal'] - ricetta['kcal'] > 0 and
                limiti['carboidrati'] - ricetta['carboidrati'] > 0 and
                limiti['proteine'] - ricetta['proteine'] > 0 and
                limiti['grassi'] - ricetta['grassi'] > 0
            )

        return sufficienti_macronutrienti(day) or (
            controllo_macro_settimanale and sufficienti_macronutrienti(weekly)
        )
    except KeyError as e:
        raise ValueError(f"Chiave mancante: {e}")


def ordina_settimana_per_kcal(settimana) -> dict:
    """
    Ordina i giorni della settimana in base alle calorie giornaliere rimanenti in ordine decrescente.

    Args:
        settimana (dict): Struttura settimanale con dati giornalieri, settimanali, e consumi.

    Returns:
        dict: Nuova struttura della settimana con giorni ordinati per calorie rimanenti.

    Raises:
        KeyError: Se un giorno manca della chiave 'kcal'.
        ValueError: Se il valore di 'kcal' non è numerico.
    """
    try:
        giorni_ordinati = sorted(settimana['day'].keys(), key=lambda giorno: settimana['day'][giorno]['kcal'], reverse=True)

        # Crea una nuova struttura della settimana con i giorni ordinati
        settimana_ordinata = {
            'weekly': settimana['weekly'],
            'day': {giorno: settimana['day'][giorno] for giorno in giorni_ordinati},
            'all_food': settimana['all_food'],
            'consumi': settimana['consumi']
        }

        return settimana_ordinata
    except KeyError as e:
        raise KeyError(f"Errore: La chiave 'kcal' è mancante in uno dei giorni ({str(e)}).")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Errore: Il valore di 'kcal' non è numerico. Dettagli: {str(e)}")


def numero_ricette(p, pasto, tipo_ricetta, ricette) -> int:
    """
    Conta il numero di ricette di un certo tipo già presenti in un pasto specifico.

    Args:
        p (dict): Struttura che rappresenta i pasti di un giorno, contenente i dettagli di ciascun pasto.
        pasto (str): Nome del pasto (es. 'colazione', 'pranzo', 'cena').
        tipo_ricetta (str): Tipo di ricetta da cercare (es. 'principale', 'contorno').
        ricette (list): Lista delle ricette disponibili, ogni ricetta è un dizionario con dettagli come id e tipo.

    Returns:
        int: Numero di ricette trovate nel pasto specificato del tipo richiesto.
    """
    if pasto not in p or 'ricette' not in p[pasto]:
        return 0

    tipo_ids = {ricetta['id'] for ricetta in ricette if ricetta.get(tipo_ricetta)}
    return sum(1 for r in p[pasto]['ricette'] if r['id'] in tipo_ids)


def get_utente(user_id) -> Utente:
    """
    Recupera le informazioni di un utente specifico dal database.

    Args:
        user_id (int): L'ID dell'utente da recuperare.

    Returns:
        Utente: Istanza del modello `Utente` contenente i dettagli dell'utente.

    Raises:
        sqlalchemy.orm.exc.NoResultFound: Se non esiste un utente con l'ID specificato.
        sqlalchemy.orm.exc.MultipleResultsFound: Se più utenti con lo stesso ID vengono trovati (scenario improbabile).
    """
    try:
        return Utente.query.filter_by(id=user_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        raise ValueError(f"Utente con ID {user_id} non trovato.")
    except sqlalchemy.orm.exc.MultipleResultsFound:
        raise ValueError(f"Errore: Più utenti trovati con ID {user_id}.")


def stampa_lista_della_spesa(user_id: int, menu: dict) -> list[dict]:
    """
    Genera una lista della spesa basata sul menu settimanale.

    Args:
        user_id (int): ID dell'utente per cui generare la lista della spesa.
        menu (dict): Struttura del menu settimanale contenente giorni, pasti e ricette.

    Returns:
        list[dict]: Lista di ingredienti e relative quantità totali necessarie.
    """
    # Verifica del menu
    if not isinstance(menu, dict) or "day" not in menu or "all_food" not in menu:
        raise ValueError("Il menu fornito non è valido.")

    # Alias per le tabelle
    ir = aliased(VIngredientiRicetta)
    a = aliased(VAlimento)
    r = aliased(VRicetta)

    if menu['all_food']:
        results = (
            db.session.query((r.id).label('id_ricetta'),
                             (a.nome).label('nome'),
                             func.sum(ir.qta).label('qta_totale')
                             )
            .join(a, a.id == ir.id_alimento)
            .join(r, r.id == ir.id_ricetta)
            .filter(ir.removed == False)
            .filter(func.coalesce(ir.user_id, user_id) == user_id)
            .filter(ir.id_ricetta.in_(menu['all_food']))
            .group_by(r.id, a.nome )
            .order_by(a.nome)
            .all()
        )
    else:
        results = []  # Gestione nel caso di lista vuota

    # Calcolo delle quantità totali
    ingredient_totals = defaultdict(float)
    ricetta_qta = []
    # Itera sui giorni
    for day, day_data in menu["day"].items():
        # Itera sui pasti del giorno
        for meal_name, meal_data in day_data["pasto"].items():
            # Itera sulle ricette del pasto
            for ricetta in meal_data["ricette"]:
                # Aggiungi la quantità al totale dell'ingrediente
                ingredient_totals[ricetta["id"]] += ricetta["qta"]

    # Stampa le quantità totali per ogni ingrediente
    for ingredient, total in ingredient_totals.items():
        ricetta_qta.append({"id": ingredient, "qta": total})

    # Mappa le quantità per ricetta
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


def salva_menu(menu, user_id, period: dict = None) -> None:
    """
       Salva un nuovo menu settimanale per un utente nel database.

       Args:
           menu (dict): La struttura del menu settimanale da salvare.
           user_id (int): ID dell'utente per il quale salvare il menu.
           period (dict, opzionale): Un dizionario contenente le date di inizio e fine del periodo del menu.
                                      Se non fornito, il periodo viene calcolato automaticamente in base all'ultimo menu salvato.

       Returns:
           None
       """

    if period and ('data_inizio' not in period or 'data_fine' not in period):
        raise ValueError("Il dizionario 'period' deve contenere le chiavi 'data_inizio' e 'data_fine'.")

    if not period:
        period = {}
        last_menu = MenuSettimanale.query.filter_by(user_id=user_id).order_by(desc(MenuSettimanale.data_fine)).first()
        if last_menu:
            period = {
                'data_inizio': last_menu.data_inizio + timedelta(days=7),
                'data_fine': last_menu.data_fine + timedelta(days=7)
            }
        else:
            today = datetime.now().date()
            period = {
                'data_inizio': today,
                'data_fine': today + timedelta(days=6)
            }


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
    """
    Recupera un menu settimanale per un utente specifico.

    Args:
        user_id (int): ID dell'utente per il quale recuperare il menu.
        period (dict, optional): Dizionario contenente le date di inizio e fine della settimana.
                                  Esempio: {"data_inizio": <data>, "data_fine": <data>}.
        ids (int, optional): ID specifico del menu da recuperare. Se specificato, ignora `period`.

    Returns:
        dict: Dizionario contenente il menu e la data di fine,
              con struttura {"menu": <menu>, "data_fine": <data>} se trovato.
        None: Se nessun menu corrispondente è trovato.

    Raises:
        KeyError: Se il parametro `period` è fornito ma non contiene le chiavi `data_inizio` o `data_fine`.
    """
    if period and ('data_inizio' not in period or 'data_fine' not in period):
        raise ValueError("Il parametro 'period' deve contenere 'data_inizio' e 'data_fine'.")

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

    utente = get_utente(user_id)

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

    consumi_settimanali = deepcopy(LIMITI_CONSUMO) # Inizializza i consumi settimanali

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

    utente = get_utente(user_id=id)

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


def aggiungi_ricetta_al_menu(menu, day, meal, meal_id, user_id):
    ricetta = get_ricette_service(user_id, ids=meal_id)
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


def qta_gruppo_ricetta(ricetta_id, user_id):
    vir = aliased(VIngredientiRicetta)
    va = aliased(VAlimento)

    results = (db.session.query(
        (va.id_gruppo).label('id_gruppo'),
        func.sum(vir.qta).label('qta')
    ).join(va, va.id == vir.id_alimento)
               .filter(vir.removed == False)
               .filter(func.coalesce(vir.user_id, user_id) == user_id)
               .filter(vir.id_ricetta == ricetta_id)
               .group_by(va.id_gruppo).all())

    res = [{"ingredienti": []}]

    alimenti = [{
        'id_gruppo': int(r.id_gruppo),
        'qta_totale': float(r.qta)
    } for r in results]

    res[0]['ingredienti'] = alimenti
    return res[0]


def rimuovi_pasto_dal_menu(menu, day, meal, meal_id, user_id):
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
        aggiorna_limiti_gruppi(qta_gruppo_ricetta(ricetta_da_rimuovere['id'], user_id), menu['consumi'], True)

def cancella_tutti_pasti_menu(settimana, day, meal_type, user_id):
    for ricetta in settimana['day'][day]['pasto'][meal_type]['ricette']:
        settimana['all_food'].remove(ricetta['id'])
        aggiorna_macronutrienti(settimana, day, ricetta, True)
        aggiorna_limiti_gruppi(qta_gruppo_ricetta(ricetta['id'], user_id), settimana['consumi'], True)

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