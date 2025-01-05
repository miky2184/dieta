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
from app.services.ricette_services import create_ricetta_service, get_ricette_service, attiva_disattiva_ricetta_service, get_ingredienti_ricetta_service
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


@ricette.route('/ricette', methods=['POST'])
@login_required
def create_ricetta():
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

        create_ricetta_service(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id)

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
def toggle_ricetta(id):
    """
    Questa funzione attiva o disattiva una ricetta specifica nel database, basandosi sull'ID della ricetta.
    """
    user_id = current_user.user_id
    try:
        ricetta_id = id
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