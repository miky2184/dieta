import os
import random
import psycopg2.extras
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.database import get_db_connection
from app.models.common import printer
from copy import deepcopy
from decimal import Decimal

MAX_RETRY = int(os.getenv('MAX_RETRY'))


def scegli_pietanza(settimana, giorno_settimana: str, pasto: str, tipo: str, percentuale_pietanza: float, ripetibile: bool,
                    controllo_macro_settimanale: bool, ricette, ids_specifici=None, skip_check=False):
    """
    Seleziona una pietanza dalla lista di ricette pre-caricate in memoria.
    Se ids_specifici è fornito, filtra le ricette solo per quegli ID.
    """
    perc_decimal = Decimal(str(percentuale_pietanza))

    # Filtra le ricette in base al tipo di pasto richiesto
    ricette_filtrate = [r for r in ricette if r[tipo]]

    # Se ids_specifici è fornito, filtra ulteriormente le ricette
    if ids_specifici:
        ricette_filtrate = [r for r in ricette_filtrate if r['id'] in ids_specifici]

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
                'contorno': ricetta['contorno'],
                'ricetta': ricetta['ricetta']
            }
            ricette_modificate.append(ricetta_modificata)

    # Invoca select_food con le ricette modificate
    return select_food(ricette_modificate, settimana, giorno_settimana, pasto, MAX_RETRY, percentuale_pietanza, ripetibile,
                       False, controllo_macro_settimanale, skip_check)


def select_food(ricette, settimana, giorno_settimana, pasto, max_retry, perc: float, ripetibile: bool, found: bool,
                controllo_macro_settimanale: bool, skip_check: bool=False):
    if not ripetibile:
        ids_disponibili = [oggetto['id'] for oggetto in ricette if oggetto['id'] not in settimana['all_food']]
    else:
        ids_disponibili = [oggetto['id'] for oggetto in ricette if
                           oggetto['id'] not in settimana.get('day').get(giorno_settimana).get('pasto').get(
                               pasto).get('ids')]

    if ids_disponibili and max_retry > 0:
        # Seleziona casualmente un ID dalla lista dei disponibili
        id_selezionato = random.choice(ids_disponibili)
        max_retry = max_retry - 1

        # Trova l'oggetto corrispondente all'ID selezionato
        ricetta_selezionata = next(oggetto for oggetto in ricette if oggetto['id'] == id_selezionato)

        mt = settimana.get('day').get(giorno_settimana).get('pasto').get(pasto)
        day = settimana.get('day').get(giorno_settimana)
        macronutrienti_settimali = settimana.get('weekly')
        if (    skip_check or
                (
                    (day.get('kcal') - ricetta_selezionata.get('kcal')) > 0 and
                    (day.get('carboidrati') - ricetta_selezionata.get('carboidrati')) > 0 and
                    (day.get('proteine') - ricetta_selezionata.get('proteine')) > 0 and
                    (day.get('grassi') - ricetta_selezionata.get('grassi')) > 0
                )
                or
                    (controllo_macro_settimanale and
                     (macronutrienti_settimali.get('kcal') - ricetta_selezionata.get('kcal') > 0 and
                    (macronutrienti_settimali.get('carboidrati') - ricetta_selezionata.get('carboidrati')) > 0 and
                    (macronutrienti_settimali.get('proteine') - ricetta_selezionata.get('proteine')) > 0 and
                    (macronutrienti_settimali.get('grassi') - ricetta_selezionata.get('grassi')) > 0)
                )
        ):
            settimana.get('all_food').append(id_selezionato)
            mt.get('ids').append(id_selezionato)
            r = {'qta': perc,
                 'id': ricetta_selezionata.get('id'),
                 'nome_ricetta': ricetta_selezionata.get('nome_ricetta'),
                 'ricetta': ricetta_selezionata.get('ricetta'),
                 'kcal': ricetta_selezionata.get('kcal'),
                 'carboidrati': ricetta_selezionata.get('carboidrati'),
                'proteine':  ricetta_selezionata.get('proteine'),
                'grassi': ricetta_selezionata.get('grassi'),
                }
            mt.get('ricette').append(r)
            day['kcal'] = day.get('kcal') - ricetta_selezionata.get('kcal')
            day['carboidrati'] = day.get('carboidrati') - ricetta_selezionata.get('carboidrati')
            day['proteine'] = day.get('proteine') - ricetta_selezionata.get('proteine')
            day['grassi'] = day.get('grassi') - ricetta_selezionata.get('grassi')
            macronutrienti_settimali['kcal'] = macronutrienti_settimali.get('kcal') - ricetta_selezionata.get('kcal')
            macronutrienti_settimali['carboidrati'] = macronutrienti_settimali.get('carboidrati') - ricetta_selezionata.get('carboidrati')
            macronutrienti_settimali['proteine'] = macronutrienti_settimali.get('proteine') - ricetta_selezionata.get('proteine')
            macronutrienti_settimali['grassi'] = macronutrienti_settimali.get('grassi') - ricetta_selezionata.get('grassi')
            found = True
        else:
            select_food(ricette, settimana, giorno_settimana, pasto, max_retry, perc, ripetibile, False, controllo_macro_settimanale)

    return found


def carica_ricette(ids=None, stagionalita: bool=False, attive:bool=False):
    """
    Carica tutte le ricette disponibili dal database in memoria.
    """
    and_attive = ""
    and_ids = ""
    and_stagionalita = ""
    if stagionalita:
        and_stagionalita = " AND (frutta AND extract(month FROM current_date) = ANY(stagionalita) OR NOT frutta)"

    if ids:
        and_ids = f" AND r.id = {ids}"

    if attive:
        and_attive = " AND r.enabled"

    with get_db_connection() as conn:
        cur = conn.cursor()
        query = f"""
            SELECT distinct
    r.id, 
    r.nome_ricetta,
    CEIL(SUM((carboidrati/100 * qta * 4) + 
             (proteine/100 * qta * 4) + 
             (grassi/100 * qta * 9)) OVER (PARTITION BY r.id)) AS kcal,
    ROUND(SUM(carboidrati/100 * qta) OVER (PARTITION BY r.id), 2) AS carboidrati,
    ROUND(SUM(proteine/100 * qta) OVER (PARTITION BY r.id), 2) AS proteine,
    ROUND(SUM(grassi/100 * qta) OVER (PARTITION BY r.id), 2) AS grassi,
    r.colazione, 
    r.spuntino, 
    r.principale, 
    r.contorno, 
    r.colazione_sec, 
    r.enabled AS attiva,
    COALESCE(i.ricetta, '') AS ricetta
FROM dieta.ricetta r
LEFT JOIN (
    SELECT 
        ir.id_ricetta, 
        string_agg(a.nome || ': ' || ir.qta || 'g', ', ') AS ricetta
    FROM dieta.ingredienti_ricetta ir
    LEFT JOIN dieta.alimento a ON ir.id_alimento = a.id
    GROUP BY ir.id_ricetta
) i ON r.id = i.id_ricetta
LEFT JOIN dieta.ingredienti_ricetta ir ON ir.id_ricetta = r.id
LEFT JOIN dieta.alimento a ON ir.id_alimento = a.id
where 1=1
{and_stagionalita} {and_ids} {and_attive}
GROUP BY r.id, r.nome_ricetta,carboidrati, proteine, grassi, qta, r.colazione, r.spuntino, r.principale, r.contorno, r.colazione_sec, r.enabled, i.ricetta
 order by enabled desc, r.nome_ricetta

        """

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        ricette = cur.fetchall()

    return ricette


def genera_menu(settimana, controllo_macro_settimanale: bool, ricette) -> None:
    percentuali = [1, 0.75, 0.5]
    id_pane = 272

    for percentuale_pietanza in percentuali:
        for _ in range(MAX_RETRY):
            for giorno in settimana['day']:
                p = settimana['day'][giorno]['pasto']

                if len(p['pranzo']['ricette']) == 0:
                    scegli_pietanza(settimana, giorno, 'pranzo', 'principale', percentuale_pietanza, False, controllo_macro_settimanale, ricette)
                if len(p['cena']['ricette']) == 0:
                    scegli_pietanza(settimana, giorno, 'cena', 'principale', percentuale_pietanza, False, controllo_macro_settimanale, ricette)
                if len(p['colazione']['ricette']) <= 1:
                    scegli_pietanza(settimana, giorno, 'colazione', 'colazione', percentuale_pietanza, True, controllo_macro_settimanale, ricette)
                    scegli_pietanza(settimana, giorno, 'colazione', 'colazione_sec', percentuale_pietanza, True, controllo_macro_settimanale, ricette)

                # Aggiungi il pane sia a pranzo che a cena
                scegli_pietanza(settimana, giorno, 'pranzo', 'contorno', 1, True, controllo_macro_settimanale, ricette, ids_specifici=[id_pane], skip_check=True)
                scegli_pietanza(settimana, giorno, 'cena', 'contorno', 1, True, controllo_macro_settimanale, ricette, ids_specifici=[id_pane], skip_check=True)

                if len(p['pranzo']['ricette']) < 3:
                    scegli_pietanza(settimana, giorno, 'pranzo', 'contorno', percentuale_pietanza, True, controllo_macro_settimanale, ricette)

                if len(p['cena']['ricette']) < 3:
                    scegli_pietanza(settimana, giorno, 'cena', 'contorno', percentuale_pietanza, True, controllo_macro_settimanale, ricette)

                if len(p['spuntino_mattina']['ricette']) == 0:
                    scegli_pietanza(settimana, giorno, 'spuntino_mattina', 'spuntino', percentuale_pietanza, True, controllo_macro_settimanale, ricette, skip_check=True)
                if len(p['spuntino_pomeriggio']['ricette']) == 0:
                    scegli_pietanza(settimana, giorno, 'spuntino_pomeriggio', 'spuntino', percentuale_pietanza, True, controllo_macro_settimanale, ricette, skip_check=True)


def definisci_calorie_macronutrienti():
    """Calcola le calorie e i macronutrienti giornalieri e li restituisce."""

    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """select calorie_giornaliere as kcal , carboidrati , proteine , grassi 
                     from dieta.utenti u limit 1"""

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        rows = cur.fetchone()

    return rows


def stampa_ingredienti_ricetta():
    """
    Recupera gli ingredienti delle ricette dal database e restituisce i dati come lista di dizionari.
    """
    ingredienti = []

    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT r.nome_ricetta, a.nome AS nome_alimento, ir.qta
            FROM dieta.ingredienti_ricetta ir
            JOIN dieta.ricetta r ON (ir.id_ricetta = r.id)
            JOIN dieta.alimento a ON (a.id = ir.id_alimento)
            ORDER BY nome_ricetta
        """

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

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
    lista_della_spesa = []

    with get_db_connection() as conn:
        cur = conn.cursor()
        # Crea una tabella temporanea per l'elaborazione
        query = """
            CREATE TEMP TABLE if not exists temp_ricetta_id (
                id_ricetta BIGINT NOT NULL
            ) ON COMMIT DROP;
            """

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        query = """
            INSERT INTO temp_ricetta_id (id_ricetta)
            VALUES %s
        """

        # Inserisci gli ID delle ricette nella tabella temporanea
        psycopg2.extras.execute_values(cur, query, [(value,) for value in ids_all_food])

        # Recupera la lista degli ingredienti e le quantità totali
        query = """
            SELECT a.nome AS alimento, SUM(ir.qta) AS qta_totale
            FROM dieta.ingredienti_ricetta ir
            JOIN dieta.alimento a ON ir.id_alimento = a.id
            JOIN temp_ricetta_id t ON t.id_ricetta = ir.id_ricetta
            GROUP BY a.nome
            ORDER BY a.nome;
        """

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

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
        giorni_indietro = (oggi.weekday() - 0) % 7
        ultimo_lunedi = oggi - timedelta(days=giorni_indietro)
        domenica_prossima = ultimo_lunedi + timedelta(days=6)

        # Converti tutti i Decimals a float
        menu_convertito = convert_decimal_to_float(menu)

        # Inserisce un nuovo menu per la prossima settimana
        query = """
            INSERT INTO dieta.menu_settimanale (data_inizio, data_fine, menu)
            VALUES (%s, %s, %s)
        """

        params = (ultimo_lunedi.date(), domenica_prossima.date(), Json(menu_convertito))

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        conn.commit()


def salva_menu_settimana_prossima(menu):
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        # Calcola l'inizio e la fine della prossima settimana
        oggi = datetime.now()
        lunedi_prossimo = oggi + timedelta(days=(7 - oggi.weekday()))
        domenica_prossima = lunedi_prossimo + timedelta(days=6)

        lunedi_prossimo = oggi + timedelta(days=(7 - oggi.weekday()))
        domenica_prossima = lunedi_prossimo + timedelta(days=6)

        # Converti tutti i Decimals a float
        menu_convertito = convert_decimal_to_float(menu)

        # Verifica se un menu per la prossima settimana esiste già
        query = """ SELECT id 
                      FROM dieta.menu_settimanale 
                     WHERE data_inizio = %s 
                       AND data_fine = %s
                """

        params = (lunedi_prossimo.date(), domenica_prossima.date())

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        result = cur.fetchone()

        if result:
            # Aggiorna il menu esistente
            query = """
                UPDATE dieta.menu_settimanale
                SET menu = %s
                WHERE id = %s
            """

            params = (Json(menu_convertito), result[0])

            # Stampa la query con parametri
            printer(cur.mogrify(query, params).decode('utf-8'))

            # Recupera il menu per la settimana corrente
            cur.execute(query, params)

        else:
            # Inserisce un nuovo menu per la prossima settimana
            query = """
                INSERT INTO dieta.menu_settimanale (data_inizio, data_fine, menu)
                VALUES (%s, %s, %s)
            """

            params = (lunedi_prossimo.date(), domenica_prossima.date(), Json(menu_convertito))

            # Stampa la query con parametri
            printer(cur.mogrify(query, params).decode('utf-8'))

            # Recupera il menu per la settimana corrente
            cur.execute(query, params)

        conn.commit()


def get_menu_corrente(ids=None):
    menu_corrente = None
    where_cond = "%s between data_inizio AND data_fine "
    oggi = datetime.now()
    params = (oggi.date(),)

    if ids:
        where_cond = "id = %s"
        params = (ids,)

    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()


        query = f"""
            SELECT menu 
              FROM dieta.menu_settimanale
            WHERE {where_cond}
        """


        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

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
            SELECT id 
              FROM dieta.menu_settimanale 
             WHERE data_inizio = %s AND data_fine = %s
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
        oggi = datetime.now()

        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        query = """
            SELECT id, data_inizio, data_fine 
              FROM dieta.menu_settimanale
              WHERE data_fine >= %s
             ORDER BY data_inizio ASC
        """

        params = (oggi.date(),)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        settimane = cur.fetchall()

    return settimane


def save_weight(date, weight):
    # Qui va il codice per salvare i dati nel database
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()

        query = """
            INSERT INTO dieta.registro_peso (data_rilevazione, peso)
            VALUES (%s, %s)
            ON CONFLICT (data_rilevazione) 
            DO UPDATE SET peso = EXCLUDED.peso;
        """

        params = (date, weight)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()

        return get_peso_hist()


def get_peso_hist():
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        query = """select data_rilevazione as date, peso as weight 
                                 from dieta.registro_peso 
                             order by data_rilevazione"""

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        peso = cur.fetchall()

        return peso


def get_menu_settimana(settimana_id):
    menu_selezionato = None
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """ SELECT menu 
                      FROM dieta.menu_settimanale 
                     WHERE id = %s
            """

        params = (settimana_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        result = cur.fetchone()
        if result:
            menu_selezionato = result['menu']

    return menu_selezionato


def get_settimana(macronutrienti):
    ricetta = {'ids': [], 'ricette': []}

    pasto = {'colazione': deepcopy(ricetta),
             'spuntino_mattina': deepcopy(ricetta),
             'pranzo': deepcopy(ricetta),
             'cena': deepcopy(ricetta),
             'spuntino_pomeriggio': deepcopy(ricetta),
             }

    macronutrienti_giornalieri = {
        'carboidrati': Decimal(macronutrienti['carboidrati']),
        'proteine': Decimal(macronutrienti['proteine']),
        'grassi': Decimal(macronutrienti['grassi']),
        'kcal': Decimal(macronutrienti['kcal']),
        'pasto': deepcopy(pasto)
    }

    macronutrienti_settimali = {
        'carboidrati': Decimal(macronutrienti['carboidrati']) * 7,
        'proteine': Decimal(macronutrienti['proteine']) * 7,
        'grassi': Decimal(macronutrienti['grassi']) * 7,
        'kcal': Decimal(macronutrienti['kcal']) * 7
    }

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
            'all_food': []
            }


def salva_ricetta(nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """ UPDATE dieta.ricetta SET nome_ricetta = upper(%s), 
                                             colazione = %s, 
                                             colazione_sec = %s, 
                                             spuntino = %s, 
                                             principale = %s, 
                                             contorno = %s 
                    WHERE id = %s """

        params = (nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def attiva_disattiva_ricetta(ricetta_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "UPDATE dieta.ricetta SET enabled = not enabled WHERE id = %s"

        params = (ricetta_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def get_ricette(recipe_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """SELECT a.id, a.nome, qta, ir.id_ricetta 
                     FROM      dieta.ingredienti_ricetta ir 
                          JOIN dieta.alimento a ON (ir.id_alimento = a.id) 
                    WHERE id_ricetta = %s"""

        params = (recipe_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        ricette = cur.fetchall()

    return ricette


def elimina_ingredienti(ingredient_id, recipe_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "DELETE FROM dieta.ingredienti_ricetta WHERE id_alimento = %s AND id_ricetta = %s"

        params = (ingredient_id, recipe_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def salva_utente_dieta(id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                       meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
                       proteine, grassi):
    with get_db_connection() as conn:
        cur = conn.cursor()

        query = """        
            INSERT INTO dieta.utenti (
                id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, 
                peso_ideale, meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, 
                carboidrati, proteine, grassi
                ) VALUES (    
                     %s, %s, %s, %s, %s,  %s,  %s,  %s,  %s,  %s, 
                     %s,  %s,  %s,  %s,  %s, 
                     %s,  %s,  %s
                )
                ON CONFLICT (id) 
                DO UPDATE SET 
                    nome = EXCLUDED.nome,
                    cognome = EXCLUDED.cognome,
                    sesso = EXCLUDED.sesso,
                    eta = EXCLUDED.eta,
                    altezza = EXCLUDED.altezza,
                    peso = EXCLUDED.peso,
                    tdee = EXCLUDED.tdee,
                    deficit_calorico = EXCLUDED.deficit_calorico,
                    bmi = EXCLUDED.bmi,
                    peso_ideale = EXCLUDED.peso_ideale,
                    meta_basale = EXCLUDED.meta_basale,
                    meta_giornaliero = EXCLUDED.meta_giornaliero,
                    calorie_giornaliere = EXCLUDED.calorie_giornaliere,
                    calorie_settimanali = EXCLUDED.calorie_settimanali,
                    carboidrati = EXCLUDED.carboidrati,
                    proteine = EXCLUDED.proteine,
                    grassi = EXCLUDED.grassi           
            """
        params = (
        id, nome.upper(), cognome.upper(), sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
        meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
        proteine, grassi)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        cur.execute(query, params)
        conn.commit()


def salva_nuova_ricetta(name, breakfast, snack, main, side, second_breakfast):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """INSERT INTO dieta.ricetta (nome_ricetta, colazione, spuntino, principale, contorno, colazione_sec) 
                 VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"""

        params = (name.upper(), breakfast, snack, main, side, second_breakfast)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def salva_ingredienti(recipe_id, ingredient_id, quantity):
    with get_db_connection() as conn:
        cur = conn.cursor()

        query = "SELECT COUNT(*) as cnt FROM dieta.ingredienti_ricetta WHERE id_ricetta = %s AND id_alimento = %s"
        params = (recipe_id, ingredient_id)
        cur.execute(query, params)
        count = cur.fetchone()['cnt']

        if count > 0:
            # Se esiste, esegui un aggiornamento
            query = "UPDATE dieta.ingredienti_ricetta SET qta = %s WHERE id_alimento = %s AND id_ricetta = %s"
        else:
            # Altrimenti, esegui un inserimento
            query = "INSERT INTO dieta.ingredienti_ricetta (qta, id_alimento, id_ricetta) VALUES (%s, %s, %s)"

        params = (quantity, ingredient_id, recipe_id)
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)
        conn.commit()


def recupera_ingredienti():
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "SELECT id, nome FROM dieta.alimento ORDER BY nome;"

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        foods = cur.fetchall()

    return foods


def get_dati_utente():
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """
                SELECT id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, 
                peso_ideale, meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, 
                carboidrati, proteine, grassi 
                FROM dieta.utenti
                limit 1;  
            """

        params = ()

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        row = cur.fetchone()

    return row


def calcola_macronutrienti_rimanenti(menu):
    remaining_macronutrienti = {}
    for giorno, dati_giorno in menu['day'].items():
        remaining_kcal = float(dati_giorno['kcal'])
        remaining_carboidrati = float(dati_giorno['carboidrati'])
        remaining_proteine = float(dati_giorno['proteine'])
        remaining_grassi = float(dati_giorno['grassi'])

        remaining_macronutrienti[giorno] = {
            'kcal': max(remaining_kcal, 0),
            'carboidrati': max(remaining_carboidrati, 0),
            'proteine': max(remaining_proteine, 0),
            'grassi': max(remaining_grassi, 0)
        }
    return remaining_macronutrienti


def recupera_alimenti():
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM dieta.alimento ORDER BY nome;"
        cur.execute(query)
        alimenti = cur.fetchall()
    return alimenti


def salva_alimento(id, nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce):
    with get_db_connection() as conn:
        cur = conn.cursor()
        if id:
            query = """
                UPDATE dieta.alimento
                SET nome = %s, carboidrati = %s, proteine = %s, grassi = %s, frutta = %s, carne_bianca = %s,
                    carne_rossa = %s, pane = %s, verdura = %s, confezionato = %s, vegan = %s, pesce = %s
                WHERE id = %s
            """
            params = (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, id)
        else:
            query = """
                INSERT INTO dieta.alimento (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce)
        cur.execute(query, params)
        conn.commit()


def elimina_alimento(alimento_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "DELETE FROM dieta.alimento WHERE id = %s"
        cur.execute(query, (alimento_id,))
        conn.commit()


def salva_nuovo_alimento(name, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """INSERT INTO dieta.alimento (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce) 
                        VALUES (upper(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

        params = (name, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        alimento_id = cur.fetchone()

        if confezionato:
            cur.execute(
                "INSERT INTO dieta.ricetta (nome_ricetta) VALUES (upper(%s)) RETURNING id",
                (name,))
            ricetta_id = cur.fetchone()
            conn.commit()

            cur.execute(
                "INSERT INTO dieta.ingredienti_ricetta (id_ricetta, id_alimento, qta) VALUES (%s, %s, %s)",
                (ricetta_id['id'], alimento_id['id'], 100))
            conn.commit()

        conn.commit()


def aggiungi_ricetta_al_menu(menu, day, meal, meal_id):
    ricetta = carica_ricette(ids=meal_id)
    menu['day'][day]['pasto'][meal]['ricette'].append({
        'id': ricetta[0]['id'],
        'nome_ricetta': ricetta[0]['nome_ricetta'],
        'qta': 1,
        'ricetta': ricetta[0]['ricetta'],
        'kcal':ricetta[0]['kcal'],
        'carboidrati': ricetta[0]['carboidrati'],
        'grassi': ricetta[0]['grassi'],
        'proteine': ricetta[0]['proteine']
    })

    # Aggiorna i macronutrienti per il giorno
    menu['day'][day]['kcal'] -= float(ricetta[0]['kcal'])
    menu['day'][day]['carboidrati'] -= float(ricetta[0]['carboidrati'])
    menu['day'][day]['proteine'] -= float(ricetta[0]['proteine'])
    menu['day'][day]['grassi'] -= float(ricetta[0]['grassi'])

    # Aggiorna i macronutrienti settimanali
    menu['weekly']['kcal'] -= float(ricetta[0]['kcal'])
    menu['weekly']['carboidrati'] -= float(ricetta[0]['carboidrati'])
    menu['weekly']['proteine'] -= float(ricetta[0]['proteine'])
    menu['weekly']['grassi'] -= float(ricetta[0]['grassi'])


def update_menu_corrente(menu, week_id):
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()

        # Converti tutti i Decimals a float
        menu_convertito = convert_decimal_to_float(menu)

        # Inserisce un nuovo menu per la prossima settimana
        query = """
            UPDATE dieta.menu_settimanale set menu = %s 
            where id = %s
        """

        params = (Json(menu_convertito), week_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        conn.commit()

def remove_meal_from_menu(menu, day, meal, meal_id):
    # Trova la ricetta da rimuovere
    ricetta_da_rimuovere = None
    for ricetta in menu['day'][day]['pasto'][meal]['ricette']:
        print(f"ricetta-id::{ricetta['id']}")
        print(f"meal_id::{meal_id}")
        if int(ricetta['id']) == int(meal_id):
            print("dentro")
            ricetta_da_rimuovere = ricetta
            print(f"ricetta_da_rimuovere::{ricetta_da_rimuovere}")
            break

    # Se la ricetta è trovata, rimuovila
    if ricetta_da_rimuovere:
        menu['day'][day]['pasto'][meal]['ricette'].remove(ricetta_da_rimuovere)

        # Recupera i valori nutrizionali della ricetta rimossa
        ricetta_valori = carica_ricette(ids=meal_id)

        # Aggiorna i macronutrienti per il giorno
        menu['day'][day]['kcal'] += float(ricetta_valori[0]['kcal'])
        menu['day'][day]['carboidrati'] += float(ricetta_valori[0]['carboidrati'])
        menu['day'][day]['proteine'] += float(ricetta_valori[0]['proteine'])
        menu['day'][day]['grassi'] += float(ricetta_valori[0]['grassi'])

        # Aggiorna i macronutrienti settimanali
        menu['weekly']['kcal'] += float(ricetta_valori[0]['kcal'])
        menu['weekly']['carboidrati'] += float(ricetta_valori[0]['carboidrati'])
        menu['weekly']['proteine'] += float(ricetta_valori[0]['proteine'])
        menu['weekly']['grassi'] += float(ricetta_valori[0]['grassi'])

    return menu
