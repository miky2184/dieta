#app/services/menu_services.py
import os
import random
import re
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
import json

from sqlalchemy import and_, func, asc, desc
from sqlalchemy.orm import aliased

from app.models import db
from app.models.IngredientiRicetta import IngredientiRicetta
from app.models.MenuSettimanale import MenuSettimanale
from app.models.PesoIdeale import PesoIdeale
from app.models.RegistroPeso import RegistroPeso
from app.models.Utente import Utente
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from app.services.db_services import get_sequence_value
from app.services.modifica_pasti_services import get_menu_service
from app.services.ricette_services import get_ricette_service
from app.services.util_services import printer, calcola_macronutrienti_rimanenti_service

MAX_RETRY = int(os.getenv('MAX_RETRY'))

LIMITI_CONSUMO = {
    '1':  240,   # Uova
    '3':  600,   # Carne Bianca
    '4':  300,   # Carne Rossa
    '5':  450,   # Legumi
    '8':  600,   # Cereali
    '9':  420,   # Pane
    '12': 160,   # Frutta secca
    '14': 600,   # Patate
    '15': 140    # Olio o grassi da condimento
}

pasti_config = [
    {'pasto': 'pranzo', 'tipo': 'principale', 'complemento': False,'ripetibile': False, 'min_ricette': 1, 'max_percentuale': 1},
    {'pasto': 'cena', 'tipo': 'principale', 'complemento': False,'ripetibile': False, 'min_ricette': 1, 'max_percentuale': 1},
    {'pasto': 'colazione', 'tipo': 'colazione', 'complemento': False,'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1},
    {'pasto': 'colazione', 'tipo': 'colazione_sec', 'complemento': False,'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1},
    {'pasto': 'pranzo', 'tipo': 'contorno', 'complemento': False,'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1.5},
    {'pasto': 'cena', 'tipo': 'contorno', 'complemento': False, 'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1.5},
    {'pasto': 'spuntino_mattina', 'tipo': 'spuntino', 'complemento': False, 'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1.5},
    {'pasto': 'spuntino_pomeriggio', 'tipo': 'spuntino', 'complemento': False, 'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1.5},
    {'pasto': 'spuntino_sera', 'tipo': 'spuntino', 'complemento': False, 'ripetibile': True, 'min_ricette': 1, 'max_percentuale': 1},
    {'pasto': 'pranzo', 'tipo': 'contorno', 'complemento': True, 'ripetibile': True, 'min_ricette': 2, 'max_percentuale': 3},
    {'pasto': 'cena', 'tipo': 'contorno', 'complemento': True, 'ripetibile': True, 'min_ricette': 2, 'max_percentuale': 3},
]

def genera_menu_utente_service(user_id) -> None:
    """
    Genera il menu settimanale per l'utente. Include la settimana corrente, successiva
    e una nuova settimana successiva all'ultima presente, se necessario.

    Args:
        user_id (int): ID dell'utente.

    Returns:
        None
    """
    macronutrienti = Utente.get_by_id(user_id)
    if not macronutrienti.calorie_giornaliere:
        raise ValueError('Macronutrienti non definiti!')

    # Trova l'ultima settimana presente nel database
    query = (db.session.query(MenuSettimanale)
             .filter(MenuSettimanale.user_id==user_id,
                     func.current_date() <= MenuSettimanale.data_fine)
             .order_by(desc(MenuSettimanale.data_fine)))

    ultima_settimana = query.first()

    #print_query(query)

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


def genera_e_salva_menu(user_id, period, macronutrienti: Utente) -> None:
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
    if not get_menu_service(user_id, period=period):
        settimana = deepcopy(get_settimana(macronutrienti))
        genera_menu(settimana, False, ricette_menu, user_id)

        # Ordina la settimana per kcal rimanenti
        #settimana_ordinata = ordina_settimana_per_kcal(settimana)
        genera_menu(settimana, True, ricette_menu, user_id)
        salva_menu_service(settimana, user_id, period=period)


def verifica_e_seleziona(settimana, giorno, pasto, tipo, ripetibile, min_ricette, controllo_macro, ricette, max_percentuale, pane: bool = False) -> None:
    """
    Verifica se un pasto specifico ha il numero minimo di ricette richiesto.

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
            scegli_pietanza(settimana, giorno, pasto, tipo, ripetibile, controllo_macro, ricette, max_percentuale, pane)


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
            verifica_e_seleziona(settimana, giorno, config['pasto'], config['tipo'], config['ripetibile'], config['min_ricette'], controllo_macro_settimanale, ricette, config['max_percentuale'], config['complemento'])


def scegli_pietanza(settimana, giorno_settimana: str, pasto: str, tipo: str, ripetibile: bool,
                    controllo_macro_settimanale: bool, ricette, max_percentuale, pane: bool = False, ids_specifici=None, skip_check=False) -> bool:
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
                           'colazione', 'spuntino', 'principale', 'contorno', 'ricetta', 'ingredienti', 'info', 'qta', 'complemento']}
        for r in ricette_filtrate
    ]

    # Chiama select_food per selezionare la pietanza
    return select_food(ricette_modificate, settimana, giorno_settimana, pasto, ripetibile, controllo_macro_settimanale, skip_check, max_percentuale, pane, ids_specifici)


def select_food(ricette, settimana, giorno_settimana, pasto, ripetibile, controllo_macro_settimanale, skip_check, max_percentuale, pane: bool = False, ids_specifici=None) -> bool:
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
    ids_disponibili = determina_ids_disponibili(ricette, settimana, giorno_settimana, pasto, ripetibile, pane, ids_specifici)

    # Filtra le ricette in base agli ID disponibili e ai criteri nutrizionali
    ricette_filtrate = [ricetta for ricetta in ricette if ricetta['id'] in ids_disponibili]

    if not ricette_filtrate:
        printer(f"Nessuna ricetta valida trovata per giorno: {giorno_settimana}, pasto: {pasto}")
        return found

    random.shuffle(ricette_filtrate)

    for ricetta in ricette_filtrate:
        percentuale_effettiva = calcola_percentuale_effettiva(ricetta, settimana['day'][giorno_settimana], max_percentuale)
        if percentuale_effettiva >= 0.5:
            if skip_check or controlla_limiti_macronutrienti(ricetta, settimana['day'][giorno_settimana], settimana['weekly'], controllo_macro_settimanale, percentuale_effettiva):
                if check_limiti_consumo_ricetta(ricetta, settimana['consumi'], percentuale_effettiva):
                    aggiorna_settimana(settimana, giorno_settimana, pasto, ricetta, percentuale_effettiva)
                    found = True
                    break

    return found


def calcola_percentuale_effettiva(ricetta, day, max_percentuale) -> float:
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
        if all(day.get(macro, 0) >= ricetta.get(macro, 0) > 0 for macro in
               ['kcal', 'carboidrati', 'proteine', 'grassi']):
            percentuali_possibili = [
                day[macro] / ricetta[macro]
                for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']
            ]
        else:
            percentuali_possibili = []

        # Se nessuna percentuale è calcolabile, restituisci 0
        if not percentuali_possibili:
            return 0

        # Restituisci la percentuale effettiva limitata al range [0.5, max_percentuale]
        return round(max(0.5, min(max_percentuale, min(percentuali_possibili))),1)

    except KeyError as e:
        raise ValueError(f"Chiave mancante nei dati: {e}")
    except Exception as e:
        raise RuntimeError(f"Errore durante il calcolo della percentuale: {str(e)}")


def aggiorna_settimana(settimana, giorno_settimana, pasto, ricetta, percentuale) -> None:
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
    old_qta = ricetta['qta']
    # Aggiungi la ricetta al menu del pasto
    mt['ids'].append(ricetta['id'])
    mt['ricette'].append({
        'ricetta': calcola_quantita(ricetta, 'ricetta', 'nome', old_qta, percentuale),
        'ingredienti': calcola_quantita(ricetta, 'ingredienti', 'id_gruppo', old_qta, percentuale),
        'qta': percentuale,
        'id': ricetta['id'],
        'nome_ricetta': ricetta['nome_ricetta'],
        'kcal': ricetta['kcal'],
        'carboidrati': ricetta['carboidrati'],
        'proteine': ricetta['proteine'],
        'grassi': ricetta['grassi'],
        'info': ricetta['info']
    })

    # Aggiorna i macronutrienti giornalieri e settimanali
    for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
        day[macro] -= round(ricetta[macro] * percentuale, 2)
        weekly[macro] -= round(ricetta[macro] * percentuale, 2)

    aggiorna_limiti_gruppi(ricetta, settimana['consumi'], old_qta, percentuale)


def determina_ids_disponibili(ricette, settimana, giorno_settimana, pasto, ripetibile, pane, ids_specifici) -> list:
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
        if not pane:
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
                    if r['id'] in ids_specifici and r['id'] not in settimana['all_food'] and not r['complemento']
                ]
            if ripetibile:
                return [
                    r['id'] for r in ricette
                    if r['id'] not in settimana['day'][giorno_settimana]['pasto'][pasto]['ids'] and not r['complemento']
                ]
            return [
                r['id'] for r in ricette
                if r['id'] not in settimana['all_food'] and not r['complemento']
            ]
        else:
            return [
                r['id'] for r in ricette if r['contorno'] and r['complemento']
            ]
    except KeyError as e:
        raise KeyError(f"Errore nella struttura: {e}")
    except Exception as e:
        raise RuntimeError(f"Errore durante la determinazione degli ID disponibili: {str(e)}")


def check_limiti_consumo_ricetta(ricetta, consumi, perc) -> bool:
    """
    Verifica se una ricetta rispetta i limiti di consumo settimanale.

    Args:
        ricetta (dict): Ricetta contenente una lista di ingredienti con quantità totali e ID di gruppo.
        consumi (dict): Dizionario dei limiti di consumo rimanenti per ogni gruppo alimentare.
        perc (float): percentuale da utilizzare per il calcolo dei limiti

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
            qta = gruppo.get('qta', 0)

            if id_gruppo in consumi and consumi[id_gruppo] - (qta * perc) < 0:
                return False  # Supera il limite
        return True
    except Exception as e:
        raise RuntimeError(f"Errore durante il controllo dei limiti di consumo: {str(e)}")


def aggiorna_limiti_gruppi(ricetta, consumi, old_perc: float, perc: float = 1.0, rimuovi: bool = False):
    """
    Aggiorna i consumi rimanenti per i gruppi alimentari in base agli ingredienti di una ricetta.

    Args:
        ricetta (dict): Ricetta contenente una lista di ingredienti con quantità totali e ID di gruppo.
        consumi (dict): Dizionario dei consumi rimanenti per ciascun gruppo alimentare.
        user_id: utente abilitato alla funzione
        perc (float): percentuale da utilizzare nei calcoli per i limiti di gruppo
        rimuovi (bool, opzionale): Indica se aggiungere (`True`) o sottrarre (`False`) le quantità.

    Raises:
        KeyError: Se la chiave 'ingredienti' manca nella ricetta.
        ValueError: Se i dati nella ricetta o in consumi non sono validi.
        :param old_perc:
    """
    if 'ingredienti' not in ricetta:
        raise KeyError("La chiave 'ingredienti' è mancante nella ricetta.")
    if not isinstance(consumi, dict):
        raise ValueError("Il parametro 'consumi' deve essere un dizionario.")

    moltiplicatore = 1 if rimuovi else -1
    try:

        for ingrediente in ricetta['ingredienti']:
            id_gruppo = str(ingrediente['id_gruppo'])
            qta_ingrediente = ingrediente['qta']

            if id_gruppo in consumi:
                if old_perc != 0:
                    consumi[id_gruppo] = round(
                        consumi[id_gruppo] + (moltiplicatore * qta_ingrediente / old_perc * perc), 1)
                else:
                    consumi[id_gruppo] = round(consumi[id_gruppo] + (moltiplicatore * qta_ingrediente * perc), 1)

    except Exception as e:
        raise RuntimeError(f"Errore durante l'aggiornamento dei limiti dei gruppi: {str(e)}")


def calcola_quantita(ricetta, chiave_ingredienti, chiave_nome, old_perc, percentuale: float = 1.0) -> list[dict]:
    """
    Funzione generica per calcolare la quantità degli ingredienti o gruppi.

    :param ricetta: Dizionario contenente gli ingredienti.
    :param chiave_ingredienti: Chiave per accedere agli ingredienti ('ricetta' o 'ingredienti').
    :param chiave_nome: Chiave per il nome dell'ingrediente ('nome' o 'id_gruppo').
    :param old_perc: Percentuale di riferimento precedente.
    :param percentuale: Percentuale da applicare (default 1.0).
    :return: Lista di dizionari con nome/id_gruppo e quantità calcolata.
    """
    if chiave_ingredienti not in ricetta:
        raise ValueError(f"Il dizionario della ricetta non contiene la chiave '{chiave_ingredienti}'.")

    return [
        {chiave_nome: ingrediente[chiave_nome],
         'qta': (ingrediente['qta'] / old_perc) * percentuale if old_perc != 0 else ingrediente['qta'] * percentuale}
        for ingrediente in ricetta[chiave_ingredienti]
    ]


def controlla_limiti_macronutrienti(ricetta, day, weekly, controllo_macro_settimanale, perc: float = 1.0) -> bool:
    """
    Verifica se i macronutrienti di una ricetta possono essere aggiunti senza superare i limiti giornalieri o settimanali.

    Args:
        :param ricetta: Informazioni nutrizionali della ricetta, contenente i valori di calorie, carboidrati, proteine e grassi.
        :param day:  Valori dei macronutrienti rimanenti per il giorno corrente.
        :param weekly: Valori dei macronutrienti rimanenti per la settimana corrente.
        :param controllo_macro_settimanale:  Se True, verifica anche i limiti settimanali oltre a quelli giornalieri.
        :param perc:

    Returns:
        bool: True se la ricetta può essere aggiunta senza superare i limiti, False altrimenti.
    """
    try:
        def sufficienti_macronutrienti(limiti) -> bool:
            return (
                limiti['kcal'] - (ricetta['kcal'] * perc) > 0 and
                limiti['carboidrati'] - (ricetta['carboidrati'] * perc) > 0 and
                limiti['proteine'] - (ricetta['proteine'] * perc) > 0 and
                limiti['grassi'] - (ricetta['grassi'] * perc) > 0
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

    if menu['all_food']:
        # Alias per le tabelle
        vir = aliased(VIngredientiRicetta)
        va = aliased(VAlimento)

        # Subquery per il filtro NOT EXISTS per VAlimento
        filtro_va = VAlimento.filtro_alimenti(user_id, va)

        # Subquery per il filtro NOT EXISTS per VIngredientiRicetta
        filtro_vir = VIngredientiRicetta.filtro_ingredienti(user_id, vir)

        # Query principale
        results = (
            db.session.query(
                vir.id_ricetta,
                va.nome,
                func.sum(vir.qta).label('ingredienti'),
            )
            .join(
                va,
                and_(
                    va.id == vir.id_alimento,
                    filtro_va,
                    filtro_vir
                )
            )
            .filter(vir.id_ricetta.in_(menu['all_food']))
            .group_by(vir.id_ricetta, va.nome)
            .order_by(va.nome)
        ).all()
    else:
        results = []

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


def save_weight(data, user_id):
    """
    Salva i dati di peso, vita e fianchi per un utente.
    La logica del peso ideale è ora gestita dalla tabella separata PesoIdeale.
    """
    utente = Utente.get_by_id(user_id)

    # Verifica se l'utente ha un peso ideale configurato
    if utente.peso_ideale is None:
        return False

    # Converti la data string in oggetto date se necessario
    if isinstance(data['date'], str):
        data_rilevazione = datetime.strptime(data['date'], '%Y-%m-%d').date()
    else:
        data_rilevazione = data['date']

    # Cerca se esiste già un record per questa data
    registro_peso = RegistroPeso.query.filter_by(
        user_id=user_id,
        data_rilevazione=data_rilevazione
    ).first()

    if registro_peso:
        # Aggiorna il record esistente
        registro_peso.peso = data['weight'] or None
        registro_peso.vita = data['vita'] or None
        registro_peso.fianchi = data['fianchi'] or None
    else:
        # Crea un nuovo record
        registro_peso = RegistroPeso(
            data_rilevazione=data_rilevazione,
            peso=data['weight'] or None,
            vita=data['vita'] or None,
            fianchi=data['fianchi'] or None,
            user_id=user_id
        )
        db.session.add(registro_peso)

    db.session.commit()
    return True


def get_peso_ideale_per_data_interpolato(user_id, data_target):
    """
    Calcola il peso ideale per una data specifica, interpolando tra i valori esistenti
    se la data non ha un peso ideale specifico.
    """
    # Cerca un peso ideale esatto per la data
    peso_ideale_esatto = PesoIdeale.query.filter_by(
        user_id=user_id,
        data=data_target
    ).first()

    if peso_ideale_esatto:
        return float(peso_ideale_esatto.peso_ideale)

    # Se non c'è un peso ideale esatto, interpola tra i valori più vicini
    peso_precedente = PesoIdeale.query.filter(
        PesoIdeale.user_id == user_id,
        PesoIdeale.data <= data_target
    ).order_by(desc(PesoIdeale.data)).first()

    peso_successivo = PesoIdeale.query.filter(
        PesoIdeale.user_id == user_id,
        PesoIdeale.data >= data_target
    ).order_by(asc(PesoIdeale.data)).first()

    if not peso_precedente or not peso_successivo:
        # Se non ci sono abbastanza punti per interpolare, usa il peso ideale dell'utente
        utente = Utente.get_by_id(user_id)
        return float(utente.peso_ideale) if utente.peso_ideale else None

    if peso_precedente.data == peso_successivo.data:
        return float(peso_precedente.peso_ideale)

    # Interpolazione lineare
    giorni_totali = (peso_successivo.data - peso_precedente.data).days
    giorni_trascorsi = (data_target - peso_precedente.data).days

    differenza_peso = float(peso_successivo.peso_ideale - peso_precedente.peso_ideale)
    peso_giornaliero = differenza_peso / giorni_totali

    peso_ideale_calcolato = float(peso_precedente.peso_ideale) + (peso_giornaliero * giorni_trascorsi)

    return round(peso_ideale_calcolato, 1)


def get_progresso_completo(user_id, data_inizio=None, data_fine=None):
    """
    Ottiene il progresso completo di un utente combinando pesi reali e ideali
    """
    query_pesi_reali = RegistroPeso.query.filter(RegistroPeso.user_id == user_id)
    query_pesi_ideali = PesoIdeale.query.filter(PesoIdeale.user_id == user_id)

    if data_inizio:
        query_pesi_reali = query_pesi_reali.filter(RegistroPeso.data_rilevazione >= data_inizio)
        query_pesi_ideali = query_pesi_ideali.filter(PesoIdeale.data >= data_inizio)

    if data_fine:
        query_pesi_reali = query_pesi_reali.filter(RegistroPeso.data_rilevazione <= data_fine)
        query_pesi_ideali = query_pesi_ideali.filter(PesoIdeale.data <= data_fine)

    pesi_reali = query_pesi_reali.order_by(RegistroPeso.data_rilevazione).all()
    pesi_ideali = query_pesi_ideali.order_by(PesoIdeale.data).all()

    # Combina i dati in un dizionario per data
    risultato = {}

    # Aggiungi i pesi reali
    for peso_reale in pesi_reali:
        data_str = peso_reale.data_rilevazione.strftime('%Y-%m-%d')
        if data_str not in risultato:
            risultato[data_str] = {}

        risultato[data_str].update({
            'data': peso_reale.data_rilevazione,
            'peso_reale': float(peso_reale.peso) if peso_reale.peso else None,
            'vita': float(peso_reale.vita) if peso_reale.vita else None,
            'fianchi': float(peso_reale.fianchi) if peso_reale.fianchi else None
        })

    # Aggiungi i pesi ideali
    for peso_ideale in pesi_ideali:
        data_str = peso_ideale.data.strftime('%Y-%m-%d')
        if data_str not in risultato:
            risultato[data_str] = {'data': peso_ideale.data}

        risultato[data_str]['peso_ideale'] = float(peso_ideale.peso_ideale)

    # Converti in lista ordinata per data
    lista_risultato = list(risultato.values())
    lista_risultato.sort(key=lambda x: x['data'])

    return lista_risultato


def get_peso_hist_completo(user_id):
    """
    Recupera la cronologia completa combinando dati reali e pesi ideali.
    Restituisce un array di oggetti con tutte le informazioni per data.
    """
    # Query per i dati reali
    pesi_reali = RegistroPeso.query.filter_by(user_id=user_id).order_by(asc(RegistroPeso.data_rilevazione)).all()

    # Query per i pesi ideali
    pesi_ideali = PesoIdeale.query.filter_by(user_id=user_id).order_by(asc(PesoIdeale.data)).all()

    # Dizionario per combinare i dati per data
    dati_combinati = {}

    # Aggiungi i dati reali
    for peso_reale in pesi_reali:
        data_str = peso_reale.data_rilevazione.strftime('%Y-%m-%d')
        dati_combinati[data_str] = {
            'data_rilevazione': data_str,
            'peso': float(peso_reale.peso) if peso_reale.peso else None,
            'vita': float(peso_reale.vita) if peso_reale.vita else None,
            'fianchi': float(peso_reale.fianchi) if peso_reale.fianchi else None,
            'peso_ideale': None,  # Sarà popolato dopo
            'user_id': peso_reale.user_id
        }

    # Aggiungi i pesi ideali
    for peso_ideale in pesi_ideali:
        data_str = peso_ideale.data.strftime('%Y-%m-%d')

        if data_str in dati_combinati:
            # Aggiorna il record esistente
            dati_combinati[data_str]['peso_ideale'] = float(peso_ideale.peso_ideale)
        else:
            # Crea nuovo record solo per peso ideale
            dati_combinati[data_str] = {
                'data_rilevazione': data_str,
                'peso': None,
                'vita': None,
                'fianchi': None,
                'peso_ideale': float(peso_ideale.peso_ideale),
                'user_id': peso_ideale.user_id
            }

    # Converti in lista e ordina per data
    risultato = list(dati_combinati.values())
    risultato.sort(key=lambda x: x['data_rilevazione'])

    return risultato


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


def salva_utente_dieta(utente_id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                       meta_basale, meta_giornaliero, calorie_giornaliere, settimane_dieta, carboidrati,
                       proteine, grassi, dieta, attivita_fisica):
    utente = Utente.get_by_id(utente_id)

    # Aggiorna i dati dell'utente
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
    utente.attivita_fisica = attivita_fisica

    db.session.add(utente)

    # Cancella tutti i record di peso ideale esistenti per questo utente
    db.session.query(PesoIdeale).filter(PesoIdeale.user_id == utente_id).delete()

    # Calcola la data di fine dieta
    match = re.match(r"^(.*?)\s*\(", settimane_dieta)
    oggi = datetime.now().date()
    giorni_indietro = (oggi.weekday() - 0) % 7
    lunedi_corrente = oggi - timedelta(days=giorni_indietro)

    settimane = 0
    if match:
        settimane = int(match.group(1))

    data_fine_dieta = lunedi_corrente + (timedelta(days=7 * settimane))

    # Calcola la perdita di peso settimanale
    peso_iniziale = utente.peso
    perdita_peso_totale = peso_iniziale - peso_ideale

    perdita_peso_settimanale = perdita_peso_totale
    if settimane > 0:
        perdita_peso_settimanale = perdita_peso_totale / settimane

    # Crea i record di peso ideale per ogni settimana
    for settimana in range(0, settimane + 1):  # +1 per includere la settimana finale
        if settimana == settimane:
            # Settimana finale - usa la data di fine dieta
            data_settimana = data_fine_dieta
            peso_ideale_settimana = peso_ideale
        else:
            # Settimane intermedie
            data_settimana = lunedi_corrente + timedelta(days=7 * settimana)
            peso_ideale_settimana = peso_iniziale - perdita_peso_settimanale * settimana

        # Crea o aggiorna il record PesoIdeale
        peso_ideale_record = PesoIdeale.query.filter_by(
            user_id=utente_id,
            data=data_settimana
        ).first()

        if not peso_ideale_record:
            peso_ideale_record = PesoIdeale(
                user_id=utente_id,
                data=data_settimana,
                peso_ideale=round(peso_ideale_settimana, 1)
            )
            db.session.add(peso_ideale_record)
        else:
            peso_ideale_record.peso_ideale = round(peso_ideale_settimana, 1)

    # Gestione del registro peso per la settimana corrente (peso iniziale)
    registro_corrente = RegistroPeso.query.filter_by(
        user_id=utente_id,
        data_rilevazione=lunedi_corrente
    ).first()

    if not registro_corrente:
        registro_corrente = RegistroPeso(
            user_id=utente_id,
            data_rilevazione=lunedi_corrente,
            peso=peso_iniziale
        )
        db.session.add(registro_corrente)
    else:
        registro_corrente.peso = peso_iniziale

    db.session.commit()


# 3. FUNZIONE HELPER PER OTTENERE PESO IDEALE PER UNA DATA
def get_peso_ideale_per_data(user_id, data):
    """
    Ottiene il peso ideale per un utente in una data specifica
    """
    peso_ideale = PesoIdeale.query.filter_by(
        user_id=user_id,
        data=data
    ).first()

    return peso_ideale.peso_ideale if peso_ideale else None


# 4. FUNZIONE HELPER PER OTTENERE TUTTI I PESI IDEALI DI UN UTENTE
def get_pesi_ideali_utente(user_id):
    """
    Ottiene tutti i pesi ideali programmati per un utente
    """
    return PesoIdeale.query.filter_by(user_id=user_id).order_by(PesoIdeale.data).all()


# 5. ESEMPIO DI QUERY PER COMBINARE DATI REALI E IDEALI
def get_progresso_peso_completo(user_id):
    """
    Combina dati reali e pesi ideali per mostrare il progresso
    """
    from sqlalchemy import or_

    # Query per ottenere sia i pesi reali che quelli ideali
    pesi_reali = db.session.query(
        RegistroPeso.data_rilevazione.label('data'),
        RegistroPeso.peso.label('peso_reale'),
        db.literal(None).label('peso_ideale')
    ).filter(
        RegistroPeso.user_id == user_id,
        RegistroPeso.peso.isnot(None)
    )

    pesi_ideali = db.session.query(
        PesoIdeale.data.label('data'),
        db.literal(None).label('peso_reale'),
        PesoIdeale.peso_ideale.label('peso_ideale')
    ).filter(PesoIdeale.user_id == user_id)

    # Unisci le query
    tutti_pesi = pesi_reali.union(pesi_ideali).order_by('data').all()

    return tutti_pesi


def aggiungi_ricetta_al_menu(menu, day, meal, meal_id, user_id):
    ricetta = get_ricette_service(user_id, ids=meal_id)[0]
    ricetta['qta'] = 1
    menu['all_food'].append(ricetta['id'])
    menu['day'][day]['pasto'][meal]['ids'].append(ricetta['id'])
    menu['day'][day]['pasto'][meal]['ricette'].append({
        'id': ricetta['id'],
        'nome_ricetta': ricetta['nome_ricetta'],
        'qta': ricetta['qta'],
        'kcal':ricetta['kcal'],
        'carboidrati': ricetta['carboidrati'],
        'grassi': ricetta['grassi'],
        'proteine': ricetta['proteine'],
        'ricetta': calcola_quantita(ricetta, 'ricetta', 'nome', ricetta['qta']),
        'ingredienti': calcola_quantita(ricetta, 'ingredienti', 'id_gruppo', ricetta['qta']),
        'info': ricetta['info']
    })
    aggiorna_macronutrienti(menu, day, ricetta)
    aggiorna_limiti_gruppi(ricetta, menu['consumi'], ricetta['qta'], ricetta['qta'])


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
        aggiorna_limiti_gruppi(ricetta_da_rimuovere, menu['consumi'], ricetta_da_rimuovere['qta'], ricetta_da_rimuovere['qta'],True)


def cancella_tutti_pasti_menu(settimana, day, meal_type, user_id):
    for ricetta in settimana['day'][day]['pasto'][meal_type]['ricette']:
        settimana['all_food'].remove(ricetta['id'])
        aggiorna_macronutrienti(settimana, day, ricetta, True)
        aggiorna_limiti_gruppi(ricetta, settimana['consumi'], ricetta['qta'], ricetta['qta'], True)

    settimana['day'][day]['pasto'][meal_type] = {"ids": [], "ricette": []}


def aggiorna_macronutrienti(menu, day, ricetta, rimuovi=False):
    moltiplicatore = 1 if rimuovi else -1
    for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
        menu['day'][day][macro] += moltiplicatore * ricetta[macro] * ricetta['qta']
        menu['weekly'][macro] += moltiplicatore * ricetta[macro] * ricetta['qta']


def delete_week_menu_service(week_id, user_id):
    MenuSettimanale.query.filter_by(id=week_id, user_id=user_id).delete()
    db.session.commit()


def recupera_ricette_per_alimento(alimento_id, user_id):
    vir = aliased(VIngredientiRicetta)
    vr = aliased(VRicetta)

    # Subquery per il filtro NOT EXISTS per VIngredientiRicetta
    filtro_vir = VIngredientiRicetta.filtro_ingredienti(user_id, alias=vir)

    # Subquery per il filtro NOT EXISTS per VIngredientiRicetta
    filtro_vr = VRicetta.filtro_ricette(user_id, alias=vr)

    ricette = (db.session.query(vr.nome_ricetta)
                       .select_from(vr)
                .outerjoin(
                    vir,
                    and_(
                        vir.id_ricetta == vr.id,
                        filtro_vir
                    )
                )
               .filter(vir.id_alimento == alimento_id)
               .filter(filtro_vr)
               .distinct()
               .all())

    ricette_data = [{'nome_ricetta': r.nome_ricetta} for r in ricette]
    return ricette_data

def completa_menu_service(week_id: int, user_id: int):
    menu = MenuSettimanale.query.filter_by(id=week_id, user_id=user_id).one()

    if not menu:
        raise ValueError(f"Nessun menu trovato per la week_id {week_id}")

    menu_da_completare = menu.menu

    macronutrienti_rimanenti = calcola_macronutrienti_rimanenti_service(menu_da_completare)

    giorni = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica']

    ricette = get_ricette_service(user_id, stagionalita=True, attive=True)

    for giorno in giorni:
        for pasto in pasti_config:
            pasto_data = menu_da_completare['day'][giorno]['pasto'][pasto['pasto']]

            # **1️⃣ Controllo se il pasto è vuoto**
            if not pasto_data['ricette']:
                # **2️⃣ Cerca una ricetta compatibile**
                verifica_e_seleziona(menu_da_completare, giorno, pasto['pasto'], pasto['tipo'], pasto['ripetibile'], pasto['min_ricette'], True, ricette, pasto['max_percentuale'], pasto['complemento'])

    for giorno in giorni:
        for pasto in pasti_config:
            if macronutrienti_rimanenti[giorno]['kcal'] > 0:
                # **2️⃣ Cerca una ricetta compatibile**
                verifica_e_seleziona(menu_da_completare, giorno, pasto['pasto'], pasto['tipo'], pasto['ripetibile'], pasto['min_ricette'], True, ricette, pasto['max_percentuale'], pasto['complemento'])
    update_menu_corrente_service(menu_da_completare, week_id, user_id)


def update_menu_corrente_service(menu_da_salvare, week_id, user_id):

    menu_da_aggiornare = MenuSettimanale.get_by_id(week_id)

    if not menu_da_aggiornare:
        raise ValueError(f"Menu con ID {week_id} non trovato per l'utente {user_id}")

    if isinstance(menu_da_salvare, str):
        try:
            menu = json.loads(menu_da_salvare)  # Se è una stringa JSON, convertirla in un dizionario
        except json.JSONDecodeError as e:
            raise ValueError(f"Errore nella conversione JSON: {e}")

    menu_da_aggiornare.menu = None
    db.session.flush()  # Forza un aggiornamento nel contesto di sessione
    menu_da_aggiornare.menu = menu_da_salvare
    db.session.commit()


def salva_menu_service(menu, user_id, period: dict = None) -> None:
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
        id=get_sequence_value('dieta.seq_menu_settimanale'),
        data_inizio=period['data_inizio'],
        data_fine=period['data_fine'],
        menu=menu,
        user_id=user_id
    )

    db.session.add(new_menu_settimanale)
    db.session.commit()