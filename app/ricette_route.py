from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from app.services.modifica_pasti_services import get_menu_service
from app.services.ricette_services import update_ricetta_service, get_ricette_service, attiva_disattiva_ricetta_service, \
    get_ingredienti_ricetta_service, salva_nuova_ricetta, salva_ingredienti_service, delete_ricetta_service

ricette = Blueprint('ricette', __name__)

def generate_cache_key():
    """
    Genera una chiave cache unica basata sui parametri della richiesta.
    """
    user_id = current_user.user_id
    stagionalita = request.args.get('stagionalita', 'false').lower()
    complemento = request.args.get('complemento', 'false').lower()
    contorno = request.args.get('contorno', 'false').lower()
    attive = request.args.get('attive', 'false').lower()
    meal = request.args.get('meal', 'none')

    # Genera una chiave univoca
    return f"ricette_{user_id}_{stagionalita}_{complemento}_{contorno}_{attive}_{meal}"


def invalidate_cache(user_id):
    """
    Invalida tutte le chiavi di cache associate alle ricette dell'utente.
    """
    cache_keys = [
        f"ricette_{user_id}_{stagionalita}_{complemento}_{contorno}_{attive}_{meal}"
        for stagionalita in ['true', 'false']
        for complemento in ['true', 'false']
        for contorno in ['true', 'false']
        for attive in ['true', 'false']
        for meal in ['colazione', 'pranzo', 'cena', 'spuntino', 'none']
    ]
    for key in cache_keys:
        current_app.cache.delete(key)


@ricette.route('/ricette', methods=['GET'])
@login_required
def handle_ricette():
    """
    Funzione consolidata per gestire entrambe le richieste:
    - Recuperare ricette in base a filtri dinamici.
    - Recuperare ricette disponibili per un pasto specifico, escludendo quelle già presenti.
    """
    user_id = current_user.user_id

    # Parametri dinamici dai query string
    stagionalita = request.args.get('stagionalita', 'false').lower() == 'true'
    complemento = request.args.get('complemento', 'all').lower()
    contorno = request.args.get('contorno', 'false').lower() == 'true'
    attive = request.args.get('attive', 'false').lower() == 'true'
    meal_time = request.args.get('meal_time')
    meal_type = request.args.get('meal_type')
    day = request.args.get('day') if request.args.get('day') != 'undefined' else None  # Per menu specifico
    week_id = request.args.get('week_id')  # Per menu specifico

    # Mappatura dei tipi di pasto (opzionale)
    meal_type_mapping = {
        'colazione': ['colazione', 'colazione_sec'],
        'spuntino_mattina': ['spuntino'],
        'pranzo': ['principale', 'contorno'],
        'spuntino_pomeriggio': ['spuntino'],
        'cena': ['principale', 'contorno'],
        'spuntino_sera': ['spuntino'],
        'complemento': []
    }

    generic_meal_types = meal_type_mapping.get(meal_time, [])
    generic_meal_types = [meal_type] if meal_type in generic_meal_types else generic_meal_types

    try:

        # Logica aggiuntiva per le ricette disponibili (se day e week_id sono specificati)
        if day and week_id:
            menu_corrente = get_menu_service(user_id, menu_id=week_id)

            # Recupera la data di fine stagionalità dal menu corrente
            data_stagionalita = menu_corrente.get('data_fine')

            # Aggiorna la lista delle ricette con i dati stagionali
            ricette_list = get_ricette_service(
                user_id,
                stagionalita=True,
                attive=True,
                complemento='no',
                data_stagionalita=data_stagionalita
            )

            if menu_corrente['menu']:
                if meal_time in ('pranzo', 'cena'):
                    ricette_presenti_ids = menu_corrente['menu']['all_food']
                else:
                    ricette_presenti_ids = [
                        r['id'] for r in menu_corrente['menu']['day'][day]['pasto'][meal_time]['ricette']
                    ]

                # Ordina le ricette: prima quelle non presenti nel menu, poi quelle già presenti
                ricette_list.sort(key=lambda ricetta: ricetta['id'] in ricette_presenti_ids)
        else:
            # Recupera le ricette dal servizio
            ricette_list = get_ricette_service(
                user_id,
                stagionalita=stagionalita,
                complemento=complemento,
                contorno=contorno,
                attive=attive
            )

        # Filtra ulteriormente in base al tipo di pasto, se specificato
        if generic_meal_types:
            ricette_list = [
                ricetta for ricetta in ricette_list
                if any(ricetta.get(meal_key, False) for meal_key in generic_meal_types)
            ]

        return jsonify({"status": 'success', 'ricette': ricette_list}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/ricetta', methods=['POST'])
@login_required
def create_ricetta():
    """
    Questa funzione salva una nuova ricetta basata sui dati forniti dal form.
    """
    user_id = current_user.user_id
    try:
        name = request.form['name']
        breakfast = 'colazione' in request.form
        snack = 'spuntino' in request.form
        main = 'principale' in request.form
        side = 'contorno' in request.form
        second_breakfast = 'colazione/biscotti' in request.form
        complemento = 'complemento' in request.form

        salva_nuova_ricetta(name.upper(), breakfast, snack, main, side, second_breakfast, complemento, user_id)
        current_app.cache.delete(invalidate_cache(user_id))

        return jsonify({"status": "success"}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/ricette/<int:ricetta_id>', methods=['PUT'])
@login_required
def update_ricetta(ricetta_id):
    """
    Questa funzione salva o aggiorna una ricetta nel database in base ai dati forniti dal client.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        colazione = data['colazione']
        colazione_sec = data['colazione_sec']
        spuntino = data['spuntino']
        principale = data['principale']
        contorno = data['contorno']
        nome = data['nome']
        complemento = data['complemento']

        update_ricetta_service(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id)

        current_app.cache.delete(invalidate_cache(user_id))
        return jsonify({'status': 'success', 'message': 'Ricetta salvata con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/ricette/<int:ricetta_id>/stato', methods=['PATCH'])
@login_required
def toggle_ricetta(ricetta_id):
    """
    Questa funzione attiva o disattiva una ricetta specifica nel database, basandosi sull'ID della ricetta.
    """
    user_id = current_user.user_id
    try:
        attiva_disattiva_ricetta_service(ricetta_id, user_id)
        current_app.cache.delete(invalidate_cache(user_id))
        return jsonify({'status': 'success', 'message': 'Ricetta modificata con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/ingredienti_ricetta/<int:recipe_id>', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"ricette_{request.view_args['recipe_id']}_{current_user.user_id}")
@login_required
def get_ricetta(recipe_id):
    """
    Questa funzione restituisce i dettagli di una ricetta specifica basata sul suo ID.
    """
    user_id = current_user.user_id
    try:
        res = get_ingredienti_ricetta_service(recipe_id, user_id)
        return jsonify({'status': 'success', 'ricette': res}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/aggiorna_ingredienti_ricetta', methods=['POST'])
@login_required
def aggiorna_ingredienti_ricetta():
    """
    Questa funzione aggiorna la quantità di un ingrediente specifico in una ricetta.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ingredient_id = data['ingredient_id']
        recipe_id = data['recipe_id']
        quantity = data['quantity']

        salva_ingredienti_service(recipe_id, ingredient_id, quantity, user_id)
        current_app.cache.delete(invalidate_cache(user_id))
        current_app.cache.delete(f'ricette_{recipe_id}_{user_id}')
        return jsonify({'status': 'success', 'message': 'Quantità aggiornata correttamente.'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/ricette/<int:ricette_id>', methods=['DELETE'])
@login_required
def delete_ricetta(ricette_id):
    """
    Questa funzione elimina un alimento dal database basandosi sul suo ID.
    """
    user_id = current_user.user_id
    try:
        delete_ricetta_service(ricette_id, user_id)
        current_app.cache.delete(invalidate_cache(user_id))
        return jsonify({'status': 'success', 'message': 'Ricetta eliminata con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
