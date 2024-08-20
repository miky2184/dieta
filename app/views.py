from flask import Blueprint, render_template, request, redirect, url_for
from .services.menu_services import (definisci_calorie_macronutrienti, save_weight, genera_menu,
                                     stampa_lista_della_spesa, get_menu_corrente, salva_menu_settimana_prossima,
                                     carica_ricette, get_settimane_salvate, get_menu_settima_prossima,
                                     salva_menu_corrente, get_menu_settimana, get_settimana, salva_ricetta,
                                     attiva_disattiva_ricetta, get_ricette, elimina_ingredienti, salva_utente_dieta,
                                     salva_nuova_ricetta, salva_ingredienti,
                                     recupera_ingredienti, get_peso_hist, get_dati_utente, calcola_macronutrienti_rimanenti,
                                     recupera_alimenti, salva_alimento, elimina_alimento, salva_nuovo_alimento,
                                     aggiungi_ricetta_al_menu, update_menu_corrente, remove_meal_from_menu)
from copy import deepcopy

views = Blueprint('views', __name__)


@views.route('/')
def index():
    # Calcola le calorie e i macronutrienti
    macronutrienti = definisci_calorie_macronutrienti()
    # Recupera le ricette dal database
    ricette = carica_ricette(stagionalita=False)
    # Recupera il menu corrente
    menu_corrente = get_menu_corrente()

    if not menu_corrente:
        ricette_menu = carica_ricette(stagionalita=True)
        settimana_corrente = deepcopy(get_settimana(macronutrienti))
        genera_menu(settimana_corrente, False, ricette_menu)
        genera_menu(settimana_corrente, True, ricette)
        salva_menu_corrente(settimana_corrente)
        menu_corrente = settimana_corrente

    if not get_menu_settima_prossima():
        ricette_menu = carica_ricette(stagionalita=True)
        prossima_settimana = deepcopy(get_settimana(macronutrienti))
        genera_menu(prossima_settimana, False, ricette_menu)
        genera_menu(prossima_settimana, True, ricette)
        salva_menu_settimana_prossima(prossima_settimana)

    # Recupera le settimane salvate per il dropdown
    settimane_salvate = get_settimane_salvate()

    # Recupera la lista della spesa
    lista_spesa = stampa_lista_della_spesa(menu_corrente.get('all_food'))

    # Calcola i macronutrienti rimanenti per ogni giorno
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

    alimenti = recupera_alimenti()

    # Questa sarà la pagina principale, passa i dati al template
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           ricette=ricette,
                           menu=menu_corrente,
                           lista_spesa=lista_spesa,
                           settimane=settimane_salvate,
                           remaining_macronutrienti=remaining_macronutrienti,
                           alimenti=alimenti
                           )


@views.route('/menu_settimana/<int:settimana_id>')
def menu_settimana(settimana_id):

    menu_selezionato = get_menu_settimana(settimana_id)

    macronutrienti_rimanenti = calcola_macronutrienti_rimanenti(menu_selezionato)

    return jsonify({'menu':menu_selezionato, 'remaining_macronutrienti': macronutrienti_rimanenti})


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

    salva_ingredienti(recipe_id, ingredient_id, quantity)

    return jsonify({'status': 'success', 'message': 'Ingrediente inserito correttamente.'})


@views.route('/update_ingredient', methods=['POST'])
def update_ingredient():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    salva_ingredienti(recipe_id, ingredient_id, quantity)

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


@views.route('/new_food', methods=['POST'])
def new_food():
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

    salva_nuovo_alimento(name, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce)

    return redirect(url_for('views.index'))


@views.route('/submit-weight', methods=['POST'])
def submit_weight():
    data = request.json
    # Salva i dati del peso nel database
    peso = save_weight(data['date'], data['weight'])
    return jsonify(peso)


@views.route('/salva-dati', methods=['POST'])
def salva_dati():
    id = request.form['id']
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

    salva_utente_dieta(id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
    meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
    proteine, grassi)

    return redirect(url_for('views.index'))


@views.route('/get_peso_data')
def get_peso_data():
    peso = get_peso_hist()
    return jsonify(peso)


from flask import jsonify


@views.route('/get_data_utente', methods=['GET'])
def get_data_utente():
    utente = get_dati_utente()
    return jsonify(utente)


@views.route('/save_alimento', methods=['POST'])
def save_alimento():
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

    salva_alimento(alimento_id, nome, carboidrati, proteine, grassi, frutta, carne_bianca, carne_rossa, pane, verdura, confezionato, vegan, pesce)

    return jsonify({'status': 'success', 'message': 'Alimento salvato con successo!'})


@views.route('/delete_alimento', methods=['POST'])
def delete_alimento():
    data = request.get_json()
    alimento_id = data.get('id')

    elimina_alimento(alimento_id)

    return jsonify({'status': 'success', 'message': 'Alimento eliminato con successo!'})


@views.route('/get_available_meals')
def get_available_meals():
    meal_type = request.args.get('meal')
    day = request.args.get('day')
    week_id = request.args.get('week_id')

    meal_type_mapping = {
        'colazione': ['colazione', 'colazione_sec'],
        'spuntino_mattina': ['spuntino'],
        'pranzo': ['principale'],
        'cena': ['principale'],
        'spuntino_pomeriggio': ['spuntino']
    }

    generic_meal_types = meal_type_mapping.get(meal_type)

    # Logica per recuperare le ricette disponibili in base al tipo di pasto (colazione, pranzo, cena, ecc.)
    ricette = carica_ricette(stagionalita=True, attive=True)

    # Filtra le ricette disponibili in base ai tipi di pasto (considerando più tipi se necessario)
    available_meals = [ricetta for ricetta in ricette if any(ricetta[generic_meal_type] for generic_meal_type in generic_meal_types)]

    # Filtra ulteriormente per escludere le ricette già presenti nel pasto
    menu_corrente = get_menu_corrente()
    if menu_corrente:
        ricette_presenti_ids = [r['id'] for r in menu_corrente['day'][day]['pasto'][meal_type]['ricette']]
        available_meals = [ricetta for ricetta in available_meals if ricetta['id'] not in ricette_presenti_ids]

    return jsonify(available_meals)


@views.route('/add_meals_to_menu/<int:week_id>', methods=['POST'])
def add_meals_to_menu(week_id):
    data = request.get_json()
    day = data['day']
    meal = data['meal']
    selected_meals = data['selectedMeals']

    # Recupera il menu corrente
    menu_corrente = get_menu_corrente(week_id)

    # Aggiungi i pasti selezionati al menu corrente
    for meal_id in selected_meals:
        aggiungi_ricetta_al_menu(menu_corrente, day, meal, meal_id)

    # Ricalcola i macronutrienti rimanenti
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

    # Salva il menu aggiornato
    update_menu_corrente(menu_corrente, week_id)

    return jsonify({
        'status': 'success',
        'menu': menu_corrente,  # Puoi restituire il menu aggiornato se vuoi aggiornarlo sul client
        'remaining_macronutrienti': remaining_macronutrienti
    })


@views.route('/remove_meal/<int:week_id>', methods=['POST'])
def remove_meal(week_id):
    data = request.get_json()
    day = data['day']
    meal = data['meal']
    meal_id = data['meal_id']

    # Recupera il menu corrente
    menu_corrente = get_menu_corrente(week_id)

    # Rimuovi il pasto
    updated_menu = remove_meal_from_menu(menu_corrente, day, meal, meal_id)

    # Salva il menu aggiornato
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
    data = request.get_json()
    day = data['day']
    meal = data['meal']
    meal_id = data['meal_id']
    quantity = float(data['quantity'])
    week_id = data['week_id']

    # Recupera il menu corrente
    menu_corrente = get_menu_settimana(week_id)

    # Aggiorna la quantità del pasto
    for ricetta in menu_corrente['day'][day]['pasto'][meal]['ricette']:
        if float(ricetta['id']) == float(meal_id):
            old_qta = ricetta['qta']
            ricetta['qta'] = quantity

            # Ricalcola i macronutrienti per il giorno e la settimana
            for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
                # Calcola la differenza in base alla nuova quantità rispetto alla vecchia
                difference = float(ricetta[macro]) * (old_qta - quantity)

                # Aggiorna i valori giornalieri e settimanali
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
