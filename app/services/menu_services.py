import os
import random
import psycopg2.extras
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timedelta
from flask import current_app
from app.models.database import get_db_connection
from app.models.common import printer
from copy import deepcopy
from decimal import Decimal
import re

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


def select_food(ricette, settimana, giorno_settimana, pasto, max_retry, perc, ripetibile, found, controllo_macro_settimanale, skip_check):
    ids_disponibili = [oggetto['id'] for oggetto in ricette if oggetto['id'] not in settimana['all_food']] if not ripetibile else [oggetto['id'] for oggetto in ricette if oggetto['id'] not in settimana['day'][giorno_settimana]['pasto'][pasto]['ids']]

    ricette_filtrate = [ricetta for ricetta in ricette if ricetta['id'] in ids_disponibili and (skip_check or check_macronutrienti(ricetta, settimana['day'][giorno_settimana], settimana['weekly'], controllo_macro_settimanale))]

    if not ricette_filtrate:
        return found

    id_selezionato = random.choice(ricette_filtrate)['id']
    ricetta_selezionata = next(oggetto for oggetto in ricette if oggetto['id'] == id_selezionato)

    mt = settimana.get('day').get(giorno_settimana).get('pasto').get(pasto)
    day = settimana.get('day').get(giorno_settimana)
    macronutrienti_settimali = settimana.get('weekly')
    if (skip_check or check_macronutrienti(ricetta_selezionata, settimana['day'][giorno_settimana], settimana['weekly'], controllo_macro_settimanale)):
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
        select_food(ricette, settimana, giorno_settimana, pasto, max_retry, perc, ripetibile, False, controllo_macro_settimanale, skip_check)

    return found


def check_macronutrienti(ricetta, day, weekly, controllo_macro_settimanale):
    return ((
            (day['kcal'] - ricetta['kcal']) > 0 and
            (day['carboidrati'] - ricetta['carboidrati']) > 0 and
            (day['proteine'] - ricetta['proteine']) > 0 and
            (day['grassi'] - ricetta['grassi']) > 0
           ) or
           (controllo_macro_settimanale and
            (weekly['kcal'] - ricetta['kcal']) > 0 and
            (weekly['carboidrati'] - ricetta['carboidrati']) > 0 and
            (weekly['proteine'] - ricetta['proteine']) > 0 and
            (weekly['grassi'] - ricetta['grassi']) > 0)
            )


def carica_ricette(user_id, ids=None, stagionalita: bool=False, attive:bool=False):
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
    r.user_id,
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
    LEFT JOIN dieta.alimento a ON ir.id_alimento = a.id AND ir.user_id = a.user_id
    where ir.user_id = %s
    GROUP BY ir.id_ricetta
) i ON r.id = i.id_ricetta
LEFT JOIN dieta.ingredienti_ricetta ir ON ir.id_ricetta = r.id and ir.user_id = r.user_id
LEFT JOIN dieta.alimento a ON ir.id_alimento = a.id and ir.user_id = a.user_id
where 1=1
and r.user_id = %s {and_stagionalita} {and_ids} {and_attive}
GROUP BY r.user_id, r.id, r.nome_ricetta,carboidrati, proteine, grassi, qta, r.colazione, r.spuntino, r.principale, r.contorno, r.colazione_sec, r.enabled, i.ricetta
 order by enabled desc, r.nome_ricetta

        """
        params = (user_id,user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        ricette = cur.fetchall()

    return ricette


def genera_menu(settimana, controllo_macro_settimanale: bool, ricette) -> None:
    #percentuali = [1, 0.5, 0.75]
    percentuali = [1, 1.2, 1.1, 0.9, 0.8, 0.5]
    id_pane = 272

    for giorno in settimana['day']:
        for percentuale_pietanza in percentuali:
            for _ in range(MAX_RETRY):
                p = settimana['day'][giorno]['pasto']

                if len(p['pranzo']['ricette']) < 5:
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


def definisci_calorie_macronutrienti(user_id):
    """Calcola le calorie e i macronutrienti giornalieri e li restituisce."""

    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """select calorie_giornaliere as kcal , carboidrati , proteine , grassi 
                     from dieta.utenti u where id = %s """

        params = (user_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        rows = cur.fetchone()

    return rows


def stampa_lista_della_spesa(user_id, ids_all_food: list):
    """
    Recupera la lista della spesa basata sugli ID degli alimenti e restituisce i dati come lista di dizionari.
    """
    lista_della_spesa = []

    with get_db_connection() as conn:
        cur = conn.cursor()
        # Crea una tabella temporanea per l'elaborazione
        query = """
            CREATE TEMP TABLE IF NOT EXISTS temp_ricetta_id (
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
            JOIN dieta.alimento a ON (ir.id_alimento = a.id and ir.user_id = a.user_id)
            JOIN temp_ricetta_id t ON (t.id_ricetta = ir.id_ricetta)
            WHERE ir.user_id = %s
            GROUP BY a.nome
            ORDER BY a.nome;
        """

        params = (user_id, )

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        rows = cur.fetchall()

        conn.commit()

        for row in rows:
            lista_della_spesa.append({
                'alimento': row['alimento'],
                'qta_totale': int(row['qta_totale'])
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


def salva_menu_corrente(menu, user_id):
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
            INSERT INTO dieta.menu_settimanale (data_inizio, data_fine, menu, user_id)
            VALUES (%s, %s, %s, %s)
        """

        params = (ultimo_lunedi.date(), domenica_prossima.date(), Json(menu_convertito), user_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        conn.commit()


def salva_menu_settimana_prossima(menu, user_id):
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
                       and user_id = %s
                """

        params = (lunedi_prossimo.date(), domenica_prossima.date(), user_id)

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
                  AND user_id = %s
            """

            params = (Json(menu_convertito), result[0], user_id)

            # Stampa la query con parametri
            printer(cur.mogrify(query, params).decode('utf-8'))

            # Recupera il menu per la settimana corrente
            cur.execute(query, params)

        else:
            # Inserisce un nuovo menu per la prossima settimana
            query = """
                INSERT INTO dieta.menu_settimanale (data_inizio, data_fine, menu, user_id)
                VALUES (%s, %s, %s, %s)
            """

            params = (lunedi_prossimo.date(), domenica_prossima.date(), Json(menu_convertito), user_id)

            # Stampa la query con parametri
            printer(cur.mogrify(query, params).decode('utf-8'))

            # Recupera il menu per la settimana corrente
            cur.execute(query, params)

        conn.commit()


def get_menu_corrente(user_id, ids=None):
    menu_corrente = None
    where_cond = "and %s between data_inizio AND data_fine "
    oggi = datetime.now()
    params = (user_id, oggi.date())

    if ids:
        where_cond = "and id = %s"
        params = (user_id, ids,)

    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()

        query = f"""
            SELECT menu 
              FROM dieta.menu_settimanale
             WHERE user_id = %s {where_cond}
        """

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)
        result = cur.fetchone()

        if result:
            menu_corrente = result['menu']

    return menu_corrente


def get_menu_settima_prossima(user_id):
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
               and user_id = %s
        """

        params = (lunedi_prossimo.date(), domenica_prossima.date(), user_id)

        # Verifica se un menu per la prossima settimana esiste già
        cur.execute(query, params)
        result = cur.fetchone()

        if result:
            return True

    return False


def get_settimane_salvate(user_id):
    with get_db_connection() as conn:
        oggi = datetime.now()

        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        query = """
            SELECT id, data_inizio, data_fine 
              FROM dieta.menu_settimanale
              WHERE data_fine >= %s
               and user_id = %s
             ORDER BY data_inizio ASC
        """

        params = (oggi.date(), user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        settimane = cur.fetchall()

    return settimane


def save_weight(date, weight, user_id):
    # Qui va il codice per salvare i dati nel database
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()

        query = """
            INSERT INTO dieta.registro_peso (data_rilevazione, peso, user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (data_rilevazione, user_id) 
            DO UPDATE SET peso = EXCLUDED.peso;
        """

        params = (date, weight, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()

        return get_peso_hist(user_id)


def get_peso_hist(user_id):
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        query = """select data_rilevazione as date, peso as weight 
                                 from dieta.registro_peso 
                                 where user_id = %s
                             order by data_rilevazione"""

        params = (user_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        peso = cur.fetchall()

        return peso


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


def salva_ricetta(nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """ UPDATE dieta.ricetta SET nome_ricetta = upper(%s), 
                                             colazione = %s, 
                                             colazione_sec = %s, 
                                             spuntino = %s, 
                                             principale = %s, 
                                             contorno = %s 
                    WHERE id = %s 
                      and user_id = %s """

        params = (nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def attiva_o_disattiva_ricetta(ricetta_id, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """UPDATE dieta.ricetta 
                      SET enabled = not enabled 
                    WHERE id = %s 
                      AND user_id = %s"""

        params = (ricetta_id, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def get_ricette(recipe_id, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """SELECT a.id, a.nome, qta, ir.id_ricetta 
                     FROM      dieta.ingredienti_ricetta ir 
                          JOIN dieta.alimento a ON (ir.id_alimento = a.id AND ir.user_id = a.user_id) 
                    WHERE ir.id_ricetta = %s
                      AND ir.user_id = %s"""

        params = (recipe_id, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        ricette = cur.fetchall()

    return ricette


def elimina_ingredienti(ingredient_id, recipe_id, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """DELETE 
                     FROM dieta.ingredienti_ricetta 
                    WHERE id_alimento = %s 
                      AND id_ricetta = %s 
                      AND user_id = %s"""

        params = (ingredient_id, recipe_id, user_id)

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


def salva_nuova_ricetta(name, breakfast, snack, main, side, second_breakfast, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """INSERT INTO dieta.ricetta (nome_ricetta, colazione, spuntino, principale, contorno, colazione_sec, user_id) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id"""

        params = (name.upper(), breakfast, snack, main, side, second_breakfast, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def salva_ingredienti(recipe_id, ingredient_id, quantity, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()

        query = "SELECT COUNT(*) as cnt FROM dieta.ingredienti_ricetta WHERE id_ricetta = %s AND id_alimento = %s and user_id = %s"
        params = (recipe_id, ingredient_id, user_id)
        cur.execute(query, params)
        count = cur.fetchone()['cnt']

        if count > 0:
            # Se esiste, esegui un aggiornamento
            query = "UPDATE dieta.ingredienti_ricetta SET qta = %s WHERE id_alimento = %s AND id_ricetta = %s AND user_id = %s"
        else:
            # Altrimenti, esegui un inserimento
            query = "INSERT INTO dieta.ingredienti_ricetta (qta, id_alimento, id_ricetta, user_id) VALUES (%s, %s, %s, %s)"

        params = (quantity, ingredient_id, recipe_id, user_id)
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)
        conn.commit()


def recupera_ingredienti(user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """SELECT id, nome 
                     FROM dieta.alimento 
                    WHERE user_id = %s
                    ORDER BY nome;"""

        params = (user_id, )

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        foods = cur.fetchall()

    return foods


def get_dati_utente(user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """
                SELECT id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, 
                peso_ideale, meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, 
                carboidrati, proteine, grassi, email
                FROM dieta.utenti
                where id = %s;
            """

        params = (user_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        row = cur.fetchone()

    return row


def calcola_macronutrienti_rimanenti(menu):
    remaining_macronutrienti = {}
    if menu:
        for giorno, dati_giorno in menu['day'].items():
            remaining_kcal = round(float(dati_giorno['kcal']),2)
            remaining_carboidrati = round(float(dati_giorno['carboidrati']),2)
            remaining_proteine = round(float(dati_giorno['proteine']),2)
            remaining_grassi = round(float(dati_giorno['grassi']),2)

            remaining_macronutrienti[giorno] = {
                'kcal': remaining_kcal,
                'carboidrati': remaining_carboidrati,
                'proteine': remaining_proteine,
                'grassi': remaining_grassi
            }
    return remaining_macronutrienti


def carica_alimenti(user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """SELECT id, nome, carboidrati, proteine, grassi, kcal, macro, frutta, 
                          carne_bianca, carne_rossa, pane, stagionalita, verdura, 
                          confezionato, vegan, pesce, user_id
                     FROM dieta.alimento
                     where user_id = %s 
                    ORDER BY nome;"""
        params = (user_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        alimenti = cur.fetchall()
    return alimenti


def salva_alimento(id, nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        if id:
            query = """
                UPDATE dieta.alimento
                SET nome = %s, carboidrati = %s, proteine = %s, grassi = %s, frutta = %s, carne_bianca = %s,
                    carne_rossa = %s, pane = %s, verdura = %s, confezionato = %s, vegan = %s, pesce = %s
                WHERE id = %s
                  AND user_id = %s
            """
            params = (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, id, user_id)
        else:
            query = """
                INSERT INTO dieta.alimento (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, 
                                            pane, verdura, confezionato, vegan, pesce, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)
        conn.commit()


def elimina_alimento(alimento_id, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """DELETE 
                     FROM dieta.alimento 
                    WHERE id = %s 
                    AND user_id = %s"""

        params = (alimento_id, user_id,)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)
        conn.commit()


def salva_nuovo_alimento(name, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """INSERT INTO dieta.alimento (nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, user_id) 
                        VALUES (upper(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

        params = (name, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        alimento_id = cur.fetchone()

        if confezionato:
            query = """INSERT INTO dieta.ricetta (nome_ricetta, user_id) VALUES (upper(%s), %s) RETURNING id"""
            params = (name, user_id)

            printer(cur.mogrify(query, params).decode('utf-8'))
            cur.execute(query, params)

            ricetta_id = cur.fetchone()

            query = """INSERT INTO dieta.ingredienti_ricetta (id_ricetta, id_alimento, qta, user_id) VALUES (%s, %s, %s, %s)"""
            params = (ricetta_id['id'], alimento_id['id'], 100, user_id)

            printer(cur.mogrify(query, params).decode('utf-8'))
            cur.execute(query, params)

        conn.commit()


def aggiungi_ricetta_al_menu(menu, day, meal, meal_id, user_id):
    ricetta = carica_ricette(user_id, ids=meal_id)
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


def update_menu_corrente(menu, week_id, user_id):
    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()

        # Converti tutti i Decimals a float
        menu_convertito = convert_decimal_to_float(menu)

        # Inserisce un nuovo menu per la prossima settimana
        query = """
            UPDATE dieta.menu_settimanale 
               SET menu = %s 
             WHERE id = %s
               AND user_id = %s
        """

        params = (Json(menu_convertito), week_id, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)

        conn.commit()

def remove_meal_from_menu(menu, day, meal, meal_id, user_id):
    # Trova la ricetta da rimuovere
    ricetta_da_rimuovere = None
    for ricetta in menu['day'][day]['pasto'][meal]['ricette']:
        qta = ricetta['qta']
        if int(ricetta['id']) == int(meal_id):
            ricetta_da_rimuovere = ricetta
            break

    # Se la ricetta è trovata, rimuovila
    if ricetta_da_rimuovere:
        menu['day'][day]['pasto'][meal]['ricette'].remove(ricetta_da_rimuovere)

        # Recupera i valori nutrizionali della ricetta rimossa
        ricetta_valori = carica_ricette(user_id, ids=meal_id)

        # Aggiorna i macronutrienti per il giorno
        menu['day'][day]['kcal'] += float(ricetta_valori[0]['kcal']) * float(qta)
        menu['day'][day]['carboidrati'] += float(ricetta_valori[0]['carboidrati']) * float(qta)
        menu['day'][day]['proteine'] += float(ricetta_valori[0]['proteine']) * float(qta)
        menu['day'][day]['grassi'] += float(ricetta_valori[0]['grassi']) * float(qta)

        # Aggiorna i macronutrienti settimanali
        menu['weekly']['kcal'] += float(ricetta_valori[0]['kcal'])  * float(qta)
        menu['weekly']['carboidrati'] += float(ricetta_valori[0]['carboidrati'])  * float(qta)
        menu['weekly']['proteine'] += float(ricetta_valori[0]['proteine'])  * float(qta)
        menu['weekly']['grassi'] += float(ricetta_valori[0]['grassi'])  * float(qta)

    return menu


def delete_week_menu(week_id, user_id):
    with get_db_connection() as conn:

        # Esegui le operazioni con la connessione
        cur = conn.cursor()

        # Inserisce un nuovo menu per la prossima settimana
        query = """ DELETE FROM dieta.menu_settimanale 
                     WHERE id = %s 
                       AND user_id = %s"""
        params = (week_id, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        # Recupera il menu per la settimana corrente
        cur.execute(query, params)
        conn.commit()


def is_valid_email(email):
    # Definizione dell'espressione regolare per validare l'email
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

    # Utilizzo di re.match per verificare se l'email è valida
    if re.match(email_regex, email):
        return True
    else:
        return False


def copia_alimenti_ricette(user_id, ricette_vegane, ricette_carne, ricette_pesce):
    with get_db_connection() as conn:
        cur = conn.cursor()

        params = (int(user_id),)

        query = """insert into dieta.alimento(id, nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, stagionalita, verdura, confezionato, vegan, pesce, user_id)
                    SELECT distinct id, nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, stagionalita, verdura, confezionato, vegan, pesce, %s
                    FROM dieta.alimento_base"""
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        query = """insert into dieta.ricetta(id, nome_ricetta, colazione, spuntino, principale, contorno, enabled, colazione_sec, user_id)
                   SELECT id, nome_ricetta, colazione, spuntino, principale, contorno, false, colazione_sec, %s
                     FROM dieta.ricetta_base"""
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        query = """ insert into dieta.ingredienti_ricetta (id_ricetta, id_alimento, qta, user_id)
                    SELECT id_ricetta, id_alimento, qta, %s
                      FROM dieta.ingredienti_ricetta_base"""
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        if ricette_vegane:
            query = """WITH ricette_vegane AS (SELECT distinct r.id
                                                 FROM dieta.ricetta_base r
                                                JOIN dieta.ingredienti_ricetta_base ir ON r.id = ir.id_ricetta 
                                                JOIN dieta.alimento_base a ON ir.id_alimento = a.id
                                                GROUP BY r.id, r.nome_ricetta
                                                HAVING COUNT(*) = SUM(CASE WHEN a.vegan = true THEN 1 ELSE 0 END)
                                                ) 
                    update dieta.ricetta r set enabled = true
                      from ricette_vegane rv
                      where rv.id = r.id
                        and r.user_id = %s"""
        else:
            if ricette_carne and ricette_pesce:
                query = """update dieta.ricetta r set enabled = true
                            where r.user_id = %s"""

            elif ricette_carne and not ricette_pesce:
                query = """with ricette_no_pesce as (SELECT distinct r.id
                                                    FROM dieta.ricetta_base r
                                                    JOIN dieta.ingredienti_ricetta_base ir ON r.id = ir.id_ricetta
                                                    JOIN dieta.alimento_base a ON ir.id_alimento = a.id
                                                    WHERE NOT EXISTS (
                                                        SELECT 1
                                                        FROM dieta.ingredienti_ricetta_base ir_sub
                                                        JOIN dieta.alimento_base a_sub ON ir_sub.id_alimento = a_sub.id
                                                        WHERE ir_sub.id_ricetta = r.id
                                                          and a_sub.pesce
                                                    ))
                            update dieta.ricetta r set enabled = true
                              from ricette_no_pesce rv
                              where rv.id = r.id
                                and r.user_id = %s"""

            elif not ricette_carne and ricette_pesce:
                query = """with ricette_no_carne as (SELECT distinct r.id
                                                    FROM dieta.ricetta_base r
                                                    JOIN dieta.ingredienti_ricetta_base ir ON r.id = ir.id_ricetta
                                                    JOIN dieta.alimento_base a ON ir.id_alimento = a.id
                                                    WHERE NOT EXISTS (
                                                        SELECT 1
                                                        FROM dieta.ingredienti_ricetta_base ir_sub
                                                        JOIN dieta.alimento_base a_sub ON ir_sub.id_alimento = a_sub.id
                                                        WHERE ir_sub.id_ricetta = r.id
                                                          AND (a_sub.carne_bianca OR a_sub.carne_rossa )
                                                    ))
                            update dieta.ricetta r set enabled = true
                              from ricette_no_carne rv
                              where rv.id = r.id
                                and r.user_id = %s"""

        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)
        conn.commit()


def elimina_ricetta(ricetta_id, user_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """DELETE FROM dieta.ricetta                       
                    WHERE id = %s 
                      AND user_id = %s"""

        params = (ricetta_id, user_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()
