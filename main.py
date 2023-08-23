import json
import random
from copy import deepcopy
from decimal import Decimal
import gspread
import psycopg2.extras
from google.oauth2.service_account import Credentials
import simplejson

from db import connect_to_db

# Limiti giornalieri
MAX_KCAL = 1600
CARBOIDRATI_MAX_GIORNALIERI = 240
PROTEINE_MAX_GIORNALIERI = 61
GRASSI_MAX_GIORNALIERI = 44
MAX_RETRY = 5

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

settimana = {"day": {
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

# Percorso al file delle credenziali JSON
credentials_file = './sa/credentials.json'

# Definisci i diritti di accesso
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/spreadsheets']

# Carica le credenziali e inizializza l'autenticazione
credentials = Credentials.from_service_account_file(credentials_file, scopes=scope)
client = gspread.authorize(credentials)

# Apri un foglio di calcolo esistente utilizzando il suo URL o il suo titolo
spreadsheet = client.open_by_url(
    'https://docs.google.com/spreadsheets/d/1Dfol4CiWuiA1P-cLOoBbNuKzmvvlaXwZTY6y3oPRV-4/edit#gid=0')


def scegli_pietanza(giorno_settimana: str, meal_time: str, tipo: str, disponibili: bool):
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                             select distinct r.id, r.nome_ricetta ,
                                ceil(sum((carboidrati/100*qta*4)+(proteine/100*qta*4)+(grassi/100*qta*9)) over (partition by ir.id_ricetta)) as kcal,
                                round(sum(carboidrati/100*qta) over (partition by ir.id_ricetta),2) as carboidrati,
                                round(sum(proteine/100*qta) over (partition by ir.id_ricetta),2) as proteine,
                                round(sum(grassi/100*qta) over (partition by ir.id_ricetta),2) as grassi,
                                r.colazione , r.spuntino , r.principale , r.contorno 
                                from dieta.ingredienti_ricetta ir 
                                join dieta.ricetta r on (ir.id_ricetta = r.id)
                                join dieta.alimento a on (ir.id_alimento = a.id)
                                where {tipo}
                                  and r.enabled
                                  and (extract(month from current_date) = any(stagionalita) or stagionalita is null)
                               -- order by 1, 7 desc,8 desc,9 desc,10 desc;
                        """)
            rows = cur.fetchall()
            max_retry = 900
            return select_food(rows, giorno_settimana, meal_time, max_retry, disponibili, False)

    finally:
        if conn is not None:
            conn.close()


def select_food(rows, giorno_settimana, meal_time, max_retry, disponibili: bool, found: bool):
    if disponibili:
        ids_disponibili = [oggetto["id"] for oggetto in rows if oggetto["id"] not in settimana["all_food"]]
    else:
        ids_disponibili = [oggetto["id"] for oggetto in rows if
                           oggetto["id"] not in settimana.get("day").get(giorno_settimana).get("pasto").get(meal_time).get("ids")]

    if ids_disponibili and max_retry > 0:
        # Seleziona casualmente un ID dalla lista dei disponibili
        id_selezionato = random.choice(ids_disponibili)
        max_retry = max_retry - 1

        # Trova l'oggetto corrispondente all'ID selezionato
        ricetta_selezionata = next(oggetto for oggetto in rows if oggetto["id"] == id_selezionato)

        mt = settimana.get("day").get(giorno_settimana).get("pasto").get(meal_time)
        day = settimana.get("day").get(giorno_settimana)
        if (
                (day.get("kcal") - ricetta_selezionata.get("kcal")) > 0 and
                (day.get("carboidrati") - ricetta_selezionata.get("carboidrati")) > 0 and
                (day.get("proteine") - ricetta_selezionata.get("proteine")) > 0 and
                (day.get("grassi") - ricetta_selezionata.get("grassi")) > 0
        ):
            settimana.get("all_food").append(id_selezionato)
            mt.get("ids").append(id_selezionato)
            mt.get("ricette").append(ricetta_selezionata.get("nome_ricetta"))
            day["kcal"] = day.get("kcal") - ricetta_selezionata.get("kcal")
            day["carboidrati"] = day.get("carboidrati") - ricetta_selezionata.get("carboidrati")
            day["proteine"] = day.get("proteine") - ricetta_selezionata.get("proteine")
            day["grassi"] = day.get("grassi") - ricetta_selezionata.get("grassi")
            found = True
        else:
            select_food(rows, giorno_settimana, meal_time, max_retry, disponibili, False)

    return found


def main():
    print_setts()
    print_ricette()
    print_ingredienti_ricette()
    for i in range(MAX_RETRY):
        for giorno in settimana["day"]:
            scegli_pietanza(giorno, "pranzo", "principale", True)
            scegli_pietanza(giorno, "cena", "principale", True)
            scegli_pietanza(giorno, "pranzo", "contorno", True)
            scegli_pietanza(giorno, "cena", "contorno", True)
            scegli_pietanza(giorno, "spuntino", "spuntino", False)
            scegli_pietanza(giorno, "colazione", "colazione", False)
    #print(settimana)
    print_menu(settimana)
    print_lista_della_spesa(settimana.get("all_food"))


def print_setts():
    ws = spreadsheet.worksheet("setts")

    ws.batch_clear(["A1:D1"])

    data_to_write = [[MAX_KCAL, CARBOIDRATI_MAX_GIORNALIERI, PROTEINE_MAX_GIORNALIERI, GRASSI_MAX_GIORNALIERI]]

    ws.update("A1", data_to_write)
    ws.columns_auto_resize(0, 4)


def print_ricette():
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
                data_to_write.append([row["nome_ricetta"], float(row["kcal"]), float(row["carboidrati"]), float(row["proteine"]), float(row["grassi"])])

            ws.update("A1", data_to_write)
            ws.columns_auto_resize(0, 5)
    finally:
        if conn is not None:
            conn.close()


def print_ingredienti_ricette():
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
            ws_ricette.format('A1:C1', {'textFormat': {'bold': True}})
            ws_ricette.set_basic_filter("a1:c")
            ws_ricette.columns_auto_resize(0, 3)
    finally:
        if conn is not None:
            conn.close()


def print_menu(dieta_settimanale):
    dieta_settimanale = simplejson.loads(simplejson.dumps(dieta_settimanale, use_decimal=True))

    ws = spreadsheet.worksheet("menu")
    ws.batch_clear(["B3:B19","G3:G19","L3:L19","Q3:Q19","V3:V19","AA3:AA19","AF3:AF19",])
    cols_giorno_settimana = {"lunedi": "B","martedi": "G","mercoledi": "L","giovedi": "Q","venerdi": "V","sabato": "AA","domenica": "AF",}
    for week_day in cols_giorno_settimana:
        i = 3
        for ricetta_colazione in dieta_settimanale['day'][week_day]['pasto']['colazione']['ricette']:
            ws.update(str(cols_giorno_settimana[week_day]+str(i)), ricetta_colazione)
            i = i + 1
        x = 9
        for ricetta_pranzo in dieta_settimanale['day'][week_day]['pasto']['pranzo']['ricette']:
            ws.update(str(cols_giorno_settimana[week_day]+str(x)), ricetta_pranzo)
            x = x + 1
        y = 15
        for ricetta_cena in dieta_settimanale['day'][week_day]['pasto']['cena']['ricette']:
            ws.update(str(cols_giorno_settimana[week_day]+str(y)), ricetta_cena)
            y = y + 1
        ws.update(str(cols_giorno_settimana[week_day] + "8"), dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][0])
        ws.update(str(cols_giorno_settimana[week_day] + "14"), dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette'][1] if len(dieta_settimanale['day'][week_day]['pasto']['spuntino']['ricette']) > 0 else None)

    ws.columns_auto_resize(0, 36)
    return dieta_settimanale


def print_lista_della_spesa(ids_all_food: list):
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"""
                                select nome, sum(qta) as qta_totale
                                    from dieta.ingredienti_ricetta ir
                                    join dieta.alimento a ON (ir.id_alimento = a.id)
                                    where id_ricetta = any( %s )
                                    group by nome
                                    order by nome
                            """,  (ids_all_food,))
            rows = cur.fetchall()

            ws = spreadsheet.worksheet("lista della spesa")

            ws.batch_clear("A1:B")

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


if __name__ == '__main__':
    main()
