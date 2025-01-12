from copy import deepcopy

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.services.menu_services import (aggiungi_ricetta_al_menu, rimuovi_pasto_dal_menu,
                                        cancella_tutti_pasti_menu)
from app.services.modifica_pasti_services import get_menu_service, update_menu_corrente_service
from app.services.ricette_services import get_ricette_service
from app.services.util_services import calcola_macronutrienti_rimanenti_service

pasti = Blueprint('pasti', __name__)


@pasti.route('/copy_week', methods=['POST'])
@login_required
def copy_week():
    user_id = current_user.user_id
    try:
        data = request.json
        week_from = data.get('week_from')
        week_to = data.get('week_to')
        # Ottieni il menu della settimana di origine
        menu_from = get_menu_service(current_user.user_id, menu_id=week_from)

        if not menu_from:
            return jsonify({'status': 'error', 'message': 'Settimana non trovata.'}), 404

        # Copia il menu dalla settimana di origine alla settimana di destinazione
        update_menu_corrente_service(menu_from['menu'], week_to, user_id)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu_settimana_{week_to}_{current_user}')
        return jsonify({'status': 'success'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@pasti.route('/inverti_pasti_giorni/<int:week_id>', methods=['POST'])
@login_required
def inverti_pasti_giorni(week_id):
    user_id = current_user.user_id
    try:
        data = request.json
        day1 = data.get('day1')
        day2 = data.get('day2')

        # Recupera il menu della settimana per l'utente
        settimana = get_menu_service(user_id, menu_id=week_id)

        if not settimana:
            return jsonify({'status': 'error', 'message': 'Menu non trovato'}), 404

        # Inverti i pasti dei due giorni specificati
        temp_day = deepcopy(settimana['menu']['day'][day1])
        settimana['menu']['day'][day1] = deepcopy(settimana['menu']['day'][day2])
        settimana['menu']['day'][day2] = temp_day

        # Salva le modifiche nel database
        update_menu_corrente_service(settimana['menu'], week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(settimana['menu'])
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')

        return jsonify({
            'status': 'success',
            'menu': settimana['menu'],
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@pasti.route('/inverti_pasti/<int:week_id>', methods=['POST'])
@login_required
def inverti_pasti(week_id):
    user_id = current_user.user_id
    try:
        data = request.json
        day = data.get('day')

        # Recupera il menu della settimana per l'utente
        settimana = get_menu_service(user_id, menu_id=week_id)

        if not settimana:
            return jsonify({'status': 'error', 'message': 'Menu non trovato'}), 404

        # Inverti i pasti per il giorno specificato
        pranzo = settimana['menu']['day'][day]['pasto']['pranzo']
        cena = settimana['menu']['day'][day]['pasto']['cena']

        settimana['menu']['day'][day]['pasto']['pranzo'] = cena
        settimana['menu']['day'][day]['pasto']['cena'] = pranzo

        # Salva le modifiche nel database
        update_menu_corrente_service(settimana['menu'], week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(settimana['menu'])
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')
        return jsonify({
            'status': 'success',
            'menu': settimana['menu'],
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@pasti.route('/cancella_pasto/<int:week_id>', methods=['POST'])
@login_required
def cancella_pasto(week_id):
    user_id = current_user.user_id
    try:
        data = request.json
        day = data.get('day')
        meal_type = data.get('meal_type')

        # Recupera il menu della settimana per l'utente
        settimana = get_menu_service(user_id, menu_id=week_id)

        if not settimana:
            return jsonify({'status': 'error', 'message': 'Menu non trovato'}), 404

        meal_mapping = {
            'colazione': ['colazione'],
            'principali': ['pranzo', 'cena'],
            'spuntini': ['spuntino_mattina', 'spuntino_pomeriggio', 'spuntino_sera'],
            'all': ['colazione', 'pranzo', 'cena', 'spuntino_mattina', 'spuntino_pomeriggio', 'spuntino_sera']
        }

        for meal in meal_mapping.get(meal_type, []):
            cancella_tutti_pasti_menu(settimana['menu'], day, meal, user_id)

        # Salva le modifiche nel database
        update_menu_corrente_service(settimana['menu'], week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(settimana['menu'])
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')
        return jsonify({
            'status': 'success',
            'menu': settimana['menu'],
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@pasti.route('/aggiungi_ricetta_menu/<int:week_id>', methods=['POST'])
@login_required
def aggiungi_ricetta_menu(week_id):
    """
    Questa funzione aggiunge uno o più pasti selezionati al menu per una settimana specifica,
    aggiorna i macronutrienti rimanenti e salva il menu aggiornato nel database.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        day = data['day']
        meal = data['meal']
        selected_meals = data['selectedMeals']

        # Recupera il menu corrente dal database
        menu_corrente = get_menu_service(user_id, menu_id=week_id)

        # Aggiunge i pasti selezionati al menu
        for meal_id in selected_meals:
            aggiungi_ricetta_al_menu(menu_corrente['menu'], day, meal, meal_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(menu_corrente['menu'])

        # Salva il menu aggiornato nel database
        update_menu_corrente_service(menu_corrente['menu'], week_id, user_id)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')
        return jsonify({
            'status': 'success',
            'menu': menu_corrente['menu'],  # Restituisce il menu aggiornato
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@pasti.route('/rimuovi_ricetta/<int:week_id>', methods=['POST'])
@login_required
def rimuovi_ricetta(week_id):
    """
    Questa funzione rimuove un pasto specifico dal menu per un giorno specifico,
    ricalcola i macronutrienti rimanenti e salva il menu aggiornato.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        day = data['day']
        meal = data['meal']
        meal_id = data['meal_id']

        # Recupera il menu corrente dal database
        menu_corrente = get_menu_service(user_id, menu_id=week_id)

        # Rimuove il pasto dal menu
        rimuovi_pasto_dal_menu(menu_corrente['menu'], day, meal, meal_id, user_id)

        # Salva il menu aggiornato nel database
        update_menu_corrente_service(menu_corrente['menu'], week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(menu_corrente['menu'])
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')
        return jsonify({
            'status': 'success',
            'menu': menu_corrente['menu'],
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500