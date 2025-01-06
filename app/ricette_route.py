from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.services.ricette_services import update_ricetta_service, get_ricette_service, attiva_disattiva_ricetta_service, \
    get_ingredienti_ricetta_service, salva_nuova_ricetta

ricette = Blueprint('ricette', __name__)


@ricette.route('/ricette', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"list_ricette_{current_user.user_id}")
@login_required
def list_ricette():
    user_id = current_user.user_id
    try:
        # Recupera le ricette disponibili dal database.
        ricette = get_ricette_service(user_id, stagionalita=False)
        return jsonify({"status": 'success', 'ricette': ricette}), 200
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
        current_app.cache.delete(f'list_ricette_{user_id}')

        return jsonify({"status": "success"}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ricette.route('/ricette/<int:id>', methods=['PUT'])
@login_required
def update_ricetta(id):
    """
    Questa funzione salva o aggiorna una ricetta nel database in base ai dati forniti dal client.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ricetta_id = data['id']
        colazione = data['colazione']
        colazione_sec = data['colazione_sec']
        spuntino = data['spuntino']
        principale = data['principale']
        contorno = data['contorno']
        nome = data['nome']
        complemento = data['complemento']

        update_ricetta_service(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id)

        current_app.cache.delete(f'list_ricette_{user_id}')
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
        current_app.cache.delete(f'list_ricette_{user_id}')
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
        ricette = get_ingredienti_ricetta_service(recipe_id, user_id)
        return jsonify({'status': 'success', 'ricette': ricette}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



