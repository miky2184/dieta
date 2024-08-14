import os
import random
import psycopg2.extras
import psycopg2
from copy import deepcopy
from psycopg2.extras import Json
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.database import get_db_connection
from app.models.common import printer


BOT_TOKEN = os.getenv('BOT_TOKEN')
USER_CHAT_ID = os.getenv('USER_CHAT_ID')
GS_URL = os.getenv('GS_URL')
MAX_KCAL = int(os.getenv('MAX_KCAL'))
CARBOIDRATI_MAX_GIORNALIERI = float(os.getenv('CARBOIDRATI_MAX_GIORNALIERI'))
PROTEINE_MAX_GIORNALIERI = float(os.getenv('PROTEINE_MAX_GIORNALIERI'))
GRASSI_MAX_GIORNALIERI = float(os.getenv('GRASSI_MAX_GIORNALIERI'))
MAX_RETRY = int(os.getenv('MAX_RETRY'))
WIDTH_COLS_QTA = int(os.getenv('WIDTH_COLS_QTA'))
SLEEP_TIME = int(os.getenv('SLEEP_TIME', 20))
SA = os.getenv('SA')

ingredienti_ricetta = {}
ricetta = {'ids': [], 'ricette': []}

pasto = {'colazione': deepcopy(ricetta),
         'spuntino': deepcopy(ricetta),
         'pranzo': deepcopy(ricetta),
         'cena': deepcopy(ricetta)
         }

macronutrienti_giornalieri = {
    'carboidrati': Decimal(CARBOIDRATI_MAX_GIORNALIERI),
    'proteine': Decimal(PROTEINE_MAX_GIORNALIERI),
    'grassi': Decimal(GRASSI_MAX_GIORNALIERI),
    'kcal': Decimal(MAX_KCAL),
    'pasto': deepcopy(pasto)
}

macronutrienti_settimali = {
    'carboidrati': Decimal(CARBOIDRATI_MAX_GIORNALIERI) * 7,
    'proteine': Decimal(PROTEINE_MAX_GIORNALIERI) * 7,
    'grassi': Decimal(GRASSI_MAX_GIORNALIERI) * 7,
    'kcal': Decimal(MAX_KCAL) * 7
}

orig_settimana = {'weekly': macronutrienti_settimali,
             'day': {
                 'lunedi': deepcopy(macronutrienti_giornalieri),
                 'martedi': deepcopy(macronutrienti_giornalieri),
                 'mercoledi': deepcopy(macronutrienti_giornalieri),
                 'giovedi': deepcopy(macronutrienti_giornalieri),
                 'venerdi': deepcopy(macronutrienti_giornalieri),
                 'sabato': deepcopy(macronutrienti_giornalieri),
                 'domenica': deepcopy(macronutrienti_giornalieri)
             },
             'all_food': []
             }


def scegli_pietanza(settimana, giorno_settimana: str, meal_time: str, tipo: str, perc: float, disponibili: bool,
                    weekly_check: bool, ricette):
    """
    Seleziona una pietanza dalla lista di ricette pre-caricate in memoria.
    """
    perc_decimal = Decimal(str(perc))
    # Filtra le ricette in base al tipo di pasto richiesto
    printer(f"Ricette prima del filtro: {ricette}")
    ricette_filtrate = [r for r in ricette if r[tipo]]
    printer(f"Ricette dopo il filtro: {ricette_filtrate}")
    #printer(f"ricette_filtrate{ricette_filtrate}")
    # Moltiplica i valori nutrizionali per la percentuale
    ricette_modificate = []
    for ricetta in ricette_filtrate:
        if ricetta['attiva']:
            ricetta_modificata = {
                'id': ricetta['id'],
                'nome_ricetta': ricetta['nome_ricetta'],
                'kcal': ricetta['kcal'] * perc_decimal,
                'carboidrati': ricetta['carboidrati'] * perc_decimal,
                'proteine': ricetta['proteine'] * perc_decimal,
                'grassi': ricetta['grassi'] * perc_decimal,
                'colazione': ricetta['colazione'],
                'spuntino': ricetta['spuntino'],
                'principale': ricetta['principale'],
                'contorno': ricetta['contorno']
            }
            ricette_modificate.append(ricetta_modificata)

    # Invoca select_food con le ricette modificate
    return select_food(ricette_modificate, settimana, giorno_settimana, meal_time, MAX_RETRY, perc, disponibili, False, weekly_check)

def select_food(rows, settimana, giorno_settimana, meal_time, max_retry, perc: float, disponibili: bool, found: bool,
                weekly_check: bool):
    if disponibili:
        ids_disponibili = [oggetto['id'] for oggetto in rows if oggetto['id'] not in settimana['all_food']]
    else:
        ids_disponibili = [oggetto['id'] for oggetto in rows if
                           oggetto['id'] not in settimana.get('day').get(giorno_settimana).get('pasto').get(
                               meal_time).get('ids')]

    if ids_disponibili and max_retry > 0:
        # Seleziona casualmente un ID dalla lista dei disponibili
        id_selezionato = random.choice(ids_disponibili)
        max_retry = max_retry - 1

        # Trova l'oggetto corrispondente all'ID selezionato
        ricetta_selezionata = next(oggetto for oggetto in rows if oggetto['id'] == id_selezionato)

        mt = settimana.get('day').get(giorno_settimana).get('pasto').get(meal_time)
        day = settimana.get('day').get(giorno_settimana)
        weekly_nut = settimana.get('weekly')
        if (
                ((day.get('kcal') - ricetta_selezionata.get('kcal')) > 0 and
                 (day.get('carboidrati') - ricetta_selezionata.get('carboidrati')) > 0 and
                 (day.get('proteine') - ricetta_selezionata.get('proteine')) > 0 and
                 (day.get('grassi') - ricetta_selezionata.get('grassi')) > 0) or (weekly_check and
                                                                                  (weekly_nut.get(
                                                                                      'kcal') - ricetta_selezionata.get(
                                                                                      'kcal') > 0 and
                                                                                   (weekly_nut.get(
                                                                                       'carboidrati') - ricetta_selezionata.get(
                                                                                       'carboidrati')) > 0 and
                                                                                   (weekly_nut.get(
                                                                                       'proteine') - ricetta_selezionata.get(
                                                                                       'proteine')) > 0 and
                                                                                   (weekly_nut.get(
                                                                                       'grassi') - ricetta_selezionata.get(
                                                                                       'grassi')) > 0))
        ):
            settimana.get('all_food').append(id_selezionato)
            mt.get('ids').append(id_selezionato)
            r = {'qta': perc, 'nome_ricetta': ricetta_selezionata.get('nome_ricetta')}
            mt.get('ricette').append(r)
            day['kcal'] = day.get('kcal') - ricetta_selezionata.get('kcal')
            day['carboidrati'] = day.get('carboidrati') - ricetta_selezionata.get('carboidrati')
            day['proteine'] = day.get('proteine') - ricetta_selezionata.get('proteine')
            day['grassi'] = day.get('grassi') - ricetta_selezionata.get('grassi')
            weekly_nut['kcal'] = weekly_nut.get('kcal') - ricetta_selezionata.get('kcal')
            weekly_nut['carboidrati'] = weekly_nut.get('carboidrati') - ricetta_selezionata.get('carboidrati')
            weekly_nut['proteine'] = weekly_nut.get('proteine') - ricetta_selezionata.get('proteine')
            weekly_nut['grassi'] = weekly_nut.get('grassi') - ricetta_selezionata.get('grassi')
            found = True
        else:
            select_food(rows, settimana, giorno_settimana, meal_time, max_retry, perc, disponibili, False, weekly_check)

    return found


def carica_ricette():
    """
    Carica tutte le ricette disponibili dal database in memoria.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT distinct r.id, r.nome_ricetta,
                ceil(sum((carboidrati/100*qta*4)+(proteine/100*qta*4)+(grassi/100*qta*9)) over (partition by ir.id_ricetta)) as kcal,
                round(sum(carboidrati/100*qta) over (partition by ir.id_ricetta), 2) as carboidrati,
                round(sum(proteine/100*qta) over (partition by ir.id_ricetta), 2) as proteine,
                round(sum(grassi/100*qta) over (partition by ir.id_ricetta), 2) as grassi,
                r.colazione, r.spuntino, r.principale, r.contorno, r.colazione_sec, r.enabled as attiva
            FROM dieta.ingredienti_ricetta ir 
            left JOIN dieta.ricetta r ON (ir.id_ricetta = r.id)
            left JOIN dieta.alimento a ON (ir.id_alimento = a.id)
            WHERE 1=1 
            -- AND r.enabled
            AND (frutta AND extract(month FROM current_date) = ANY(stagionalita) OR NOT frutta)
            order by enabled desc, r.nome_ricetta
        """)
        ricette = cur.fetchall()

    return ricette

def genera_menu(settimana, check_weekly: bool, ricette) -> None:
    percentuali = [1, 2, 0.75, 0.5]
    for perc in percentuali:
        for _ in range(MAX_RETRY):
            printer(f"settimana::{settimana}")
            for giorno in settimana['day']:
                p = settimana['day'][giorno]['pasto']
                if len(p['pranzo']['ricette']) < 1:
                    scegli_pietanza(settimana, giorno, 'pranzo', 'principale', perc, True, check_weekly, ricette)
                if len(p['cena']['ricette']) < 1:
                    scegli_pietanza(settimana, giorno, 'cena', 'principale', perc, True, check_weekly, ricette)
                if len(p['colazione']['ricette']) < 2:
                    scegli_pietanza(settimana, giorno, 'colazione', 'colazione', perc, False, check_weekly, ricette)
                    scegli_pietanza(settimana, giorno, 'colazione', 'colazione_sec', perc, False, check_weekly, ricette)
                scegli_pietanza(settimana, giorno, 'pranzo', 'contorno', perc, True, check_weekly, ricette)
                scegli_pietanza(settimana, giorno, 'cena', 'contorno', perc, True, check_weekly, ricette)
                if len(p['spuntino']['ricette']) < 2:
                    scegli_pietanza(settimana, giorno, 'spuntino', 'spuntino', perc, False, check_weekly, ricette)

    return settimana

def definisci_calorie_macronutrienti():
    """Calcola le calorie e i macronutrienti giornalieri e li restituisce."""

    # Prepara i dati da restituire
    data_to_write = {
        "kcal": MAX_KCAL,
        "carboidrati": CARBOIDRATI_MAX_GIORNALIERI,
        "proteine": PROTEINE_MAX_GIORNALIERI,
        "grassi": GRASSI_MAX_GIORNALIERI
    }

    return data_to_write


def stampa_ricette():
    """
    Recupera le ricette dal database e restituisce i dati come lista di dizionari.
    """

    ricette = []
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT r.nome_ricetta,
                            ceil(sum((carboidrati/100*qta*4) + (proteine/100*qta*4) + (grassi/100*qta*9)) OVER (PARTITION BY ir.id_ricetta)) AS kcal,
                            round(sum(carboidrati/100*qta) OVER (PARTITION BY ir.id_ricetta), 2) AS carboidrati,
                            round(sum(proteine/100*qta) OVER (PARTITION BY ir.id_ricetta), 2) AS proteine,
                            round(sum(grassi/100*qta) OVER (PARTITION BY ir.id_ricetta), 2) AS grassi
            FROM dieta.ingredienti_ricetta ir
            JOIN dieta.ricetta r ON (ir.id_ricetta = r.id)
            JOIN dieta.alimento a ON (ir.id_alimento = a.id)
            WHERE 1=1
            ORDER BY nome_ricetta
        """)
        rows = cur.fetchall()

        for row in rows:
            ricette.append({
                'nome_ricetta': row['nome_ricetta'],
                'kcal': float(row['kcal']),
                'carboidrati': float(row['carboidrati']),
                'proteine': float(row['proteine']),
                'grassi': float(row['grassi'])
            })

    return ricette


def stampa_ingredienti_ricetta():
    """
    Recupera gli ingredienti delle ricette dal database e restituisce i dati come lista di dizionari.
    """
    ingredienti = []

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.nome_ricetta, a.nome AS nome_alimento, ir.qta
            FROM dieta.ingredienti_ricetta ir
            JOIN dieta.ricetta r ON (ir.id_ricetta = r.id)
            JOIN dieta.alimento a ON (a.id = ir.id_alimento)
            ORDER BY nome_ricetta
        """)
        rows = cur.fetchall()

        for row in rows:
            ingredienti.append({
                'nome_ricetta': row['nome_ricetta'],
                'nome_alimento': row['nome_alimento'],
                'qta': float(row['qta'])
            })

    return ingredienti


def stampa_lista_della_spesa(ids_all_food: list):
    """
    Recupera la lista della spesa basata sugli ID degli alimenti e restituisce i dati come lista di dizionari.
    """
    conn = None
    lista_della_spesa = []

    with get_db_connection() as conn:
        cur = conn.cursor()
        # Crea una tabella temporanea per l'elaborazione
        cur.execute('''
            CREATE TEMP TABLE temp_ricetta_id (
                id_ricetta BIGINT NOT NULL
            ) ON COMMIT DROP;
        ''')

        # Inserisci gli ID delle ricette nella tabella temporanea
        psycopg2.extras.execute_values(cur, '''
            INSERT INTO temp_ricetta_id (id_ricetta)
            VALUES %s
        ''', [(value,) for value in ids_all_food])

        # Recupera la lista degli ingredienti e le quantità totali
        cur.execute('''
            SELECT a.nome AS alimento, SUM(ir.qta) AS qta_totale
            FROM dieta.ingredienti_ricetta ir
            JOIN dieta.alimento a ON ir.id_alimento = a.id
            JOIN temp_ricetta_id t ON t.id_ricetta = ir.id_ricetta
            GROUP BY a.nome
            ORDER BY a.nome;
        ''')
        rows = cur.fetchall()

        for row in rows:
            lista_della_spesa.append({
                'alimento': row['alimento'],
                'qta_totale': float(row['qta_totale'])
            })

    return lista_della_spesa

def convert_decimal_to_float(data):
    """
    Convert all Decimal instances in a data structure to float.
    Works recursively on dictionaries and lists.
    """
    if isinstance(data, dict):
        return {k: convert_decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_decimal_to_float(element) for element in data]
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data

def salva_menu_corrente(menu):

    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        # Calcola l'inizio e la fine della prossima settimana
        oggi = datetime.now()
        ultimo_lunedi = oggi - timedelta(days=(7 - oggi.weekday()+1))
        domenica_prossima = ultimo_lunedi + timedelta(days=6)

        # Converti tutti i Decimals a float
        menu_convertito = convert_decimal_to_float(menu)

        # Inserisce un nuovo menu per la prossima settimana
        cur.execute("""
            INSERT INTO dieta.menu_settimanale (data_inizio, data_fine, menu)
            VALUES (%s, %s, %s)
        """, (ultimo_lunedi.date(), domenica_prossima.date(), Json(menu_convertito)))

        conn.commit()


def salva_menu_settimana_prossima(menu):

    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        # Calcola l'inizio e la fine della prossima settimana
        oggi = datetime.now()
        lunedi_prossimo = oggi + timedelta(days=(7 - oggi.weekday()))
        domenica_prossima = lunedi_prossimo + timedelta(days=6)

        # Converti tutti i Decimals a float
        menu_convertito = convert_decimal_to_float(menu)

        # Verifica se un menu per la prossima settimana esiste già
        cur.execute("""
            SELECT id FROM dieta.menu_settimanale WHERE data_inizio = %s AND data_fine = %s
        """, (lunedi_prossimo.date(), domenica_prossima.date()))
        result = cur.fetchone()

        if result:
            # Aggiorna il menu esistente
            cur.execute("""
                UPDATE dieta.menu_settimanale
                SET menu = %s
                WHERE id = %s
            """, (Json(menu_convertito), result[0]))
        else:
            # Inserisce un nuovo menu per la prossima settimana
            cur.execute("""
                INSERT INTO dieta.menu_settimanale (data_inizio, data_fine, menu)
                VALUES (%s, %s, %s)
            """, (lunedi_prossimo.date(), domenica_prossima.date(), Json(menu_convertito)))

        conn.commit()


def get_menu_corrente():
    menu_corrente = None

    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        oggi = datetime.now()

        query = """
            SELECT menu FROM dieta.menu_settimanale
            WHERE %s between data_inizio AND data_fine 
        """
        params = (oggi.date(),)

        # Stampa la query con parametri
        print(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)
        result = cur.fetchone()

        if result:
            menu_corrente = result['menu']

    return menu_corrente


def get_menu_settima_prossima():
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        # Calcola l'inizio e la fine della prossima settimana
        oggi = datetime.now()
        lunedi_prossimo = oggi + timedelta(days=(7 - oggi.weekday()))
        domenica_prossima = lunedi_prossimo + timedelta(days=6)

        query = """
            SELECT id FROM dieta.menu_settimanale WHERE data_inizio = %s AND data_fine = %s
        """

        params = (lunedi_prossimo.date(), domenica_prossima.date(),)

        # Verifica se un menu per la prossima settimana esiste già
        cur.execute(query, params)
        result = cur.fetchone()

        if result:
            return True

    return False



def get_settimane_salvate():
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        cur.execute("""
            SELECT id, data_inizio, data_fine FROM dieta.menu_settimanale
            ORDER BY data_inizio DESC
        """)
        settimane = cur.fetchall()

    return settimane
