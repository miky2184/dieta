from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from .services.menu_services import (definisci_calorie_macronutrienti, stampa_ricette, stampa_ingredienti_ricetta, genera_menu,
                  stampa_lista_della_spesa, orig_settimana, get_menu_corrente, salva_menu_settimana_prossima, carica_ricette,
                  get_settimane_salvate, get_menu_settima_prossima, salva_menu_corrente)
from .models.database import get_db_connection
from .models.common import printer
from copy import deepcopy
views = Blueprint('views', __name__)

@views.route('/')
def index():
    # Calcola le calorie e i macronutrienti
    macronutrienti = definisci_calorie_macronutrienti()
    # Recupera le ricette dal database
    ricette = carica_ricette()
    # Recupera gli ingredienti delle ricette dal database
    ingredienti = stampa_ingredienti_ricetta()

    # Recupera il menu corrente
    menu_corrente = get_menu_corrente()

    if not menu_corrente:
        settimana_corrente = deepcopy(orig_settimana)
        settimana_corrente = genera_menu(settimana_corrente, False, ricette)
        genera_menu(settimana_corrente, True, ricette)
        salva_menu_corrente(settimana_corrente)
        menu_corrente = settimana_corrente

    if not get_menu_settima_prossima():
        prossima_settimana = deepcopy(orig_settimana)
        prossima_settimana =  genera_menu(prossima_settimana, False, ricette)
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
                           ingredienti=ingredienti,
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
            "UPDATE dieta.ricetta SET nome_ricetta = upper(%s), colazione = %s, colazione_sec = %s, spuntino = %s, principale = %s, contorno = %s WHERE id = %s",
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
            "SELECT a.id, a.nome, qta, ir.id_ricetta FROM dieta.ingredienti_ricetta ir JOIN dieta.alimento a ON (ir.id_alimento = a.id) WHERE id_ricetta = %s",
            (recipe_id,))
        ingredients = cur.fetchall()
        #cur.execute("SELECT id, nome FROM dieta.alimento ORDER BY nome;")
        #foods = cur.fetchall()
        #cur.execute("SELECT nome_ricetta FROM dieta.ricetta WHERE id = %s", (recipe_id,))
        #recipe_name = cur.fetchone()[0]

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


@views.route('/get_all_ingredients',)
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
