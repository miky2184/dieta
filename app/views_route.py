import base64
import traceback
from datetime import datetime
from io import BytesIO

from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, current_app
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.models.Utente import Utente
from app.services.menu_services import (save_weight, stampa_lista_della_spesa,
                                        get_settimane_salvate,
                                        elimina_ingredienti, salva_utente_dieta,
                                        salva_ingredienti,
                                        get_peso_hist,
                                        recupera_ricette_per_alimento, recupera_ingredienti_ricetta,
                                        get_totale_gruppi_service)
from app.services.modifica_pasti_services import get_menu_service
from app.services.modifica_pasti_services import update_menu_corrente_service
from app.services.util_services import calcola_macronutrienti_rimanenti_service

views = Blueprint('views', __name__)


@views.route('/dashboard', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"dashboard_{current_user.user_id}")
@login_required
def dashboard():
    """
    Questa funzione gestisce la route principale (/) e restituisce la pagina principale con il menu settimanale,
    le ricette, i macronutrienti e altri dati rilevanti. Se il menu corrente non esiste, viene creato un menu vuoto.
    """
    user_id = current_user.user_id
    # Calcola le calorie e i macronutrienti giornalieri dell'utente.
    macronutrienti = Utente.get_by_id(user_id)

    period = {
        "data_inizio": datetime.now().date(),
        "data_fine": datetime.now().date()
    }
    # Recupera il menu corrente dal database.
    menu_corrente = get_menu_service(user_id, period)

    # Se il menu corrente non esiste, crea una struttura vuota con tutti i pasti e i macronutrienti inizializzati.
    if not menu_corrente:
        menu_corrente = {
            'day': {
                'lunedi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                     'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                     'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                     }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
                'martedi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                      'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                      'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                      }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
                'mercoledi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                        'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                        'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                        }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
                'giovedi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                      'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                      'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                      }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
                'venerdi': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                      'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                      'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                      }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
                'sabato': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                     'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                     'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                     }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
                'domenica': {'pasto': {'colazione': {'ricette': []}, 'spuntino_mattina': {'ricette': []},
                                       'pranzo': {'ricette': []}, 'spuntino_pomeriggio': {'ricette': []},
                                       'cena': {'ricette': []}, 'spuntino_sera': {'ricette': []}
                                       }, 'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
            },
            'weekly': {'kcal': 0, 'carboidrati': 0, 'proteine': 0, 'grassi': 0, 'fibre': 0},
            'all_food': []
        }
    else:
        menu_corrente = menu_corrente['menu']

    # Recupera le settimane salvate per la selezione.
    settimane_salvate = get_settimane_salvate(user_id)

    # Calcola i macronutrienti rimanenti per ogni giorno del menu.
    remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(menu_corrente)

    show_tutorial = not current_user.tutorial_completed

    # Rende la pagina index con tutti i dati necessari.
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           menu=menu_corrente,
                           settimane=settimane_salvate,
                           remaining_macronutrienti=remaining_macronutrienti,
                           show_tutorial=show_tutorial,
                           utenti=[current_user]
                           )


@views.route('/delete_ingredienti', methods=['POST'])
@login_required
def delete_ingredienti():
    """
    Questa funzione elimina un ingrediente da una ricetta basata sugli ID forniti.
    """
    try:
        data = request.get_json()
        ingredient_id = data['ingredient_id']
        recipe_id = data['recipe_id']
        user_id = current_user.user_id

        elimina_ingredienti(ingredient_id, recipe_id, user_id)
        current_app.cache.delete(f'list_ricette_{user_id}')
        current_app.cache.delete(f'ricette_{recipe_id}_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ingrediente eliminato correttamente.'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@views.route('/modifica_ingredienti_ricetta', methods=['POST'])
@login_required
def modifica_ingredienti_ricetta():
    """
    Questa funzione aggiunge un ingrediente a una ricetta esistente nel database.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ingredient_id = data['ingredient_id']
        recipe_id = data['recipe_id']
        quantity = data['quantity']

        salva_ingredienti(recipe_id, ingredient_id, quantity, user_id)
        current_app.cache.delete(f'list_ricette_{user_id}')
        current_app.cache.delete(f'ricette_{recipe_id}_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ingrediente inserito correttamente.'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@views.route('/update_ingredient', methods=['POST'])
@login_required
def update_ingredient():
    """
    Questa funzione aggiorna la quantità di un ingrediente specifico in una ricetta.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ingredient_id = data['ingredient_id']
        recipe_id = data['recipe_id']
        quantity = data['quantity']

        salva_ingredienti(recipe_id, ingredient_id, quantity, user_id)
        current_app.cache.delete(f'ricette_{recipe_id}_{user_id}')
        current_app.cache.delete(f'list_ricette_{user_id}')
        return jsonify({'status': 'success', 'message': 'Quantità aggiornata correttamente.'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/submit_weight', methods=['POST'])
@login_required
def submit_weight():
    """
    Questa funzione salva il peso dell'utente nel database.
    """
    user_id = current_user.user_id
    try:
        data = request.json
        # Salva i dati del peso nel database
        salvato = save_weight(data, user_id)

        if not salvato:
            return jsonify({'status': 'error', 'message': 'Prima di salvare i parametri, compila il tab Dieta con i tuoi Dati.'}), 404

        peso = get_peso_hist(user_id)

        # Esempio di svuotamento della cache di una funzione specifica
        current_app.cache.delete(f'get_peso_data_{user_id}')

        return jsonify({'status': 'success', 'peso': peso}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


@views.route('/salva_dati', methods=['POST'])
@login_required
def salva_dati():
    """
    Questa funzione salva i dati personali dell'utente relativi alla dieta nel database.
    """

    user_id = current_user.user_id
    try:
        id = request.form['id']
        nome = request.form['nome']
        cognome = request.form['cognome']
        sesso = request.form['sesso']
        eta = int(request.form['eta'])
        altezza = int(request.form['altezza'])
        peso = float(request.form['peso'])
        tdee = request.form['tdee']
        deficit_calorico = request.form['deficit_calorico']
        bmi = float(request.form['bmi'])
        peso_ideale = int(request.form['peso_ideale'])
        meta_basale = int(request.form['meta_basale'])
        meta_giornaliero = int(request.form['meta_giornaliero'])
        calorie_giornaliere = int(request.form['calorie_giornaliere'])
        settimane_dieta = request.form['settimane_dieta']
        carboidrati = int(request.form['carboidrati'])
        proteine = int(request.form['proteine'])
        grassi = int(request.form['grassi'])
        dieta = request.form['dieta']

        salva_utente_dieta(id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                           meta_basale, meta_giornaliero, calorie_giornaliere, settimane_dieta, carboidrati,
                           proteine, grassi, dieta)

        current_app.cache.delete(f'get_data_utente_{user_id}')
        current_app.cache.delete(f'get_peso_data_{user_id}')
        return redirect(url_for('views.dashboard'))
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_peso_data', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"get_peso_data_{current_user.user_id}")
@login_required
def get_peso_data():
    """
    Questa funzione recupera la cronologia del peso dell'utente dal database.
    """
    user_id = current_user.user_id
    try:
        peso = get_peso_hist(user_id)
        return jsonify({'status': 'success', 'peso': peso}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_data_utente', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"get_data_utente_{current_user.user_id}")
@login_required
def get_data_utente():
    """
    Questa funzione restituisce i dati personali dell'utente relativi alla dieta.
    """
    user_id = current_user.user_id
    try:
        utente = Utente.get_by_id(user_id)
        return jsonify(utente.to_dict()), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/aggiorna_quantita_ingrediente', methods=['POST'])
@login_required
def aggiorna_quantita_ingrediente():
    """
    Questa funzione aggiorna la quantità di un pasto specifico in un giorno specifico
    e ricalcola i macronutrienti rimanenti.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        day = data['day']
        meal = data['meal']
        ricetta_id = int(data['ricetta_id'])  # Convertiamo in int per confronto sicuro
        quantity = float(data['quantity'])
        week_id = data['week_id']

        # Recupera il menu corrente dal database
        menu_corrente = get_menu_service(user_id, menu_id=week_id)

        ingredienti_ricetta = recupera_ingredienti_ricetta(ricetta_id, user_id, quantity)
        totale_gruppi = get_totale_gruppi_service(ricetta_id, user_id, quantity)

        # Aggiorna la quantità del pasto nel menu
        for ricetta in menu_corrente['menu']['day'][day]['pasto'][meal]['ricette']:
            if int(ricetta['id']) == ricetta_id:
                old_qta = ricetta['qta']
                ricetta['qta'] = quantity
                ricetta['ricetta'] = ingredienti_ricetta
                ricetta['ingredienti'] = totale_gruppi

                # Ricalcola i macronutrienti giornalieri e settimanali
                for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
                    difference = ricetta[macro] * (old_qta - quantity)
                    menu_corrente['menu']['day'][day][macro] += difference
                    menu_corrente['menu']['weekly'][macro] += difference

        # Salva il menu aggiornato
        update_menu_corrente_service(menu_corrente['menu'], week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(menu_corrente['menu'])
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'menu//menu_settimana/{week_id}')

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


@views.route('/generate_pdf', methods=['POST'])
@login_required
def generate_pdf():
    """
    Questa funzione genera un PDF contenente il menu settimanale e la lista della spesa.
    La richiesta contiene l'immagine del menu in formato base64 e l'ID della settimana selezionata.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        img_data = data['image']
        week_id = data['week_id']

        # Decodifica l'immagine base64 inviata dal client
        img_data = img_data.split(',')[1]
        img = Image.open(BytesIO(base64.b64decode(img_data)))

        # Recupera il menu selezionato dal database
        menu_selezionato = get_menu_service(user_id, menu_id=week_id)

        # Imposta il PDF in orientamento orizzontale
        pdf_file = BytesIO()
        c = canvas.Canvas(pdf_file, pagesize=landscape(letter))
        width, height = landscape(letter)

        # Aggiungi margini al PDF
        margin_x = inch * 0.5
        margin_y = inch * 0.5

        # Calcola le dimensioni dell'immagine da inserire nel PDF
        img_width, img_height = img.size
        aspect = img_height / img_width
        img_display_width = width - 2 * margin_x
        img_display_height = img_display_width * aspect

        if img_display_width > width or img_display_height > height:
            img = img.resize((int(width * 0.8), int(height * 0.8)))

        # Inserisci l'immagine nel PDF con margini
        c.drawImage(ImageReader(img), margin_x, height - img_display_height - margin_y,
                    width=img_display_width, height=img_display_height)

        # Aggiungi una nuova pagina al PDF per la lista della spesa
        c.showPage()

        # Aggiungi la lista della spesa al PDF
        y = height - margin_y  # Posiziona la lista sotto l'immagine
        shopping_list = stampa_lista_della_spesa(user_id, menu_selezionato['menu'])
        c.setFont("Helvetica", 12)
        c.drawString(margin_x, y, "Lista della Spesa:")
        y -= 20
        for item in shopping_list:
            c.drawString(margin_x + 20, y, f"[ ] {item['alimento']} - {item['qta_totale']}g")
            y -= 15
            if y < margin_y:
                c.showPage()
                y = height - margin_y

        c.save()

        # Ritorna il PDF generato come risposta alla richiesta
        pdf_file.seek(0)
        return send_file(pdf_file, as_attachment=True, download_name='menu_settimanale.pdf', mimetype='application/pdf')
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/complete_tutorial', methods=['POST'])
@login_required
def complete_tutorial():
    user_id = current_user.user_id
    try:
        current_user.tutorial_completed = True
        db.session.commit()
        current_app.cache.delete(f'dashboard_{user_id}')
        return jsonify({'status': 'success'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_ricette_con_alimento/<int:alimento_id>', methods=['GET'])
@login_required
def get_ricette_con_alimento(alimento_id):
    user_id = current_user.user_id
    try:
        ricette_data = recupera_ricette_per_alimento(alimento_id, user_id)
        return jsonify({'status': 'success', 'ricette': ricette_data}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

