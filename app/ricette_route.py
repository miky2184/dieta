from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.services.ricette_services import update_ricetta_service, get_ricette_service, attiva_disattiva_ricetta_service, \
    get_ingredienti_ricetta_service, salva_nuova_ricetta, salva_ingredienti_service

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
@current_app.cache.cached(timeout=300, key_prefix=lambda: generate_cache_key())
@login_required
def list_ricette():
    """
    Funzione consolidata per recuperare le ricette in base a filtri dinamici.
    Supporta stagionalità, complemento, contorno e filtri per tipo di pasto.
    """
    user_id = current_user.user_id

    # Parametri dinamici dai query string
    stagionalita = request.args.get('stagionalita', 'false').lower() == 'true'
    complemento = request.args.get('complemento', 'false').lower() == 'true'
    contorno = request.args.get('contorno', 'false').lower() == 'true'
    attive = request.args.get('attive', 'false').lower() == 'true'
    meal_type = request.args.get('meal')

    # Mappatura dei tipi di pasto (opzionale)
    meal_type_mapping = {
        'colazione': ['colazione', 'colazione_sec'],
        'spuntino_mattina': ['spuntino'],
        'pranzo': ['principale'],
        'spuntino_pomeriggio': ['spuntino'],
        'cena': ['principale'],
        'spuntino_sera': ['spuntino']
    }

    generic_meal_types = meal_type_mapping.get(meal_type)

    try:
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
                ricetta for ricetta in ricette_list if
                any(ricetta[generic_meal_type] for generic_meal_type in generic_meal_types)
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
