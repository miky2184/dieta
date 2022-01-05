import decimal
from pathlib import Path
import math
import os
from dotenv import load_dotenv
import mariadb
import random
from json2html import json2html
import PySimpleGUI as sg
import webbrowser
import copy
import collections

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_NAME = os.getenv('DB_NAME')
DB_PWD = os.getenv('DB_PWD')
MAX_RETRY_LIMIT = 10000

combo_dict = {'SPUNTINO': 0, 'COLAZIONE': 1, 'PRANZO/CENA': 2, 'CONTORNO': 3}


def aggiungi_nuovo_alimento(alimenti_val):
    conndb = None
    try:
        conndb = mariadb.connect(user=DB_USER, database=DB_NAME, host=DB_HOST, password=DB_PWD)
        cursor = conndb.cursor()
        cursor.execute("""INSERT INTO DIETA_ALIMENTO (DESCRIZIONE, KCAL, CARBOIDRATI, PROTEINE, GRASSI) 
                       VALUES (%s, %s, %s, %s, %s);""", (alimenti_val['anome'].upper(), alimenti_val['akcal'],
                                                         alimenti_val['acarb'], alimenti_val['aprot'],
                                                         alimenti_val['agras']))
        conndb.commit()
        sg.popup('Nuovo Alimento Salvato Correttamente!!')
    except Exception as e:
        print(e)
        if conndb is not None:
            conndb.close()
        raise e
    finally:
        if conndb is not None:
            conndb.close()

def set_lista_della_spesa(ingrediente, qta, lista_della_spesa):
    if ingrediente in lista_della_spesa:
        lista_della_spesa[ingrediente] = lista_della_spesa[ingrediente] + qta
    else:
        lista_della_spesa[ingrediente] = qta


def get_alimenti():
    conndb = None
    try:
        conndb = mariadb.connect(user=DB_USER, database=DB_NAME, host=DB_HOST, password=DB_PWD)
        cursor = conndb.cursor()
        cursor.execute("select da.DESCRIZIONE , da.ID from DIETA_ALIMENTO da ORDER BY 1 asc")
        rows = cursor.fetchall()
        return dict(rows)
    except Exception as e:
        print(e)
        if conndb is not None:
            conndb.close()
        raise e
    finally:
        if conndb is not None:
            conndb.close()


def convert_list2dict(ricette_list, di):
    for r in ricette_list:
        if r['pasto'] == 'SPUNTINO':
            di['spuntino'].append(r)
        elif r['pasto'] == 'PRANZO/CENA':
            di['pranzo'].append(r)
            di['cena'].append(r)
        elif r['pasto'] == 'COLAZIONE':
            di['colazione'].append(r)
        elif r['pasto'] == 'CONTORNO':
            di['pranzo'].append(r)
            di['cena'].append(r)
        elif r['pasto'] == 'PRANZO':
            di['pranzo'].append(r)
        elif r['pasto'] == 'CENA':
            di['cena'].append(r)

    return di


def crea_ricetta(ricetta_values):
    conndb = None
    try:
        conndb = mariadb.connect(user=DB_USER, database=DB_NAME, host=DB_HOST, password=DB_PWD)
        cursor = conndb.cursor(dictionary=True)
        nome_ricetta = ricetta_values['nome_ricetta']
        stagione = ricetta_values['stagione']
        categoria_pasto = combo_dict[ricetta_values['pasto']]
        cursor.execute("insert into DIETA_RICETTA(DESCRIZIONE, PASTO, STAGIONE) VALUES (%s, %s, %s);",
                       (nome_ricetta.upper(), categoria_pasto, 'Y' if stagione else 'N'))
        conndb.commit()
        cursor.execute("SELECT LAST_INSERT_ID() as ID;")
        row = cursor.fetchone()
        id_ricetta = row['ID']
        for i in range(10):
            if ricetta_values['alimento' + str(i)] != '' and ricetta_values['qta' + str(i)] != '':
                cursor.execute(
                    "insert into DIETA_INGREDIENTI(ID_RICETTA, ID_ALIMENTO, QTA_GRAMMI) VALUES (%s, %s, %s);",
                    (id_ricetta, combo_alimenti[ricetta_values['alimento' + str(i)]], ricetta_values['qta' + str(i)]))

        conndb.commit()
        sg.popup('Ricetta Salvata Correttamente!!')
    except Exception as e:
        print(e)
        if conndb is not None:
            conndb.close()
        raise e
    finally:
        if conndb is not None:
            conndb.close()


def crea_dieta(perc_colazione, perc_pranzo, perc_spuntini, perc_cena, sesso, altezza, eta, peso):
    conndb = None
    try:
        conndb = mariadb.connect(user=DB_USER, database=DB_NAME, host=DB_HOST, password=DB_PWD)
        cursor = conndb.cursor(dictionary=True)
        lista_della_spesa = {}
        peso_ideale = altezza - 100 if sesso == 'M' else altezza - 104
        metabolismo_basale = math.ceil(
            (655.095 + (9.563 * peso_ideale) + (1.8496 * altezza) - (4.6756 * eta)) if sesso == 'F' else (
                    66.473 + ((13.7516 * peso_ideale) + (5.0033 * altezza) - (6.755 * eta))))
        calorie = (peso_ideale * 30) if sesso == 'M' else (peso_ideale * 28)
        kcal_giorn = (calorie - (calorie * 0.25)) if sesso == 'M' else (calorie - (calorie * 0.15))
        print(f"metabolismo_basale::{metabolismo_basale}")
        print(f"peso ideale::{peso_ideale}")
        print(f"calorie giornaliere::{calorie}")
        print(f"fabbisogno::{kcal_giorn}")
        fabbisogno_proteine = math.ceil(peso_ideale * 1.125)
        fabbisogno_grassi = math.ceil(((kcal_giorn * 0.25) / 9) if sesso == 'M' else ((kcal_giorn * 0.30) / 9))
        kcal_proteine = fabbisogno_proteine * 4
        kcal_grassi = fabbisogno_grassi * 9
        kcal_carbo = kcal_giorn - kcal_proteine - kcal_grassi
        fabbisogno_carboidrati = math.ceil(kcal_carbo / 4)

        print(f"fabbisogno carbo::{fabbisogno_carboidrati}")
        print(f"fabbisogno proteine::{fabbisogno_proteine}")
        print(f"fabbisogno grassi::{fabbisogno_grassi}")

        ##fabbisogno_carboidrati = math.floor(kcal_giorn / 4)
        ##fabbisogno_proteine = math.floor(kcal_giorn / 4)

        max_calorie_colazione = math.floor(kcal_giorn * perc_colazione / 100)
        max_calorie_pranzo = math.floor(kcal_giorn * perc_pranzo / 100)
        max_calorie_cena = math.floor(kcal_giorn * perc_cena / 100)
        max_calorie_spuntini = math.floor(kcal_giorn * perc_spuntini / 100)
        max_calorie_pranzo = max_calorie_pranzo + (
                kcal_giorn - max_calorie_colazione - max_calorie_pranzo - max_calorie_spuntini - max_calorie_cena)
        ##print(kcal_giorn)

        cursor.execute("""WITH RICETTARIO AS (SELECT dr.ID , dr.DESCRIZIONE , sp.DESCRIZIONE as PASTO, da.DESCRIZIONE as ingrediente, di.QTA_GRAMMI , 
                         da.KCAL / 100 * di.QTA_GRAMMI as kcal, da.CARBOIDRATI / 100 * di.QTA_GRAMMI as carboidrati,
                        da.PROTEINE / 100 * di.QTA_GRAMMI as proteine, da.GRASSI / 100 * di.QTA_GRAMMI as grassi, da.CATEGORIA_ALIMENTARE 
                        FROM  DIETA_RICETTA dr join DIETA_INGREDIENTI di ON (dr.ID = di.ID_RICETTA)
                        join DIETA_ALIMENTO da on (di.ID_ALIMENTO= da.ID) JOIN DIETA_PASTO sp on (dr.PASTO=sp.ID)
                         WHERE PASTO != 0 OR dr.STAGIONE = 'Y'
                        ) 
                        SELECT distinct ID, DESCRIZIONE as ricetta , pasto as pasto,  ceil(SUM(kcal) over (PARTition by id)) as kcal_totali,
                        SUM(carboidrati) over (PARTition by id) as carboidrati_totali,
                        SUM(proteine) over (PARTition by id) as proteine_totali,
                        SUM(grassi) over (PARTition by id) as grassi_totali,
                        false as used,
                        max(CATEGORIA_ALIMENTARE) over (partition by id) as cat_alim
                        FROM RICETTARIO
                        order by 1
                        ;
                           """)
        rows = cursor.fetchall()

        print(f"kcal_giorn::{decimal.Decimal(kcal_giorn)}")
        weekly = {}
        cursor.execute("select CAT , MAXTIMES  from DIETA_CATEGORIA dc;")
        rweekly = cursor.fetchall()
        for r in rweekly:
            weekly[r['CAT']] = r['MAXTIMES']
        template_daily = {"completed": False, "kcal": decimal.Decimal(kcal_giorn),
                          "fabbisogno_carboidrati": decimal.Decimal(fabbisogno_carboidrati),
                          "fabbisogno_proteine": decimal.Decimal(fabbisogno_proteine),
                          "fabbisogno_grassi": decimal.Decimal(fabbisogno_grassi),
                          "menu": {"colazione": {"colazione": [], "tot": 0, "max": max_calorie_colazione, "isok": False,
                                                 "occ": 1},
                                   "spuntino": {"spuntino": [], "tot": 0, "max": max_calorie_spuntini, "isok": False,
                                                "occ": 2},
                                   "pranzo": {"pranzo": [], "tot": 0, "max": max_calorie_pranzo, "isok": False,
                                              "occ": 2},
                                   "cena": {"cena": [], "tot": 0, "max": max_calorie_cena, "isok": False, "occ": 2}}}

        template_menu = {"colazione": [],
                         "spuntino": [],
                         "pranzo": [],
                         "cena": []}

        dieta = {}
        menu_settimale = {}
        for day in ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]:
            dieta[day] = copy.deepcopy(template_daily)
            menu_settimale[day] = copy.deepcopy(template_menu)

        ricette_dict = {"colazione": [], "pranzo": [], "spuntino": [], "cena": []}
        convert_list2dict(rows, ricette_dict)

        """while (not dieta["lunedi"]["completed"] or not dieta["martedi"]["completed"] or not dieta["mercoledi"][
            "completed"]
               or not dieta["giovedi"]["completed"] or not dieta["venerdi"]["completed"] or not dieta["sabato"][
                    "completed"]
               or not dieta["domenica"]["completed"]):"""
        ##print(dieta["lunedi"]["kcal"])
        for giorno in dieta:
            make_menu(dieta, ricette_dict, giorno, menu_settimale, lista_della_spesa, weekly, conndb)

        print(weekly)

        ##pprint.pprint(dieta)

        ##infoFromJson = json.loads(str(dieta))
        ##print(json2html.convert(json=dieta))

        f = open('table.html', 'w')

        message = """<html><head>
            <style>
           h2 {{ color: #111; font-family: 'Open Sans', sans-serif; font-size: 30px; font-weight: 300; line-height: 32px; margin: 0 0 72px; text-align: center; }}
            
      table      {{
  font-family: Arial, Helvetica, sans-serif;
  border-collapse: collapse;
  width: 100%;
}}

 td, th {{
  border: 1px solid #ddd;
  padding: 8px;
}}

 tr:nth-child(even){{background-color: #f2f2f2;}}

 th {{
  padding-top: 12px;
  padding-bottom: 12px;
  text-align: left;
  background-color: #04AA6D;
  color: white;
}}
            </style></head>
            <body><h2>MENU SETTIMANALE</h2></br>{0}</br>
            <h2>LISTA DELLA SPESA</h2></br>
            {1}</body>
            </html>"""

        f.write(message.format(json2html.convert(json=menu_settimale),
                               json2html.convert(json=collections.OrderedDict(sorted(lista_della_spesa.items())))))
        f.close()

        # Change path to reflect file location
        filepath = Path('table.html').resolve()
        filename = 'file:///Users/michele.micunco/Documents/Workspace/GOOGLE/my_python/' + 'table.html'
        filename = f'file://{filepath}'
        webbrowser.open_new_tab(filename)
    except Exception as e:
        print(e)
        if conndb is not None:
            conndb.close()
        raise e
    finally:
        if conndb is not None:
            conndb.close()


def make_menu(dietajson, ricette, giornodieta, menu_settimale, lista_spesa, limiti_settimanali, conndb):

    cursor = conndb.cursor(dictionary=True)
    daily_menu = dietajson[giornodieta]["menu"]
    daily_kcal = dietajson[giornodieta]
    pasti = ['pranzo', 'colazione', 'cena', 'spuntino']

    ##print(f"{max_calorie_colazione}::{calorie_pranzo}::{max_calorie_cena}::{max_calorie_spuntini}")
    ##print(f"{fabbisogno_carboidrati}::{fabbisogno_proteine}::{fabbisogno_grassi}")

    all_is_ok = False
    while not all_is_ok:

        for pasto in pasti:
            retry = MAX_RETRY_LIMIT

            while not daily_menu[pasto]["isok"] and retry > 0:
                # print(daily_menu[pasto]["tot"])
                # print(daily_menu[pasto]["max"])
                # pprint.pprint(daily_menu)

                if pasto == 'spuntino':
                    cibi_disponibili = [d for d in ricette[pasto] if
                                        d['ID'] not in [x['ID'] for x in daily_menu[pasto][pasto]] and d[
                                            'kcal_totali'] +
                                        daily_menu[pasto]["tot"] <=
                                        daily_menu[pasto]["max"] and len(daily_menu[pasto][pasto]) < 2]
                # print(cibi_disponibili)
                elif pasto in ('pranzo', 'cena'):
                    cibi_disponibili = [d for d in ricette[pasto] if
                                        d['kcal_totali'] +
                                        daily_menu[pasto]["tot"] <=
                                        daily_menu[pasto]["max"] and not d['used'] and
                                        (False if d['pasto'] == 'CONTORNO' and 'CONTORNO' in [x['pasto'] for x in
                                                                                              daily_menu[pasto][
                                                                                                  pasto]] else True

                                         ) and (d['cat_alim'] is None or limiti_settimanali[d['cat_alim']] > 0)]
                else:
                    cibi_disponibili = [d for d in ricette[pasto] if
                                        d['kcal_totali'] +
                                        daily_menu[pasto]["tot"] <=
                                        daily_menu[pasto]["max"] and (
                                                not d['used'] or len(daily_menu[pasto][pasto]) < 1)]

                if len(cibi_disponibili) > 0:
                    p = random.choice(cibi_disponibili)
                    if (daily_kcal['kcal'] - p['kcal_totali'] >= 0 or daily_kcal['kcal'] - p[
                        'kcal_totali'] <= 100) and daily_kcal['fabbisogno_carboidrati'] - p[
                        'carboidrati_totali'] >= 0 and daily_kcal['fabbisogno_grassi'] - p['grassi_totali'] >= 0 and \
                            daily_kcal['fabbisogno_proteine'] - p['proteine_totali'] >= 0:

                        if pasto not in ('colazione', 'spuntino') and p['pasto'] != 'CONTORNO':
                            p['used'] = True

                        if p['kcal_totali'] + daily_menu[pasto]["tot"] <= daily_menu[pasto]["max"]:
                            daily_kcal['fabbisogno_carboidrati'] = daily_kcal['fabbisogno_carboidrati'] - p[
                                'carboidrati_totali']
                            daily_kcal['fabbisogno_proteine'] = daily_kcal['fabbisogno_proteine'] - p[
                                'proteine_totali']
                            daily_kcal['fabbisogno_grassi'] = daily_kcal['fabbisogno_grassi'] - p['grassi_totali']

                            ##print(p)
                            daily_menu[pasto][pasto].append(p)

                            cursor.execute(f"""
                            select da.DESCRIZIONE as descrizione, di.QTA_GRAMMI as qta 
                            from DIETA_RICETTA dr join DIETA_INGREDIENTI di on(dr.ID = di.ID_RICETTA) join
                            DIETA_ALIMENTO da on(da.ID = di.ID_ALIMENTO)
                            where dr.ID = {p['ID']};""")

                            ingredienti = cursor.fetchall()

                            for i in ingredienti:
                                set_lista_della_spesa(i['descrizione'], i['qta'], lista_spesa)

                            menu_settimale[giornodieta][pasto].append(
                                {"ricetta": p['ricetta'], "kcal": p['kcal_totali'],
                                 "carboidrati": round(p['carboidrati_totali'], 2),
                                 "proteine": round(p['proteine_totali'], 2),
                                 'grassi': round(p['grassi_totali'], 2), 'ingredienti': ingredienti},
                            )
                            daily_menu[pasto]["occ"] = daily_menu[pasto]["occ"] - 1
                            daily_menu[pasto]["tot"] = daily_menu[pasto]["tot"] + p['kcal_totali']
                            daily_kcal['kcal'] = daily_kcal['kcal'] - p['kcal_totali']
                            if p['cat_alim'] is not None:
                                limiti_settimanali[p['cat_alim']] = limiti_settimanali[p['cat_alim']] - 1
                        else:
                            retry = retry - 1
                    else:
                        retry = retry - 1
                else:
                    daily_menu[pasto]["isok"] = True

            daily_menu[pasto]["isok"] = True

            if daily_menu['colazione']['isok'] and daily_menu['pranzo']['isok'] and daily_menu['cena']['isok'] and \
                    daily_menu['spuntino']['isok']:
                all_is_ok = True

            menu_settimale[giornodieta]['rimanenti'] = {'kcal': round(daily_kcal['kcal'], 2),
                                                        'carboidrati': round(daily_kcal['fabbisogno_carboidrati'],
                                                                             2),
                                                        'proteine': round(daily_kcal['fabbisogno_proteine'], 2),
                                                        'grassi': round(daily_kcal['fabbisogno_grassi'], 2)}


sg.theme('SystemDefault')  # Add a touch of color
# All the stuff inside your window.

combo_alimenti = get_alimenti()
choices = list(combo_alimenti.keys())

layout_alimenti = [[ sg.Text('Nome Alimento', size=(20, 1)), sg.InputText(key='anome')],
                   [sg.Text('KCAL', size=(20, 1)), sg.InputText(key='akcal')],
[sg.Text('CARBOIDRATI', size=(20, 1)), sg.InputText(key='acarb')],
[sg.Text('PROTEINE', size=(20, 1)), sg.InputText(key='aprot')],
[sg.Text('GRASSI', size=(20, 1)), sg.InputText(key='agras')],
    [sg.Submit('Salva Nuovo Alimento')]]

layout_ricette = [
    [sg.Text('NOME RICETTA', size=(20, 1)), sg.InputText(key='nome_ricetta'),
     sg.Combo(list(combo_dict.keys()), key='pasto'),
     sg.Checkbox("Stagione", key='stagione')],
    [sg.Combo(choices, key='alimento0'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta0')],
    [sg.Combo(choices, key='alimento1'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta1')],
    [sg.Combo(choices, key='alimento2'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta2')],
    [sg.Combo(choices, key='alimento3'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta3')],
    [sg.Combo(choices, key='alimento4'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta4')],
    [sg.Combo(choices, key='alimento5'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta5')],
    [sg.Combo(choices, key='alimento6'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta6')],
    [sg.Combo(choices, key='alimento7'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta7')],
    [sg.Combo(choices, key='alimento8'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta8')],
    [sg.Combo(choices, key='alimento9'), sg.Text('QTA:', size=(20, 1)), sg.InputText(key='qta9')],
    [sg.Submit('Salva Ricetta'), sg.Submit('Ricarica Alimenti')]
]

layout_dieta = [[sg.Text('NOME', size=(20, 1)), sg.Input(key='nome', default_text='Michele'),
                 sg.Text('COGNOME', size=(20, 1)), sg.Input(key='cognome', default_text='Micunco')],
                [sg.Text('SESSO', size=(20, 1)), sg.Combo(["M", "F"], key='sesso', default_value='M')],
                [sg.Text('ALTEZZA', size=(20, 1)),
                 sg.Slider(range=(140, 210), orientation='h', size=(34, 20), default_value=166, key='altezza')],
                [sg.Text('ETA', size=(20, 1)),
                 sg.Slider(range=(18, 100), orientation='h', size=(34, 20), default_value=37, key='eta')],
                 [sg.Text('PESO ATTUALE', size=(20, 1)),
                sg.Slider(range=(40, 210), orientation='h', size=(34, 20), default_value=77, key='peso')],
                [sg.Text('%Colazione', size=(20, 1)),
                 sg.Slider(range=(0, 100), orientation='h', size=(34, 20), default_value=20, key='perc_colazione')],
                [sg.Text('%Pranzo', size=(20, 1)),
                 sg.Slider(range=(0, 100), orientation='h', size=(34, 20), default_value=32, key='perc_pranzo')],
                [sg.Text('%Spuntini', size=(20, 1)),
                 sg.Slider(range=(0, 100), orientation='h', size=(34, 20), default_value=16, key='perc_spuntini')],
                [sg.Text('%Cena', size=(20, 1)),
                 sg.Slider(range=(0, 100), orientation='h', size=(34, 20), default_value=32, key='perc_cena')],
                [sg.Submit('Genera Dieta')]]

tabgrp = [[sg.TabGroup([[sg.Tab('La mia dieta', layout_dieta), sg.Tab('Le mie ricetta', layout_ricette), sg.Tab('Aggiungi Alimenti', layout_alimenti)]],
                       tab_location='centertop',
                       title_color='White', tab_background_color='Black', selected_title_color='Black',
                       selected_background_color='Gray', border_width=5)], [sg.Button('Close')]]

# Create the Window
window = sg.Window('La mia Dieta', return_keyboard_events=True, finalize=True, ).Layout(tabgrp)

# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Close':  # if user closes window or clicks cancel
        break

    if event == 'Genera Dieta':
        ##dieta(9100, 50, 30, 20, 19, 31, 16, 34)
        crea_dieta(int(values['perc_colazione']), int(values['perc_pranzo']), int(values['perc_spuntini']),
                   int(values['perc_cena']), str(values['sesso']), int(values['altezza']), int(values['eta']), int(values['peso']))
    if event == 'Salva Ricetta':
        crea_ricetta(values)

    if event == 'Salva Nuovo Alimento':
        aggiungi_nuovo_alimento(values)

    if event == 'Ricarica Alimenti':
        combo_alimenti = get_alimenti()
        choices = list(combo_alimenti.keys())
        for i in range(10):
            window['alimento'+str(i)].update(value='', values=choices)
    ##print('You entered ', values[0])

window.close()
