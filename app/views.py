from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from .services.menu_services import (definisci_calorie_macronutrienti, save_weight, genera_menu,
                                     stampa_lista_della_spesa, get_menu_corrente, salva_menu_settimana_prossima,
                                     carica_ricette, get_settimane_salvate, get_menu_settima_prossima,
                                     salva_menu_corrente, get_menu_settimana, get_settimana, salva_ricetta,
                                     attiva_disattiva_ricetta, get_ricette, elimina_ingredienti, salva_utente_dieta,
                                     salva_nuova_ricetta, aggiorna_ingredienti, aggiungi_ingredienti,
                                     recupera_ingredienti)
from copy import deepcopy

views = Blueprint('views', __name__)


@views.route('/')
def index():
    # Calcola le calorie e i macronutrienti
    macronutrienti = definisci_calorie_macronutrienti()
    # Recupera le ricette dal database
    ricette = carica_ricette(False)
    # Recupera il menu corrente
    menu_corrente = get_menu_corrente()

    if not menu_corrente:
        ricette_menu = carica_ricette(True)
        settimana_corrente = deepcopy(get_settimana(macronutrienti))
        genera_menu(settimana_corrente, False, ricette_menu)
        genera_menu(settimana_corrente, True, ricette)
        salva_menu_corrente(settimana_corrente)
        menu_corrente = settimana_corrente

    if not get_menu_settima_prossima():
        ricette_menu = carica_ricette(True)
        prossima_settimana = deepcopy(get_settimana(macronutrienti))
        genera_menu(prossima_settimana, False, ricette_menu)
        genera_menu(prossima_settimana, True, ricette)
        salva_menu_settimana_prossima(prossima_settimana)

    # Recupera le settimane salvate per il dropdown
    settimane_salvate = get_settimane_salvate()

    # Recupera la lista della spesa
    #lista_spesa = stampa_lista_della_spesa(menu_corrente.get('all_food'))

    # Questa sarà la pagina principale, passa i dati al template
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           ricette=ricette,
                           menu=menu_corrente,
                           #lista_spesa=lista_spesa,
                           settimane=settimane_salvate
                           )


@views.route('/menu_settimana/<int:settimana_id>')
def menu_settimana(settimana_id):

    menu_selezionato = get_menu_settimana(settimana_id)

    return jsonify(menu=menu_selezionato)


@views.route('/get_lista_spesa', methods=['POST'])
def get_lista_spesa():
    data = request.get_json()
    ids_all_food = data.get('ids_all_food', [])

    # Usa la funzione stampa_lista_della_spesa per ottenere la lista della spesa
    lista_spesa = stampa_lista_della_spesa(ids_all_food)

    return jsonify(lista_spesa=lista_spesa)


@views.route('/save_recipe', methods=['POST'])
def save_recipe():
    data = request.get_json()
    ricetta_id = data['id']
    colazione = data['colazione']
    colazione_sec = data['colazione_sec']
    spuntino = data['spuntino']
    principale = data['principale']
    contorno = data['contorno']
    nome = data['nome']

    salva_ricetta(nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id)

    return jsonify({'status': 'success', 'message': 'Ricetta salvata con successo!'})


@views.route('/toggle_recipe_status', methods=['POST'])
def toggle_recipe_status():
    data = request.get_json()
    ricetta_id = data['id']

    attiva_disattiva_ricetta(ricetta_id)

    return jsonify({'status': 'success', 'message': 'Ricetta modificata con successo!'})


@views.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):

    return jsonify(get_ricette(recipe_id))


@views.route('/delete_ingredient', methods=['POST'])
def delete_ingredient():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']

    elimina_ingredienti(ingredient_id, recipe_id)

    return jsonify({'status': 'success', 'message': 'Ingrediente eliminato correttamente.'})


@views.route('/get_all_ingredients', )
def get_all_ingredients():
    return jsonify(recupera_ingredienti())


@views.route('/add_ingredient_to_recipe', methods=['POST'])
def add_ingredient_to_recipe():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    aggiungi_ingredienti(recipe_id, ingredient_id, quantity)

    return jsonify({'status': 'success', 'message': 'Ingrediente inserito correttamente.'})


@views.route('/update_ingredient', methods=['POST'])
def update_ingredient():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    aggiorna_ingredienti(recipe_id, ingredient_id, quantity)

    return jsonify({'status': 'success', 'message': 'Quantità aggiornata correttamente.'})


@views.route('/new_recipe', methods=['POST'])
def new_recipe():
    name = request.form['name']
    breakfast = 'breakfast' in request.form
    snack = 'snack' in request.form
    main = 'main' in request.form
    side = 'side' in request.form
    second_breakfast = 'second_breakfast' in request.form

    salva_nuova_ricetta(name.upper(), breakfast, snack, main, side, second_breakfast)

    return redirect(url_for('views.index'))


@views.route('/submit-weight', methods=['POST'])
def submit_weight():
    data = request.json
    # Salva i dati del peso nel database
    peso = save_weight(data['date'], data['weight'])
    return jsonify(peso)


@views.route('/salva-dati', methods=['POST'])
def salva_dati():
    nome = request.form['nome']
    cognome = request.form['cognome']
    sesso = request.form['sesso']
    eta = int(request.form['eta'])
    altezza = float(request.form['altezza'])
    peso = float(request.form['peso'])
    tdee = float(request.form['tdee'])
    deficit_calorico = float(request.form['deficit_calorico'])
    bmi = float(request.form['bmi'])
    peso_ideale = float(request.form['peso_ideale'])
    meta_basale = float(request.form['meta_basale'])
    meta_giornaliero = float(request.form['meta_giornaliero'])
    calorie_giornaliere = float(request.form['calorie_giornaliere'])
    calorie_settimanali = float(request.form['calorie_settimanali'])
    carboidrati = float(request.form['carboidrati'])
    proteine = float(request.form['proteine'])
    grassi = float(request.form['grassi'])

    salva_utente_dieta(nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
    meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
    proteine, grassi)

    return redirect(url_for('views.index'))
