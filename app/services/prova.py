#app/services/menu_services.py
import os
import random
from copy import deepcopy
from datetime import datetime, timedelta

from sqlalchemy import func, desc

from app.models import db
from app.models.MenuSettimanale import MenuSettimanale
from app.models.Utente import Utente
from app.services.db_services import get_sequence_value
from app.services.modifica_pasti_services import get_menu_service
from app.services.ricette_services import get_ricette_service


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

def genera_menu_utente_service(user_id: int) -> None:
    """
    Genera il menu settimanale per l'utente. Include la settimana corrente, successiva
    e una nuova settimana successiva all'ultima presente, se necessario.

    Args:
        user_id (int): ID dell'utente.

    Returns:
        None
    """
    if not user_id or user_id <= 0:
        raise ValueError("user_id deve essere un intero positivo")

    macronutrienti = Utente.get_by_id(user_id)
    if not macronutrienti.calorie_giornaliere:
        raise ValueError('Macronutrienti non definiti!')

    # Trova l'ultima settimana presente nel database
    query = (db.session.query(MenuSettimanale)
             .filter(MenuSettimanale.user_id==user_id,
                     func.current_date() <= MenuSettimanale.data_fine)
             .order_by(desc(MenuSettimanale.data_fine)))

    ultima_settimana = query.first()

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
        genera_menu(settimana, False, ricette_menu)

        # Ordina la settimana per kcal rimanenti
        #settimana_ordinata = ordina_settimana_per_kcal(settimana)
        genera_menu(settimana, True, ricette_menu)
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
        max_percentuale
        pane

    Returns:
        None
    """
    p = settimana['day'][giorno]['pasto']
    if numero_ricette(p, pasto, tipo, ricette) < min_ricette:
        for _ in range(min_ricette - numero_ricette(p, pasto, tipo, ricette)):
            scegli_pietanza(settimana, giorno, pasto, tipo, ripetibile, controllo_macro, ricette, max_percentuale, pane)


def genera_menu(settimana: dict, controllo_macro_settimanale: bool, ricette: list) -> None:
    """
    Genera un menu settimanale distribuendo ricette su pasti giornalieri.

    Args:
        settimana (dict): La struttura del menu settimanale.
        controllo_macro_settimanale (bool): Indica se controllare i macronutrienti settimanali.
        ricette (list): Lista delle ricette disponibili.

    Returns:
        None
    """

    for giorno in settimana['day']:
        for config in pasti_config:
            verifica_e_seleziona(settimana, giorno, config['pasto'], config['tipo'], config['ripetibile'], config['min_ricette'], controllo_macro_settimanale, ricette, config['max_percentuale'], config['complemento'])


def scegli_pietanza(settimana: dict, giorno_settimana: str, pasto: str, tipo: str, ripetibile: bool,
                    controllo_macro_settimanale: bool, ricette: list, max_percentuale, pane: bool = False, ids_specifici=None, skip_check=False) -> bool:
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
        max_percentuale (float):
        pane (bool):
        ids_specifici (list, opzionale): Lista di ID di ricette specifiche da considerare. Default è None.
        skip_check (bool, opzionale): Se True, ignora i controlli nutrizionali e di limiti durante la selezione. Default è False.

    Returns:
        bool: True se è stata selezionata una pietanza, False altrimenti.
    """

    ricette_filtrate = [r for r in ricette if r[tipo] and r['attiva']]

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
        max_percentuale (float):
        pane (bool)
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


def calcola_percentuale_effettiva(ricetta, day, max_percentuale: float) -> float:
    """
    Calcola la percentuale massima utilizzabile di una ricetta,
    rispettando i limiti giornalieri dei macronutrienti e delle calorie.

    Args:
        max_percentuale:
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
        pane (bool):
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
        old_perc (float):
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