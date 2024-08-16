from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from .services.menu_services import (definisci_calorie_macronutrienti, save_weight, genera_menu,
                                     stampa_lista_della_spesa, get_menu_corrente, salva_menu_settimana_prossima,
                                     carica_ricette, get_settimane_salvate, get_menu_settima_prossima,
                                     salva_menu_corrente)
from .models.database import get_db_connection
from .models.common import printer
from copy import deepcopy
from decimal import Decimal

views = Blueprint('views', __name__)


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


@views.route('/')
def index():
    # Calcola le calorie e i macronutrienti
    macronutrienti = definisci_calorie_macronutrienti()
    # Recupera le ricette dal database
    ricette = carica_ricette(False)
    # Recupera gli ingredienti delle ricette dal database
    # ingredienti = stampa_ingredienti_ricetta()

    # Recupera il menu corrente
    menu_corrente = get_menu_corrente()

    if not menu_corrente:
        ricette_menu = carica_ricette(True)
        printer(f"macronutrienti:{macronutrienti}")
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
    lista_spesa = stampa_lista_della_spesa(menu_corrente.get('all_food'))

    # Questa sarà la pagina principale, passa i dati al template
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           ricette=ricette,
                           menu=menu_corrente,
                           lista_spesa=lista_spesa,
                           settimane=settimane_salvate
                           )


@views.route('/menu_settimana/<int:settimana_id>')
def menu_settimana(settimana_id):
    menu_selezionato = None
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT menu FROM dieta.menu_settimanale WHERE id = %s
        """, (settimana_id,))
        result = cur.fetchone()
        if result:
            menu_selezionato = result['menu']

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

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE dieta.ricetta SET nome_ricetta = upper(%s), colazione = %s, colazione_sec = %s, spuntino = %s, "
            "principale = %s, contorno = %s WHERE id = %s",
            (nome, colazione, colazione_sec, spuntino, principale, contorno, ricetta_id))
        conn.commit()

    return jsonify({'status': 'success', 'message': 'Ricetta salvata con successo!'})


@views.route('/toggle_recipe_status', methods=['POST'])
def toggle_recipe_status():
    data = request.get_json()
    ricetta_id = data['id']
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE dieta.ricetta SET enabled = not enabled WHERE id = %s", (ricetta_id,))
        conn.commit()

    return jsonify({'status': 'success', 'message': 'Ricetta modificata con successo!'})


@views.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT a.id, a.nome, qta, ir.id_ricetta "
            "  FROM      dieta.ingredienti_ricetta ir "
            "       JOIN dieta.alimento a ON (ir.id_alimento = a.id) "
            " WHERE id_ricetta = %s",
            (recipe_id,))
        ingredients = cur.fetchall()
        # cur.execute("SELECT id, nome FROM dieta.alimento ORDER BY nome;")
        # foods = cur.fetchall()
        # cur.execute("SELECT nome_ricetta FROM dieta.ricetta WHERE id = %s", (recipe_id,))
        # recipe_name = cur.fetchone()[0]

    return jsonify(ingredients)


@views.route('/delete_ingredient', methods=['POST'])
def delete_ingredient():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM dieta.ingredienti_ricetta WHERE id_alimento = %s AND id_ricetta = %s",
                    (ingredient_id, recipe_id))
        conn.commit()

    return jsonify({'status': 'success', 'message': 'Ingrediente eliminato correttamente.'})


@views.route('/get_all_ingredients', )
def get_all_ingredients():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM dieta.alimento ORDER BY nome;")
        foods = cur.fetchall()

    return jsonify(foods)


@views.route('/add_ingredient_to_recipe', methods=['POST'])
def add_ingredient_to_recipe():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO dieta.ingredienti_ricetta (id_ricetta, id_alimento, qta) VALUES (%s, %s, %s)",
                    (recipe_id, ingredient_id, quantity))
        conn.commit()

    return jsonify({'status': 'success', 'message': 'Ingrediente inserito correttamente.'})


@views.route('/update_ingredient', methods=['POST'])
def update_ingredient():
    data = request.get_json()
    ingredient_id = data['ingredient_id']
    recipe_id = data['recipe_id']
    quantity = data['quantity']

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE dieta.ingredienti_ricetta SET qta = %s WHERE id_alimento = %s AND id_ricetta = %s",
                    (quantity, ingredient_id, recipe_id))
        conn.commit()

    return jsonify({'status': 'success', 'message': 'Quantità aggiornata correttamente.'})


@views.route('/new_recipe', methods=['POST'])
def new_recipe():
    name = request.form['name']
    breakfast = 'breakfast' in request.form
    snack = 'snack' in request.form
    main = 'main' in request.form
    side = 'side' in request.form
    second_breakfast = 'second_breakfast' in request.form

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dieta.ricetta (nome_ricetta, colazione, spuntino, principale, contorno, colazione_sec) "
            "    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (name.upper(), breakfast, snack, main, side, second_breakfast))
        conn.commit()

    return redirect(url_for('views.index'))


@views.route('/new_food', methods=['POST'])
def new_food():
    name = request.form['name']
    breakfast = 'breakfast' in request.form
    snack = 'snack' in request.form
    main = 'main' in request.form
    side = 'side' in request.form
    second_breakfast = 'second_breakfast' in request.form

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO dieta.ricetta (nome_ricetta, colazione, spuntino, principale, contorno, colazione_sec) "
            "     VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (name.upper(), breakfast, snack, main, side, second_breakfast))
        conn.commit()

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

    # Connessione al database e inserimento dei dati
    with get_db_connection() as conn:
        cur = conn.cursor()

        query = """
            INSERT INTO dieta.utenti (nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, 
            peso_ideale, meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
            proteine, grassi)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        params = (nome.upper(), cognome.upper(), sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                  meta_basale, meta_giornaliero, calorie_giornaliere, calorie_settimanali, carboidrati,
                  proteine, grassi)

        # Stampa la query con parametri
        printer(cur.mogrify(query, params).decode('utf-8'))

        cur.execute(query, params)
        conn.commit()

    return redirect(url_for('views.index'))
