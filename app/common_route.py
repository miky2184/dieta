import traceback

from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.services.menu_services import (stampa_lista_della_spesa,
                                        recupera_settimane)
from app.services.modifica_pasti_services import get_menu_service

common = Blueprint('common', __name__)

@common.route('/get_weeks', methods=['GET'])
@login_required
def get_weeks():
    user_id = current_user.user_id
    try:
        weeks_list = recupera_settimane(user_id)
        return jsonify({'status': 'success', 'weeks': weeks_list}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@common.route('/get_lista_spesa/<int:settimana_id>', methods=['GET'])
@login_required
def get_lista_spesa(settimana_id):
    """
    Questa funzione gestisce la richiesta POST per ottenere la lista della spesa basata sugli ID degli alimenti
    forniti dal client. Restituisce la lista della spesa corrispondente.
    """
    user_id = current_user.user_id
    try:
        menu = get_menu_service(user_id, menu_id=settimana_id)

        # Genera la lista della spesa basata sugli ID degli alimenti.
        lista_spesa = stampa_lista_della_spesa(user_id, menu['menu'])

        return jsonify({'status': 'success', 'lista_spesa': lista_spesa}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500