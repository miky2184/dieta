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
                    controllo_macro_settimanale: bool, ricette, ids_specifici=None):
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
                'contorno': ricetta['contorno']
            }
            ricette_modificate.append(ricetta_modificata)

    # Invoca select_food con le ricette modificate
    return select_food(ricette_modificate, settimana, giorno_settimana, pasto, MAX_RETRY, percentuale_pietanza, ripetibile,
                       False, controllo_macro_settimanale)


def select_food(rows, settimana, giorno_settimana, pasto, max_retry, perc: float, ripetibile: bool, found: bool,
                controllo_macro_settimanale: bool):
    if not ripetibile:
        ids_disponibili = [oggetto['id'] for oggetto in rows if oggetto['id'] not in settimana['all_food']]
    else:
        ids_disponibili = [oggetto['id'] for oggetto in rows if
                           oggetto['id'] not in settimana.get('day').get(giorno_settimana).get('pasto').get(
                               pasto).get('ids')]

    if ids_disponibili and max_retry > 0:
        # Seleziona casualmente un ID dalla lista dei disponibili
        id_selezionato = random.choice(ids_disponibili)
        max_retry = max_retry - 1

        # Trova l'oggetto corrispondente all'ID selezionato
        ricetta_selezionata = next(oggetto for oggetto in rows if oggetto['id'] == id_selezionato)

        mt = settimana.get('day').get(giorno_settimana).get('pasto').get(pasto)
        day = settimana.get('day').get(giorno_settimana)
        macronutrienti_settimali = settimana.get('weekly')
        if (
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
            r = {'qta': perc, 'nome_ricetta': ricetta_selezionata.get('nome_ricetta')}
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
            select_food(rows, settimana, giorno_settimana, pasto, max_retry, perc, ripetibile, False, controllo_macro_settimanale)

    return found


def carica_ricette(stagionalita: bool):
    """
    Carica tutte le ricette disponibili dal database in memoria.
    """
    and_stagionalita = ""
    if stagionalita:
        and_stagionalita = "AND (frutta AND extract(month FROM current_date) = ANY(stagionalita) OR NOT frutta)"

    with get_db_connection() as conn:
        cur = conn.cursor()
        query = f"""
            SELECT distinct r.id, r.nome_ricetta,
                ceil(sum((carboidrati/100*qta*4)+
                         (proteine/100*qta*4)+
                        (grassi/100*qta*9)) over (partition by ir.id_ricetta)) as kcal,
                round(sum(carboidrati/100*qta) over (partition by ir.id_ricetta), 2) as carboidrati,
                round(sum(proteine/100*qta) over (partition by ir.id_ricetta), 2) as proteine,
                round(sum(grassi/100*qta) over (partition by ir.id_ricetta), 2) as grassi,
                r.colazione, r.spuntino, r.principale, r.contorno, r.colazione_sec, r.enabled as attiva
            FROM dieta.ricetta r
            left JOIN dieta.ingredienti_ricetta ir ON (ir.id_ricetta = r.id)
            left JOIN dieta.alimento a ON (ir.id_alimento = a.id)
            WHERE 1=1
            {and_stagionalita}                  
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

                if len(p['pranzo']['ricette']) < 1:
                    scegli_pietanza(settimana, giorno, 'pranzo', 'principale', percentuale_pietanza, False, controllo_macro_settimanale, ricette)
                if len(p['cena']['ricette']) < 1:
                    scegli_pietanza(settimana, giorno, 'cena', 'principale', percentuale_pietanza, False, controllo_macro_settimanale, ricette)
                if len(p['colazione']['ricette']) < 2:
                    scegli_pietanza(settimana, giorno, 'colazione', 'colazione', percentuale_pietanza, True, controllo_macro_settimanale, ricette)
                    scegli_pietanza(settimana, giorno, 'colazione', 'colazione_sec', percentuale_pietanza, True, controllo_macro_settimanale, ricette)
                    # Aggiungi il pane sia a pranzo che a cena
                scegli_pietanza(settimana, giorno, 'pranzo', 'contorno', 1, False, controllo_macro_settimanale, ricette, ids_specifici=[id_pane])
                scegli_pietanza(settimana, giorno, 'cena', 'contorno', 1, False, controllo_macro_settimanale, ricette, ids_specifici=[id_pane])
                scegli_pietanza(settimana, giorno, 'pranzo', 'contorno', percentuale_pietanza, True, controllo_macro_settimanale, ricette)
                scegli_pietanza(settimana, giorno, 'cena', 'contorno', percentuale_pietanza, True, controllo_macro_settimanale, ricette)
                if len(p['spuntino_mattina']['ricette']) < 1:
                    scegli_pietanza(settimana, giorno, 'spuntino_mattina', 'spuntino', percentuale_pietanza, True, controllo_macro_settimanale, ricette)
                if len(p['spuntino_pomeriggio']['ricette']) < 1:
                    scegli_pietanza(settimana, giorno, 'spuntino_pomeriggio', 'spuntino', percentuale_pietanza, True, controllo_macro_settimanale, ricette)


def definisci_calorie_macronutrienti():
    """Calcola le calorie e i macronutrienti giornalieri e li restituisce."""

    with get_db_connection() as conn:
        cur = conn.cursor()
        query = """select calorie_giornaliere as kcal , carboidrati , proteine , grassi 
                     from dieta.utenti u """

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


def get_menu_corrente():
    menu_corrente = None

    with get_db_connection() as conn:
        # Esegui le operazioni con la connessione
        cur = conn.cursor()
        oggi = datetime.now()

        query = """
            SELECT menu 
              FROM dieta.menu_settimanale
            WHERE %s between data_inizio AND data_fine 
        """
        params = (oggi.date(),)

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


def aggiorna_ingredienti(recipe_id, ingredient_id, quantity):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "UPDATE dieta.ingredienti_ricetta SET qta = %s WHERE id_alimento = %s AND id_ricetta = %s"

        params = (quantity, ingredient_id, recipe_id)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))
        cur.execute(query, params)

        conn.commit()


def aggiungi_ingredienti(recipe_id, ingredient_id, quantity):
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = "INSERT INTO dieta.ingredienti_ricetta (id_ricetta, id_alimento, qta) VALUES (%s, %s, %s)"

        params = (recipe_id, ingredient_id, quantity)

        # Stampa la query con parametri
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
