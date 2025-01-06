from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.ricette_route import invalidate_cache
from app.services.alimenti_services import create_alimento_service, get_alimenti_service, update_alimento_service, \
    delete_alimento_service

alimenti = Blueprint('alimenti', __name__)


@alimenti.route('/alimenti', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"alimenti_{current_user.user_id}")
@login_required
def get_alimenti():
    user_id = current_user.user_id
    try:
        # Recupera tutti gli alimenti dal database.
        return jsonify({'status': 'success', 'alimenti': get_alimenti_service(user_id)}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@alimenti.route('/alimento', methods=['POST'])
@login_required
def create_alimento():
    """
    Questa funzione salva un nuovo alimento basato sui dati forniti dal form.
    """
    user_id = current_user.user_id
    try:
        name = request.form['alimento']
        carboidrati = request.form['carbs']
        proteine = request.form['prot']
        grassi = request.form['fat']
        fibre = request.form['fibre']
        confezionato = 'confezionato' in request.form
        vegan = 'vegan' in request.form
        gruppo = request.form['gruppo']

        create_alimento_service(name, carboidrati, proteine, grassi, fibre,
                                confezionato, vegan, gruppo, user_id)

        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'alimenti_{user_id}')
        current_app.cache.delete(invalidate_cache(user_id))

        return jsonify({'status': 'success'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@alimenti.route('/alimenti/<int:alimento_id>', methods=['PUT'])
@login_required
def update_alimento(alimento_id):
    """
    Questa funzione salva un alimento esistente nel database, aggiornandone i dati.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        nome = data.get('nome')
        carboidrati = data.get('carboidrati')
        proteine = data.get('proteine')
        grassi = data.get('grassi')
        fibre = data.get('fibre')
        confezionato = data.get('confezionato')
        vegan = data.get('vegan')
        gruppo = data.get('gruppo')

        update_alimento_service(alimento_id, nome, carboidrati, proteine, grassi, fibre, confezionato, vegan, gruppo, user_id)
        current_app.cache.delete(f'alimenti_{user_id}')
        current_app.cache.delete(f'alimenti_{user_id}')
        return jsonify({'status': 'success', 'message': 'Alimento salvato con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@alimenti.route('/alimenti/<int:alimento_id>', methods=['DELETE'])
@login_required
def delete_alimento(alimento_id):
    """
    Questa funzione elimina un alimento dal database basandosi sul suo ID.
    """
    user_id = current_user.user_id
    try:
        delete_alimento_service(alimento_id, user_id)
        current_app.cache.delete(f'alimenti_{user_id}')
        return jsonify({'status': 'success', 'message': 'Alimento eliminato con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500