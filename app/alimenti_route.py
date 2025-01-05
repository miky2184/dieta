from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, current_app
from app.services.menu_services import (get_utente, save_weight, genera_menu,
                                        stampa_lista_della_spesa, get_menu,
                                        get_ricette_service, get_settimane_salvate,
                                        salva_menu, get_settimana,
                                        elimina_ingredienti, salva_utente_dieta,
                                        salva_nuova_ricetta, salva_ingredienti,
                                        get_peso_hist, get_dati_utente,
                                        calcola_macronutrienti_rimanenti,
                                        aggiungi_ricetta_al_menu, update_menu_corrente, rimuovi_pasto_dal_menu,
                                        delete_week_menu, ordina_settimana_per_kcal, genera_menu_utente,
                                        recupera_ricette_per_alimento, copia_menu, recupera_settimane, cancella_tutti_pasti_menu,
                                        recupera_ingredienti_ricetta, get_gruppi_data)
from app.services.alimenti_services import create_alimento_service, get_alimenti_service, update_alimento_service, delete_alimento_service
from app.services.ricette_services import create_ricetta_service, get_ricette_service, attiva_disattiva_ricetta_service
from copy import deepcopy
import time
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from io import BytesIO
import base64
from PIL import Image
from flask_login import login_required, current_user
from app.models.models import db
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

alimenti = Blueprint('alimenti', __name__)


@alimenti.route('/alimenti', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"alimenti_{current_user.user_id}")
@login_required
def get_alimenti():
    user_id = current_user.user_id
    try:
        # Recupera tutti gli alimenti dal database.
        alimenti = get_alimenti_service(user_id)
        return jsonify({'status': 'success', 'alimenti': alimenti}), 200
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
        current_app.cache.delete(f'alimenti_{user_id}')
        current_app.cache.delete(f'list_ricette_{user_id}')

        return jsonify({'status': 'success'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@alimenti.route('/alimenti/<int:id>', methods=['PUT'])
@login_required
def update_alimento(id):
    """
    Questa funzione salva un alimento esistente nel database, aggiornandone i dati.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        alimento_id = data.get('id')
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


@alimenti.route('/alimenti/<int:id>', methods=['DELETE'])
@login_required
def delete_alimento(id):
    """
    Questa funzione elimina un alimento dal database basandosi sul suo ID.
    """
    user_id = current_user.user_id
    try:
        delete_alimento_service(id, user_id)
        current_app.cache.delete(f'alimenti_{user_id}')
        current_app.cache.delete(f'alimenti_{user_id}')
        return jsonify({'status': 'success', 'message': 'Alimento eliminato con successo!'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500