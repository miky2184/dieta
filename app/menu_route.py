import traceback

from flask import Blueprint, jsonify, current_app, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.models.GruppoAlimentare import GruppoAlimentare
from app.services.menu_services import delete_week_menu_service, genera_menu_utente_service, completa_menu_service
from app.services.modifica_pasti_services import get_menu_service
from app.services.util_services import calcola_macronutrienti_rimanenti_service
from app.models.MenuSettimanale import MenuSettimanale

menu = Blueprint('menu', __name__)

@menu.route('/generate_menu', methods=['POST'])
@login_required
def generate_menu():
    """
    Gestisce la generazione del menu settimanale per l'utente.
    """
    user_id = current_user.user_id
    try:
        genera_menu_utente_service(user_id)

        #current_app.cache.delete(f'dashboard_{user_id}')
        return {'status': 'success', 'progress': 100}
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
        return jsonify({'status': 'success', 'gruppi': GruppoAlimentare.get_all()})
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


from datetime import date

@menu.route('/delete_menu/<int:week_id>', methods=['DELETE'])
@login_required
def delete_menu(week_id):
    user_id = current_user.user_id
    try:
        # Recupera il menu dal database
        menu_da_cancellare = MenuSettimanale.query.filter_by(id=week_id, user_id=user_id).first()

        if not menu_da_cancellare:
            return jsonify({'status': 'error', 'message': 'Menu non trovato.'}), 404

        # Controlla se la data corrente è maggiore della data di inizio del menu
        if date.today() >= menu_da_cancellare.data_inizio:
            return jsonify({
                'status': 'error',
                'message': 'Il menu non può essere eliminato perché la data corrente è maggiore della data di inizio.'
            }), 400

        # Elimina il menu se il controllo passa
        delete_week_menu_service(week_id, user_id)

        # Svuota la cache correlata
        #current_app.cache.delete(f'dashboard_{user_id}')
        #current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')
        return jsonify({'status': 'success', 'message': 'Menu eliminato con successo!'}), 200

    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@menu.route('/menu_settimana/<int:settimana_id>', methods=['GET'])
#@current_app.cache.cached(timeout=300, key_prefix=lambda: f"menu_settimana_{request.view_args['settimana_id']}_{current_user.user_id}")
@login_required
def menu_settimana(settimana_id):
    """
    Questa funzione gestisce la richiesta di visualizzazione di un menu specifico per una settimana data.
    Restituisce il menu selezionato e i macronutrienti rimanenti per quella settimana.
    """
    user_id = current_user.user_id
    try:
        menu_selezionato = get_menu_service(user_id, menu_id=settimana_id)
        macronutrienti_rimanenti = calcola_macronutrienti_rimanenti_service(menu_selezionato['menu'])

        return jsonify({'status':'success', 'menu': menu_selezionato['menu'], 'remaining_macronutrienti': macronutrienti_rimanenti}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@menu.route('/complete_menu/<int:week_id>', methods=['POST'])
@login_required
def complete_menu(week_id: int):
    """
        Gestisce il completamento di un menu parziale
    """
    user_id = current_user.user_id
    try:
        completa_menu_service(week_id, user_id)
        return {'status': 'success', 'progress': 100}
    except ValueError as val_err:
        return jsonify({'status': 'error', 'message': str(val_err), 'trace': traceback.format_exc()}), 400
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err),
                        'trace': traceback.format_exc()}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Errore sconosciuto.', 'details': str(e),
                        'trace': traceback.format_exc()}), 500

