from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, current_app
from .services.menu_services import (definisci_calorie_macronutrienti, save_weight, genera_menu,
                                     stampa_lista_della_spesa, get_menu_corrente, salva_menu_settimana_prossima,
                                     carica_ricette, get_settimane_salvate, get_menu_settima_prossima,
                                     salva_menu_corrente, get_menu_settimana, get_settimana, salva_ricetta,
                                     attiva_disattiva_ricetta, get_ricette, elimina_ingredienti, salva_utente_dieta,
                                     salva_nuova_ricetta, salva_ingredienti,
                                     recupera_ingredienti, get_peso_hist, get_dati_utente,
                                     calcola_macronutrienti_rimanenti,
                                     recupera_alimenti, salva_alimento, elimina_alimento, salva_nuovo_alimento,
                                     aggiungi_ricetta_al_menu, update_menu_corrente, remove_meal_from_menu)
from copy import deepcopy
import time
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from io import BytesIO
import base64
from PIL import Image

views = Blueprint('views', __name__)


@views.route('/', methods=['GET'])
@current_app.cache.cached(timeout=300)
def index():
    """
    Questa funzione gestisce la route principale (/) e restituisce la pagina principale con il menu settimanale,
    le ricette, i macronutrienti e altri dati rilevanti. Se il menu corrente non esiste, viene creato un menu vuoto.
    """
    # Calcola le calorie e i macronutrienti giornalieri dell'utente.
    macronutrienti = definisci_calorie_macronutrienti()

    # Recupera le ricette disponibili dal database.
    ricette = carica_ricette(stagionalita=False)

    # Recupera il menu corrente dal database.
    menu_corrente = get_menu_corrente()

    # Se il menu corrente non esiste, crea una struttura vuota con tutti i pasti e i macronutrienti inizializzati.
    if not menu_corrente:
        menu_corrente = {
            'day': {
                'lunedi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                     'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                     'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0},
                'martedi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                      'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                      'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0,
                            'grassi': 0},
                'mercoledi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                        'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                        'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0,
                              'grassi': 0},
                'giovedi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                      'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                      'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0,
                            'grassi': 0},
                'venerdi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                      'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                      'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0,
                            'grassi': 0},
                'sabato': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                     'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                     'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0},
                'domenica': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                       'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                       'cena': {'ricette': []}}, 'kcal': 0, 'carboidrati': 0, 'proteine': 0,
                             'grassi': 0},
            },
            'weekly': {'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0},
            'all_food': []
        }

    # Recupera le settimane salvate per la selezione.
    settimane_salvate = get_settimane_salvate()

    # Genera la lista della spesa basata sul menu corrente.
    lista_spesa = stampa_lista_della_spesa(menu_corrente.get('all_food'))

    # Calcola i macronutrienti rimanenti per ogni giorno del menu.
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

    # Recupera tutti gli alimenti dal database.
    alimenti = recupera_alimenti()

    # Rende la pagina index con tutti i dati necessari.
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           ricette=ricette,
                           menu=menu_corrente,
                           lista_spesa=lista_spesa,
                           settimane=settimane_salvate,
                           remaining_macronutrienti=remaining_macronutrienti,
                           alimenti=alimenti
                           )


@views.route('/generate_menu', methods=['POST'])
def generate_menu():
    """
    Questa funzione gestisce la generazione del menu per la settimana corrente e quella successiva.
    Viene chiamata tramite una richiesta POST e restituisce un aggiornamento del progresso della generazione.
    """
    macronutrienti = definisci_calorie_macronutrienti()
    ricette_menu = carica_ricette(stagionalita=True)

    progress = 0
    total_steps = 4  # Numero totale di passaggi nella generazione del menu

    # Generazione del menu per la settimana corrente
    if not get_menu_corrente():
        settimana_corrente = deepcopy(get_settimana(macronutrienti))
        genera_menu(settimana_corrente, False, ricette_menu)
        progress += 1 / total_steps * 100
        time.sleep(1)  # Simula tempo di elaborazione

        genera_menu(settimana_corrente, True, ricette_menu)
        progress += 1 / total_steps * 100
        time.sleep(1)

        salva_menu_corrente(settimana_corrente)
        progress += 1 / total_steps * 100
    else:
        progress += 3 / total_steps * 100

    # Generazione del menu per la settimana successiva
    if not get_menu_settima_prossima():
        prossima_settimana = deepcopy(get_settimana(macronutrienti))
        genera_menu(prossima_settimana, False, ricette_menu)
        progress += 1 / total_steps * 100
        time.sleep(1)

        genera_menu(prossima_settimana, True, ricette_menu)
        salva_menu_settimana_prossima(prossima_settimana)
    else:
        progress += 1 / total_steps * 100

    current_app.cache.delete("view//")
    return jsonify({'status': 'success', 'progress': progress})


@views.route('/menu_settimana/<int:settimana_id>', methods=['GET'])
@current_app.cache.cached(timeout=300)
def menu_settimana(settimana_id):
    """
    Questa funzione gestisce la richiesta di visualizzazione di un menu specifico per una settimana data.
    Restituisce il menu selezionato e i macronutrienti rimanenti per quella settimana.
    """
    menu_selezionato = get_menu_settimana(settimana_id)

    macronutrienti_rimanenti = calcola_macronutrienti_rimanenti(menu_selezionato)

    return jsonify({'menu': menu_selezionato, 'remaining_macronutrienti': macronutrienti_rimanenti})


@views.route('/get_lista_spesa', methods=['POST'])
@current_app.cache.cached(timeout=300)
def get_lista_spesa():
    """
    Questa funzione gestisce la richiesta POST per ottenere la lista della spesa basata sugli ID degli alimenti
    forniti dal client. Restituisce la lista della spesa corrispondente.
    """
    data = request.get_json()
    ids_all_food = data.get('ids_all_food', [])

    # Genera la lista della spesa basata sugli ID degli alimenti.
    lista_spesa = stampa_lista_della_spesa(ids_all_food)

    return jsonify(lista_spesa=lista_spesa)


@views.route('/save_recipe', methods=['POST'])
def save_recipe():
    """
    Questa funzione salva o aggiorna una ricetta nel database in base ai dati forniti dal client.
    """
    data = request.get_json()
    ricetta_id = data['id']
    colazione = data['colazione']
    colazione_sec = data['colazione_sec']
    spuntino = data['spuntino']
    principale = data['principale']
    contorno = data['contorno']
    nome = data['nome']

    salva_ricetta(nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id)
    current_app.cache.delete("view//")

    return jsonify({'status': 'success', 'message': 'Ricetta salvata con successo!'})


@views.route('/toggle_recipe_status', methods=['POST'])
def toggle_recipe_status():
    """
    Questa funzione attiva o disattiva una ricetta specifica nel database, basandosi sull'ID della ricetta.
    """
    data = request.get_json()
    ricetta_id = data['id']

    attiva_disattiva_ricetta(ricetta_id)
    current_app.cache.delete("view//")

    return jsonify({'status': 'success', 'message': 'Ricetta modificata con successo!'})


@views.route('/recipe/<int:recipe_id>', methods=['GET'])
@current_app.cache.cached(timeout=300)
def recipe(recipe_id):
    """
    Questa funzione restituisce i dettagli di una ricetta specifica basata sul suo ID.
    """
    return jsonify(get_ricette(recipe_id))


@views.route('/delete_ingredient', methods=['POST'])
def delete_ingredient():
    """
    Questa funzione elimina un ingrediente da una ricetta basata sugli ID forniti.
    """
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']

    elimina_ingredienti(ingredient_id, recipe_id)

    return jsonify({'status': 'success', 'message': 'Ingrediente eliminato correttamente.'})


@views.route('/get_all_ingredients', methods=['GET'] )
@current_app.cache.cached(timeout=300)
def get_all_ingredients():
    """
    Questa funzione restituisce tutti gli ingredienti disponibili nel database.
    """
    return jsonify(recupera_ingredienti())


@views.route('/add_ingredient_to_recipe', methods=['POST'])
def add_ingredient_to_recipe():
    """
    Questa funzione aggiunge un ingrediente a una ricetta esistente nel database.
    """
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    salva_ingredienti(recipe_id, ingredient_id, quantity)

    return jsonify({'status': 'success', 'message': 'Ingrediente inserito correttamente.'})


@views.route('/update_ingredient', methods=['POST'])
def update_ingredient():
    """
    Questa funzione aggiorna la quantità di un ingrediente specifico in una ricetta.
    """
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    salva_ingredienti(recipe_id, ingredient_id, quantity)
    current_app.cache.delete(f"view//recipe/{recipe_id}")

    return jsonify({'status': 'success', 'message': 'Quantità aggiornata correttamente.'})


@views.route('/new_recipe', methods=['POST'])
def new_recipe():
    """
    Questa funzione salva una nuova ricetta basata sui dati forniti dal form.
    """
    name = request.form['name']
    breakfast = 'breakfast' in request.form
    snack = 'snack' in request.form
    main = 'main' in request.form
    side = 'side' in request.form
    second_breakfast = 'second_breakfast' in request.form

    salva_nuova_ricetta(name.upper(), breakfast, snack, main, side, second_breakfast)

    return redirect(url_for('views.index'))


@views.route('/new_food', methods=['POST'])
def new_food():
    """
    Questa funzione salva un nuovo alimento basato sui dati forniti dal form.
    """
    name = request.form['alimento']
    carboidrati = request.form['carboidrati']
    proteine = request.form['proteine']
    grassi = request.form['grassi']
    verdura = 'verdura' in request.form
    frutta = 'frutta' in request.form
    pesce = 'pesce' in request.form
    pane = 'pane' in request.form
    confezionato = 'confezionato' in request.form
    vegan = 'vegan' in request.form
    carne_bianca = 'carne-bianca' in request.form
    carne_rossa = 'carne-rossa' in request.form

    salva_nuovo_alimento(name, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura,
                         confezionato, vegan, pesce)

    return redirect(url_for('views.index'))


@views.route('/submit-weight', methods=['POST'])
def submit_weight():
    """
    Questa funzione salva il peso dell'utente nel database.
    """
    data = request.json
    # Salva i dati del peso nel database
    peso = save_weight(data['date'], data['weight'])
    # Esempio di svuotamento della cache di una funzione specifica
    current_app.cache.delete(f"view//get_peso_data")

    return jsonify(peso)


@views.route('/salva-dati', methods=['POST'])
def salva_dati():
    """
    Questa funzione salva i dati personali dell'utente relativi alla dieta nel database.
    """
    id = request.form['id']
    nome = request.form['nome']
    cognome = request.form['cognome']
    sesso = request.form['sesso']
    eta = int(request.form['eta'])
    altezza = int(request.form['altezza'])
    peso = int(request.form['peso'])
    tdee = request.form['tdee']
    deficit_calorico = request.form['deficit_calorico']
    bmi = float(request.form['bmi'])
    peso_ideale = int(request.form['peso_ideale'])
    meta_basale = int(request.form['meta_basale'])
    meta_giornaliero = int(request.form['meta_giornaliero'])
    calorie_giornaliere = int(request.form['calorie_giornaliere'])
    calorie_settimanali = int(request.form['calorie_settimanali'])
    carboidrati = int(request.form['carboidrati'])
    proteine = int(request.form['proteine'])
    grassi = int(request.form['grassi'])

    salva_utente_dieta(id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                       meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
                       proteine, grassi)
    current_app.cache.delete(f"view//get_data_utente")
    return redirect(url_for('views.index'))


@views.route('/get_peso_data', methods=['GET'])
@current_app.cache.cached(timeout=300)
def get_peso_data():
    """
    Questa funzione recupera la cronologia del peso dell'utente dal database.
    """
    peso = get_peso_hist()
    return jsonify(peso)


@views.route('/get_data_utente', methods=['GET'])
@current_app.cache.cached(timeout=300)
def get_data_utente():
    """
    Questa funzione restituisce i dati personali dell'utente relativi alla dieta.
    """
    utente = get_dati_utente()
    return jsonify(utente)


@views.route('/save_alimento', methods=['POST'])
def save_alimento():
    """
    Questa funzione salva un alimento esistente nel database, aggiornandone i dati.
    """
    data = request.get_json()
    alimento_id = data.get('id')
    nome = data.get('nome')
    carboidrati = data.get('carboidrati')
    proteine = data.get('proteine')
    grassi = data.get('grassi')
    frutta = data.get('frutta')
    carne_bianca = data.get('carne_bianca')
    carne_rossa = data.get('carne_rossa')
    pane = data.get('pane')
    verdura = data.get('verdura')
    confezionato = data.get('confezionato')
    vegan = data.get('vegan')
    pesce = data.get('pesce')

    salva_alimento(alimento_id, nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura,
                   confezionato, vegan, pesce)

    return jsonify({'status': 'success', 'message': 'Alimento salvato con successo!'})


@views.route('/delete_alimento', methods=['POST'])
def delete_alimento():
    """
    Questa funzione elimina un alimento dal database basandosi sul suo ID.
    """
    data = request.get_json()
    alimento_id = data.get('id')

    elimina_alimento(alimento_id)

    return jsonify({'status': 'success', 'message': 'Alimento eliminato con successo!'})


@views.route('/get_available_meals', methods=['GET'])
def get_available_meals():
    """
    Questa funzione restituisce le ricette disponibili per un pasto specifico in un giorno specifico,
    escludendo quelle già presenti nel menu corrente.
    """
    meal_type = request.args.get('meal')
    day = request.args.get('day')
    week_id = request.args.get('week_id')

    meal_type_mapping = {
        'colazione': ['colazione', 'colazione_sec'],
        'spuntino_mattina': ['spuntino'],
        'pranzo': ['principale', 'contorno'],
        'cena': ['principale', 'contorno'],
        'spuntino_pomeriggio': ['spuntino']
    }

    generic_meal_types = meal_type_mapping.get(meal_type)

    # Recupera tutte le ricette attive
    ricette = carica_ricette(stagionalita=True, attive=True)

    # Filtra le ricette disponibili in base al tipo di pasto
    available_meals = [ricetta for ricetta in ricette if
                       any(ricetta[generic_meal_type] for generic_meal_type in generic_meal_types)]

    # Esclude le ricette già presenti nel pasto del giorno specificato
    menu_corrente = get_menu_corrente(ids=week_id)
    if menu_corrente:
        ricette_presenti_ids = [r['id'] for r in menu_corrente['day'][day]['pasto'][meal_type]['ricette']]
        available_meals = [ricetta for ricetta in available_meals if ricetta['id'] not in ricette_presenti_ids]

    return jsonify(available_meals)


@views.route('/add_meals_to_menu/<int:week_id>', methods=['POST'])
def add_meals_to_menu(week_id):
    """
    Questa funzione aggiunge uno o più pasti selezionati al menu per una settimana specifica,
    aggiorna i macronutrienti rimanenti e salva il menu aggiornato nel database.
    """
    data = request.get_json()
    day = data['day']
    meal = data['meal']
    selected_meals = data['selectedMeals']

    # Recupera il menu corrente dal database
    menu_corrente = get_menu_corrente(week_id)

    # Aggiunge i pasti selezionati al menu
    for meal_id in selected_meals:
        aggiungi_ricetta_al_menu(menu_corrente, day, meal, meal_id)

    # Ricalcola i macronutrienti rimanenti
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

    # Salva il menu aggiornato nel database
    update_menu_corrente(menu_corrente, week_id)

    return jsonify({
        'status': 'success',
        'menu': menu_corrente,  # Restituisce il menu aggiornato
        'remaining_macronutrienti': remaining_macronutrienti
    })


@views.route('/remove_meal/<int:week_id>', methods=['POST'])
def remove_meal(week_id):
    """
    Questa funzione rimuove un pasto specifico dal menu per un giorno specifico,
    ricalcola i macronutrienti rimanenti e salva il menu aggiornato.
    """
    data = request.get_json()
    day = data['day']
    meal = data['meal']
    meal_id = data['meal_id']

    # Recupera il menu corrente dal database
    menu_corrente = get_menu_corrente(week_id)

    # Rimuove il pasto dal menu
    updated_menu = remove_meal_from_menu(menu_corrente, day, meal, meal_id)

    # Salva il menu aggiornato nel database
    update_menu_corrente(updated_menu, week_id)

    # Ricalcola i macronutrienti rimanenti
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(updated_menu)

    return jsonify({
        'status': 'success',
        'menu': menu_corrente,
        'remaining_macronutrienti': remaining_macronutrienti
    })


@views.route('/update_meal_quantity', methods=['POST'])
def update_meal_quantity():
    """
    Questa funzione aggiorna la quantità di un pasto specifico in un giorno specifico
    e ricalcola i macronutrienti rimanenti.
    """
    data = request.get_json()
    day = data['day']
    meal = data['meal']
    meal_id = data['meal_id']
    quantity = float(data['quantity'])
    week_id = data['week_id']

    # Recupera il menu corrente dal database
    menu_corrente = get_menu_settimana(week_id)

    # Aggiorna la quantità del pasto nel menu
    for ricetta in menu_corrente['day'][day]['pasto'][meal]['ricette']:
        if float(ricetta['id']) == float(meal_id):
            old_qta = ricetta['qta']
            ricetta['qta'] = quantity

            # Ricalcola i macronutrienti giornalieri e settimanali
            for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
                difference = float(ricetta[macro]) * (old_qta - quantity)
                menu_corrente['day'][day][macro] += difference
                menu_corrente['weekly'][macro] += difference

    # Salva il menu aggiornato
    update_menu_corrente(menu_corrente, week_id)

    # Ricalcola i macronutrienti rimanenti
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

    return jsonify({
        'status': 'success',
        'menu': menu_corrente,
        'remaining_macronutrienti': remaining_macronutrienti
    })


@views.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """
    Questa funzione genera un PDF contenente il menu settimanale e la lista della spesa.
    La richiesta contiene l'immagine del menu in formato base64 e l'ID della settimana selezionata.
    """
    data = request.get_json()
    img_data = data['image']
    week_id = data['week_id']

    # Decodifica l'immagine base64 inviata dal client
    img_data = img_data.split(',')[1]
    img = Image.open(BytesIO(base64.b64decode(img_data)))

    # Recupera il menu selezionato dal database
    menu_selezionato = get_menu_settimana(week_id)

    # Imposta il PDF in orientamento orizzontale
    pdf_file = BytesIO()
    c = canvas.Canvas(pdf_file, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Aggiungi margini al PDF
    margin_x = inch * 0.5
    margin_y = inch * 0.5

    # Calcola le dimensioni dell'immagine da inserire nel PDF
    img_width, img_height = img.size
    aspect = img_height / float(img_width)
    img_display_width = width - 2 * margin_x
    img_display_height = img_display_width * aspect

    # Inserisci l'immagine nel PDF con margini
    c.drawImage(ImageReader(img), margin_x, height - img_display_height - margin_y,
                width=img_display_width, height=img_display_height)

    # Aggiungi una nuova pagina al PDF per la lista della spesa
    c.showPage()

    # Aggiungi la lista della spesa al PDF
    y = height - margin_y  # Posiziona la lista sotto l'immagine
    shopping_list = stampa_lista_della_spesa(menu_selezionato.get('all_food'))
    c.setFont("Helvetica", 12)
    c.drawString(margin_x, y, "Lista della Spesa:")
    y -= 20
    for item in shopping_list:
        c.drawString(margin_x + 20, y, f"[ ] {item['alimento']} - {item['qta_totale']}g")
        y -= 15
        if y < margin_y:
            c.showPage()
            y = height - margin_y

    c.save()

    # Ritorna il PDF generato come risposta alla richiesta
    pdf_file.seek(0)
    return send_file(pdf_file, as_attachment=True, download_name='menu_settimanale.pdf', mimetype='application/pdf')