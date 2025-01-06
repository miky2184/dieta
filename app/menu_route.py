import traceback

from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.services.menu_services import (delete_week_menu, genera_menu_utente,
                                        get_gruppi_data)
from app.services.modifica_pasti_services import get_menu_service
from app.services.util_services import calcola_macronutrienti_rimanenti_service

menu = Blueprint('menu', __name__)

@menu.route('/generate_menu', methods=['POST'])
@login_required
def generate_menu():
    """
    Gestisce la generazione del menu settimanale per l'utente.
    """
    user_id = current_user.user_id
    try:
        genera_menu_utente(user_id)

        current_app.cache.delete(f'dashboard_{user_id}')
        return {'status': 'success', 'progress': 100}
        return jsonify(response), 200
    except ValueError as val_err:
        return jsonify({'status': 'error', 'message': str(val_err), 'trace': traceback.format_exc()}), 400
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Errore sconosciuto.', 'details': str(e), 'trace': traceback.format_exc()}), 500


@menu.route('/get_gruppi', methods=['GET'])
@login_required
def get_gruppi():
    try:
        gruppi_data = get_gruppi_data()
        return jsonify({'status': 'success', 'gruppi': gruppi_data})
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@menu.route('/delete_menu/<int:week_id>', methods=['DELETE'])
@login_required
def delete_menu(week_id):
    # Elimina il menu dal database
    user_id = current_user.user_id
    try:
        delete_week_menu(week_id, user_id)

        # Svuota la cache correlata
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu//menu_settimana/{week_id}')
        return jsonify({'status': 'success', 'message': 'Menu eliminato con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@menu.route('/menu_settimana/<int:settimana_id>', methods=['GET'])
@current_app.cache.cached(timeout=300)
@login_required
def menu_settimana(settimana_id):
    """
    Questa funzione gestisce la richiesta di visualizzazione di un menu specifico per una settimana data.
    Restituisce il menu selezionato e i macronutrienti rimanenti per quella settimana.
    """
    user_id = current_user.user_id
    try:
        menu_selezionato = get_menu_service(user_id, ids=settimana_id)
        macronutrienti_rimanenti = calcola_macronutrienti_rimanenti_service(menu_selezionato['menu'])

        return jsonify({'status':'success', 'menu': menu_selezionato['menu'], 'remaining_macronutrienti': macronutrienti_rimanenti}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500
