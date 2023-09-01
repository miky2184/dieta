import os
import random
import time
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal

import gspread
import psycopg2.extras
import requests
import schedule
import simplejson
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread_formatting import set_column_width, set_data_validation_for_cell_range, DataValidationRule, \
    BooleanCondition
from tqdm import tqdm

from db import connect_to_db

# Carica le variabili d'ambiente dal file .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_CHAT_ID = os.getenv("USER_CHAT_ID")
GS_URL = os.getenv("GS_URL")
MAX_KCAL = int(os.getenv("MAX_KCAL"))
CARBOIDRATI_MAX_GIORNALIERI = float(os.getenv("CARBOIDRATI_MAX_GIORNALIERI"))
PROTEINE_MAX_GIORNALIERI = float(os.getenv("PROTEINE_MAX_GIORNALIERI"))
GRASSI_MAX_GIORNALIERI = float(os.getenv("GRASSI_MAX_GIORNALIERI"))
MAX_RETRY = int(os.getenv("MAX_RETRY"))
WIDTH_COLS_QTA = int(os.getenv("WIDTH_COLS_QTA"))
SLEEP_TIME = int(os.getenv("SLEEP_TIME", 20))
SA = os.getenv("SA")
DEV_MODE = os.getenv("DEV_MODE", "N")
EXEC_DAY = int(os.getenv("EXEC_DAY", 4))
EXEC_HOUR = os.getenv("EXEC_HOUR", "10:00")

ricetta = {"ids": [], "ricette": []}

pasto = {"colazione": deepcopy(ricetta),
         "spuntino": deepcopy(ricetta),
         "pranzo": deepcopy(ricetta),
         "cena": deepcopy(ricetta)
         }

daily = {
    "carboidrati": Decimal(CARBOIDRATI_MAX_GIORNALIERI),
    "proteine": Decimal(PROTEINE_MAX_GIORNALIERI),
    "grassi": Decimal(GRASSI_MAX_GIORNALIERI),
    "kcal": Decimal(MAX_KCAL),
    "pasto": deepcopy(pasto)
}

weekly = {
    "carboidrati": Decimal(CARBOIDRATI_MAX_GIORNALIERI) * 7,
    "proteine": Decimal(PROTEINE_MAX_GIORNALIERI) * 7,
    "grassi": Decimal(GRASSI_MAX_GIORNALIERI) * 7,
    "kcal": Decimal(MAX_KCAL) * 7
}

settimana = {"weekly": weekly,
             "day": {
                 "lunedi": deepcopy(daily),
                 "martedi": deepcopy(daily),
                 "mercoledi": deepcopy(daily),
                 "giovedi": deepcopy(daily),
                 "venerdi": deepcopy(daily),
                 "sabato": deepcopy(daily),
                 "domenica": deepcopy(daily)
             },
             "all_food": []
             }

# Definisci i diritti di accesso
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/spreadsheets']

# Carica le credenziali e inizializza l'autenticazione
credentials = Credentials.from_service_account_file(SA, scopes=scope)
client = gspread.authorize(credentials)

# Apri un foglio di calcolo esistente utilizzando il suo URL o il suo titolo
spreadsheet = client.open_by_url(GS_URL)


def __scegli_pietanza__(giorno_settimana: str, meal_time: str, tipo: str, perc: float, disponibili: bool,
                        weekly_check: bool):
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                             select distinct r.id, r.nome_ricetta ,
                                ceil(sum((carboidrati/100*qta*4)+(proteine/100*qta*4)+(grassi/100*qta*9)) over (partition by ir.id_ricetta)) * %s as kcal,
                                round(sum(carboidrati/100*qta) over (partition by ir.id_ricetta),2) * %s as carboidrati,
                                round(sum(proteine/100*qta) over (partition by ir.id_ricetta),2) * %s as proteine,
                                round(sum(grassi/100*qta) over (partition by ir.id_ricetta),2) * %s as grassi,
                                r.colazione , r.spuntino , r.principale , r.contorno 
                                from dieta.ingredienti_ricetta ir 
                                join dieta.ricetta r on (ir.id_ricetta = r.id)
                                join dieta.alimento a on (ir.id_alimento = a.id)
                                where {tipo}
                                  and r.enabled
                                  and (frutta and extract(month from current_date) = any(stagionalita) or stagionalita is null or not frutta)                               
                        """, (perc, perc, perc, perc))
            rows = cur.fetchall()
            max_retry = 900
            return __select_food__(rows, giorno_settimana, meal_time, max_retry, perc, disponibili, False, weekly_check)

    finally:
        if conn is not None:
            conn.close()


def __select_food__(rows, giorno_settimana, meal_time, max_retry, perc: float, disponibili: bool, found: bool,
                    weekly_check: bool):
    if disponibili:
        ids_disponibili = [oggetto["id"] for oggetto in rows if oggetto["id"] not in settimana["all_food"]]
    else:
        ids_disponibili = [oggetto["id"] for oggetto in rows if
                           oggetto["id"] not in settimana.get("day").get(giorno_settimana).get("pasto").get(
                               meal_time).get("ids")]

    if ids_disponibili and max_retry > 0:
        # Seleziona casualmente un ID dalla lista dei disponibili
        id_selezionato = random.choice(ids_disponibili)
        max_retry = max_retry - 1

        # Trova l'oggetto corrispondente all'ID selezionato
        ricetta_selezionata = next(oggetto for oggetto in rows if oggetto["id"] == id_selezionato)

        mt = settimana.get("day").get(giorno_settimana).get("pasto").get(meal_time)
        day = settimana.get("day").get(giorno_settimana)
        weekly_nut = settimana.get("weekly")
        if (
                ((day.get("kcal") - ricetta_selezionata.get("kcal")) > 0 and
                 (day.get("carboidrati") - ricetta_selezionata.get("carboidrati")) > 0 and
                 (day.get("proteine") - ricetta_selezionata.get("proteine")) > 0 and
                 (day.get("grassi") - ricetta_selezionata.get("grassi")) > 0) or (weekly_check and
                                                                                  (weekly_nut.get(
                                                                                      "kcal") - ricetta_selezionata.get(
                                                                                      "kcal") > 0 and
                                                                                   (weekly_nut.get(
                                                                                       "carboidrati") - ricetta_selezionata.get(
                                                                                       "carboidrati")) > 0 and
                                                                                   (weekly_nut.get(
                                                                                       "proteine") - ricetta_selezionata.get(
                                                                                       "proteine")) > 0 and
                                                                                   (weekly_nut.get(
                                                                                       "grassi") - ricetta_selezionata.get(
                                                                                       "grassi")) > 0))
        ):
            settimana.get("all_food").append(id_selezionato)
            mt.get("ids").append(id_selezionato)
            r = {"qta": perc, "nome_ricetta": ricetta_selezionata.get("nome_ricetta")}
            mt.get("ricette").append(r)
            day["kcal"] = day.get("kcal") - ricetta_selezionata.get("kcal")
            day["carboidrati"] = day.get("carboidrati") - ricetta_selezionata.get("carboidrati")
            day["proteine"] = day.get("proteine") - ricetta_selezionata.get("proteine")
            day["grassi"] = day.get("grassi") - ricetta_selezionata.get("grassi")
            weekly_nut["kcal"] = weekly_nut.get("kcal") - ricetta_selezionata.get("kcal")
            weekly_nut["carboidrati"] = weekly_nut.get("carboidrati") - ricetta_selezionata.get("carboidrati")
            weekly_nut["proteine"] = weekly_nut.get("proteine") - ricetta_selezionata.get("proteine")
            weekly_nut["grassi"] = weekly_nut.get("grassi") - ricetta_selezionata.get("grassi")
            found = True
        else:
            __select_food__(rows, giorno_settimana, meal_time, max_retry, perc, disponibili, False, weekly_check)

    return found


def __send_telegram_message__(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={USER_CHAT_ID}&text={message}"
    print(requests.get(url).json())  # this sends the message


def __crea_menu__():
    __genera_menu__(False)
    __genera_menu__(True)


def __genera_menu__(check_weekly: bool) -> None:
    percentuali = [1, 0.75, 0.5]
    total_iterations = len(percentuali) * MAX_RETRY * len(settimana["day"])
    bar = tqdm(total=total_iterations)
    for perc in percentuali:
        for _ in range(MAX_RETRY):
            for giorno in settimana["day"]:
                p = settimana["day"][giorno]["pasto"]
                if len(p["pranzo"]["ricette"]) < 1:
                    __scegli_pietanza__(giorno, "pranzo", "principale", perc, True, check_weekly)
                if len(p["cena"]["ricette"]) < 1:
                    __scegli_pietanza__(giorno, "cena", "principale", perc, True, check_weekly)
                if len(p["colazione"]["ricette"]) < 2:
                    __scegli_pietanza__(giorno, "colazione", "colazione", perc, False, check_weekly)
                    __scegli_pietanza__(giorno, "colazione", "colazione_sec", perc, False, check_weekly)
                __scegli_pietanza__(giorno, "pranzo", "contorno", perc, True, check_weekly)
                __scegli_pietanza__(giorno, "cena", "contorno", perc, True, check_weekly)
                if len(p["spuntino"]["ricette"]) < 2:
                    __scegli_pietanza__(giorno, "spuntino", "spuntino", perc, False, check_weekly)
                # Aggiorna la barra di avanzamento
                bar.update(1)


def __print_setts__():
    ws = spreadsheet.worksheet("setts")

    ws.batch_clear(["A1:D1"])

    data_to_write = [[MAX_KCAL, CARBOIDRATI_MAX_GIORNALIERI, PROTEINE_MAX_GIORNALIERI, GRASSI_MAX_GIORNALIERI]]

    ws.update("A1", data_to_write)
    ws.columns_auto_resize(0, 4)


def __print_ricette__():
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f""" select distinct r.nome_ricetta ,
 		                            ceil(sum((carboidrati/100*qta*4)+(proteine/100*qta*4)+(grassi/100*qta*9)) over (partition by ir.id_ricetta)) as kcal,
                                    round(sum(carboidrati/100*qta) over (partition by ir.id_ricetta),2) as carboidrati,
                                    round(sum(proteine/100*qta) over (partition by ir.id_ricetta),2) as proteine,
                                    round(sum(grassi/100*qta) over (partition by ir.id_ricetta),2) as grassi 
                                    from dieta.ingredienti_ricetta ir 
                                    join dieta.ricetta r on (ir.id_ricetta = r.id)
                                    join dieta.alimento a on (ir.id_alimento = a.id)
                                    where 1=1
                                    order by nome_ricetta
                               """, )
            rows = cur.fetchall()

            ws = spreadsheet.worksheet("db")

            ws.batch_clear(["A1:E"])

            data_to_write = []

            for row in rows:
                data_to_write.append(
                    [row["nome_ricetta"], float(row["kcal"]), float(row["carboidrati"]), float(row["proteine"]),
                     float(row["grassi"])])

            ws.update("A1", data_to_write)
            ws.columns_auto_resize(0, 5)
            range_value = []
            for cell in spreadsheet.named_range("ricette"):
                if cell.value != '':
                    range_value.append(cell.value)
            return DataValidationRule(BooleanCondition('ONE_OF_LIST', range_value), showCustomUi=True)
    finally:
        if conn is not None:
            conn.close()


def __print_ingredienti_ricette__():
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""      select r.nome_ricetta , a.nome , ir.qta  
                                    from dieta.ingredienti_ricetta ir join dieta.ricetta r on (ir.id_ricetta = r.id)
                                    join dieta.alimento a ON (a.id = ir.id_alimento)
                                    order by nome_ricetta
                               """, )
            rows = cur.fetchall()

            ws_ricette = spreadsheet.worksheet("ricette")

            ws_ricette.batch_clear(["A1:C"])

            data_to_write = [["Nome Ricetta", "Alimento", "Qta (gr.)"]]

            for row in rows:
                data_to_write.append([row["nome_ricetta"], row["nome"], float(row["qta"])])

            ws_ricette.update("A1", data_to_write)
            ws_ricette.set_basic_filter("A1:C")
            ws_ricette.columns_auto_resize(0, 3)
    finally:
        if conn is not None:
            conn.close()


def __print_menu__(dieta_settimanale, validation_rule):
    existing_menu = True
    dieta_settimanale = simplejson.loads(simplejson.dumps(dieta_settimanale, use_decimal=True))

    ws_source = spreadsheet.worksheet("menu")

    # Ottieni la data corrente
    data_corrente = datetime.now()

    # Calcola il lunedì successivo
    lunedi_successivo = data_corrente + timedelta(days=(7 - data_corrente.weekday()))

    # Calcola la domenica successiva al lunedì successivo
    domenica_successiva = lunedi_successivo + timedelta(days=6)

    # Formatta la stringa richiesta
    new_sheet_name = f"menu-{lunedi_successivo.year}{lunedi_successivo.month:02d}{lunedi_successivo.day:02d}-{domenica_successiva.day:02d}"

    try:
        ws = spreadsheet.worksheet(new_sheet_name)
    except gspread.exceptions.WorksheetNotFound as e:
        existing_menu = False
        spreadsheet.duplicate_sheet(ws_source.id, new_sheet_name=new_sheet_name)
        ws = spreadsheet.worksheet(new_sheet_name)

    if not existing_menu:
        ws.batch_clear(["B7:C23", "H7:I23", "N7:O23", "T7:U23", "Z7:AA23", "AF7:AG23", "AL7:AM23"])
        cols_giorno_settimana = {"lunedi": "B-C", "martedi": "H-I", "mercoledi": "N-O", "giovedi": "T-U",
                                 "venerdi": "Z-AA",
                                 "sabato": "AF-AG", "domenica": "AL-AM", }
        for week_day in cols_giorno_settimana:
            colonna_qta = cols_giorno_settimana[week_day].split('-')[0]
            colonna_ricetta = cols_giorno_settimana[week_day].split('-')[1]

            i = 7
            for ricetta_colazione in dieta_settimanale['day'][week_day]['pasto']['colazione']['ricette']:
                ws.update(str(colonna_qta + str(i)), ricetta_colazione.get('qta'))
                ws.update(str(colonna_ricetta + str(i)), ricetta_colazione.get('nome_ricetta'))
                i = i + 1

            x = 13
            for ricetta_pranzo in dieta_settimanale['day'][week_day]['pasto']['pranzo']['ricette']:
                ws.update(str(colonna_qta + str(x)), ricetta_pranzo.get('qta'))
                ws.update(str(colonna_ricetta + str(x)), ricetta_pranzo.get('nome_ricetta'))
                x = x + 1

            y = 19
            for ricetta_cena in dieta_settimanale['day'][week_day]['pasto']['cena']['ricette']:
                ws.update(str(colonna_qta + str(y)), ricetta_cena.get('qta'))
                ws.update(str(colonna_ricetta + str(y)), ricetta_cena.get('nome_ricetta'))
                y = y + 1

            if len(dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette']) == 2:
                ws.update(str(colonna_qta + "12"),
                          dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][0].get('qta'))
                ws.update(str(colonna_ricetta + "12"),
                          dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][0].get('nome_ricetta'))
                ws.update(str(colonna_qta + "18"),
                          dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][1].get('qta'))
                ws.update(str(colonna_ricetta + "18"),
                          dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][1].get('nome_ricetta'))
            if len(dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette']) == 1:
                ws.update(str(colonna_qta + "12"),
                          dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][0].get('qta'))
                ws.update(str(colonna_ricetta + "12"),
                          dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][0].get('nome_ricetta'))

            set_data_validation_for_cell_range(ws, colonna_ricetta + '7:' + colonna_ricetta + '23', validation_rule)
            time.sleep(SLEEP_TIME)

        ws.columns_auto_resize(0, 43)
        set_column_width(ws, "B", WIDTH_COLS_QTA)
        set_column_width(ws, "H", WIDTH_COLS_QTA)
        set_column_width(ws, "N", WIDTH_COLS_QTA)
        set_column_width(ws, "T", WIDTH_COLS_QTA)
        set_column_width(ws, "Z", WIDTH_COLS_QTA)
        set_column_width(ws, "AF", WIDTH_COLS_QTA)
        set_column_width(ws, "AL", WIDTH_COLS_QTA)

        tg_message = f"""Il menu per la settimana dal {lunedi_successivo.day:02d}/{lunedi_successivo.month:02d} al {domenica_successiva.day:02d}/{domenica_successiva.month:02d} è pronto!!! Lo puoi consultare al seguenti link: {GS_URL}"""
        __send_telegram_message__(tg_message)
    else:
        print(f"menu già presente per {new_sheet_name}")

    return existing_menu


def __print_lista_della_spesa__(ids_all_food: list):
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute(""" create local temporary table temp_ricetta_id ( 
                                       id_ricetta int8 not null,
                                       test varchar(1) not null
                                   ) on commit DROP;
                        """)

            psycopg2.extras.execute_values(cur, f""" insert into temp_ricetta_id (id_ricetta, test)
                             values %s
                         """, [(value, 'a') for value in ids_all_food])

            cur.execute(f"""
                                select nome, sum(qta) as qta_totale
                                    from dieta.ingredienti_ricetta ir
                                    join dieta.alimento a ON (ir.id_alimento = a.id)
                                    join temp_ricetta_id t on (t.id_ricetta = ir.id_ricetta)
                                    where 1 = 1
                                    group by nome
                                    order by nome
                            """)
            rows = cur.fetchall()

            ws = spreadsheet.worksheet("lista della spesa")

            ws.clear()

            data_to_write = []

            for row in rows:
                data_to_write.append([row["nome"], float(row["qta_totale"])])

            ws.insert_row(["nome", "qta totale"])
            ws.update("A2", data_to_write)

            ws.format('A1:B1', {'textFormat': {'bold': True}})
            ws.set_basic_filter("a1:b")
            ws.columns_auto_resize(0, 2)

    finally:
        if conn is not None:
            conn.close()


def main():
    __print_setts__()
    validation_rule = __print_ricette__()
    __print_ingredienti_ricette__()
    __crea_menu__()
    if not __print_menu__(settimana, validation_rule):
        __print_lista_della_spesa__(settimana.get("all_food"))


def pianifica_esecuzione():
    # Ottieni il giorno della settimana corrente (0 = lunedì, 6 = domenica)
    giorno_settimana_corrente = datetime.now().weekday()

    # Verifica il giorno di esecuzione
    if giorno_settimana_corrente == EXEC_DAY:
        main()  # Esegui il tuo programma se oggi è venerdì


if DEV_MODE == 'N':
    # Esegui la verifica dell'esecuzione ogni giorno
    schedule.every().day.at(EXEC_HOUR).do(pianifica_esecuzione)

    while True:
        schedule.run_pending()
        time.sleep(600)
else:
    main()
