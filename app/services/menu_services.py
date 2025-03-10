#app/services/menu_services.py
import os
import random
import re
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, asc, desc
from sqlalchemy.orm import aliased

from app.models import db
from app.models.IngredientiRicetta import IngredientiRicetta
from app.models.MenuSettimanale import MenuSettimanale
from app.models.RegistroPeso import RegistroPeso
from app.models.Utente import Utente
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from app.services.db_services import get_sequence_value
from app.services.modifica_pasti_services import get_menu_service, update_menu_corrente_service
from app.services.ricette_services import get_ricette_service
from app.services.util_services import printer, print_query, calcola_macronutrienti_rimanenti_service

MAX_RETRY = int(os.getenv('MAX_RETRY'))

LIMITI_CONSUMO = {
    '1': 240,   # Uova (2-4 a settimana)
    '2': 0,     # Pesce (2-3 porzioni settimanali)
    '3': 400,   # Carne Bianca (1-2 porzioni settimanali)
    '4': 150,   # Carne Rossa (1 porzione settimanale)
    '5': 700,   # Legumi (2-4 porzioni settimanali)
    '8': 700,   # Cereali (100-120 g al giorno)
    '12': 190,  # Frutta secca (20-30 g al giorno)
    '15': 140   # Olio o grassi da condimento (20-30 g al giorno)
}

pasti_config = [
    {'pasto': 'colazione', 'tipo': 'colazione', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'colazione', 'tipo': 'colazione_sec', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'spuntino_mattina', 'tipo': 'spuntino', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'spuntino_pomeriggio', 'tipo': 'spuntino', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'spuntino_sera', 'tipo': 'spuntino', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'pranzo', 'tipo': 'principale', 'ripetibile': False, 'min_ricette': 1},
    {'pasto': 'cena', 'tipo': 'principale', 'ripetibile': False, 'min_ricette': 1},
    {'pasto': 'pranzo', 'tipo': 'contorno', 'ripetibile': True, 'min_ricette': 1},
    {'pasto': 'cena', 'tipo': 'contorno', 'ripetibile': True, 'min_ricette': 1},
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

    print_query(query)

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
    ricette_menu = get_ricette_service(user_id, complemento='no', stagionalita=True, data_stagionalita=period["data_fine"])
    if not get_menu_service(user_id, period=period):
        settimana = deepcopy(get_settimana(macronutrienti))
        genera_menu(settimana, False, ricette_menu, user_id)

        # Ordina la settimana per kcal rimanenti
        settimana_ordinata = ordina_settimana_per_kcal(settimana)
        genera_menu(settimana_ordinata, True, ricette_menu, user_id)
        salva_menu(settimana_ordinata, user_id, period=period)


def verifica_e_seleziona(settimana, giorno, pasto, tipo, ripetibile, min_ricette, controllo_macro, ricette, user_id) -> None:
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
                           'colazione', 'spuntino', 'principale', 'contorno', 'ricetta', 'ingredienti', 'info', 'qta']}
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
    ricette_filtrate = [ricetta for ricetta in ricette if ricetta['id'] in ids_disponibili]

    if not ricette_filtrate:
        printer(f"Nessuna ricetta valida trovata per giorno: {giorno_settimana}, pasto: {pasto}")
        return found

    random.shuffle(ricette_filtrate)

    for ricetta in ricette_filtrate:
        percentuale_effettiva = calcola_percentuale_effettiva(ricetta, settimana['day'][giorno_settimana])
        if percentuale_effettiva >= 0.5:
            if skip_check or controlla_limiti_macronutrienti(ricetta, settimana['day'][giorno_settimana], settimana['weekly'], controllo_macro_settimanale, percentuale_effettiva):
                if check_limiti_consumo_ricetta(ricetta, settimana['consumi'], percentuale_effettiva):
                    aggiorna_settimana(settimana, giorno_settimana, pasto, ricetta, percentuale_effettiva)
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
        return round(max(0.5, min(1.0, min(percentuali_possibili))),1)

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


def save_weight(data, user_id):

    utente = Utente.get_by_id(user_id)

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


def salva_utente_dieta(utente_id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                       meta_basale, meta_giornaliero, calorie_giornaliere, settimane_dieta, carboidrati,
                       proteine, grassi, dieta):

    utente = Utente.get_by_id(utente_id)

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
        RegistroPeso.user_id == utente_id,
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
        registro_intermedio = RegistroPeso.query.filter_by(user_id=utente_id, data_rilevazione=data_intermedia.date()).first()
        if not registro_intermedio:
            # Inserisci il punto intermedio nel database
            registro_intermedio = RegistroPeso(
                user_id=utente_id,
                data_rilevazione=data_intermedia.date(),
                peso=peso_iniziale if settimana == 0 else None,
                peso_ideale=round(peso_ideale_intermedio, 1)
            )
            db.session.add(registro_intermedio)
        else:
            registro_intermedio.peso = peso_iniziale if settimana == 0 else None
            registro_intermedio.peso_ideale = round(peso_ideale_intermedio, 1)


    # cerco se esiste già un record con la data di fine dieta
    new_peso = RegistroPeso.query.filter_by(user_id=utente_id, data_rilevazione=data_fine_dieta).first()

    # se c'è aggiorno solo il peso ideale
    if new_peso:
        new_peso.peso_ideale = peso_ideale
    else:
        # altrimenti creo la riga
        new_peso = RegistroPeso(
            user_id=utente_id,
            data_rilevazione=data_fine_dieta,
            peso_ideale=peso_ideale
        )
        db.session.add(new_peso)

    db.session.commit()


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

    macronutrienti_rimanenti = calcola_macronutrienti_rimanenti_service(menu.menu)

    giorni = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica']
    pasti = ['colazione', 'spuntino_mattina', 'pranzo', 'spuntino_pomeriggio', 'cena', 'spuntino_sera']

    for giorno in giorni:
        for pasto in pasti:
            pasto_data = menu.menu['day'][giorno]['pasto'][pasto]
            # **1️⃣ Controllo se il pasto è vuoto**

            if not pasto_data['ricette']:
                # **2️⃣ Cerca una ricetta compatibile**
                ricetta = trova_ricetta_compatibile_service(user_id, macronutrienti_rimanenti[giorno])

                if ricetta:
                    aggiungi_ricetta_al_menu(menu.menu, giorno, pasto, ricetta['id'], user_id)


    for giorno in giorni:
        for pasto in pasti:
            if macronutrienti_rimanenti[giorno]['kcal'] > 0:
                ricetta = trova_ricetta_compatibile_service(user_id, macronutrienti_rimanenti[giorno])

                if ricetta:
                    aggiungi_ricetta_al_menu(menu.menu, giorno, pasto, ricetta['id'], user_id)

    update_menu_corrente_service(menu.menu, week_id, user_id)


def trova_ricetta_compatibile_service(user_id: int, macro_rimanenti):
    ricette = get_ricette_service(user_id)

    # Filtro per kcal e 2 su 3 macronutrienti compatibili
    percentuali = [1.0, 1.3, 1.2, 1.1, 0.9, 0.8, 0.5]
    for ricetta in ricette:
        for perc in percentuali:
            kcal_ok = ricetta['kcal'] * perc <= macro_rimanenti['kcal']
            macro_ok = sum([
                ricetta['carboidrati'] * perc <= macro_rimanenti['carboidrati'],
                ricetta['proteine'] * perc <= macro_rimanenti['proteine'],
                ricetta['grassi'] * perc <= macro_rimanenti['grassi']
            ]) >= 2

            if kcal_ok and macro_ok:
                return {
                    'id': ricetta['id'],
                    'nome_ricetta': ricetta['nome_ricetta'],
                    'qta': perc,
                    'kcal': ricetta['kcal'] * perc,
                    'carboidrati': ricetta['carboidrati'] * perc,
                    'proteine': ricetta['proteine'] * perc,
                    'grassi': ricetta['grassi'] * perc,
                    'fibre': ricetta.get('fibre', 0) * perc
                }

    return None