import base64
import traceback
from datetime import datetime
from io import BytesIO

from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, current_app
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.models.Utente import Utente
#from app.ricette_route import invalidate_cache
from app.services.common_services import get_settimane_salvate_service
from app.services.menu_services import save_weight, stampa_lista_della_spesa, elimina_ingredienti, salva_utente_dieta, get_peso_hist, get_peso_ideale_per_data_interpolato, recupera_ricette_per_alimento, aggiorna_limiti_gruppi, calcola_quantita, update_menu_corrente_service
from app.services.modifica_pasti_services import get_menu_service
from app.services.util_services import calcola_macronutrienti_rimanenti_service

views = Blueprint('views', __name__)


@views.route('/dashboard', methods=['GET'])
#@current_app.cache.cached(timeout=300, key_prefix=lambda: f"dashboard_{current_user.user_id}")
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
    settimane_salvate = get_settimane_salvate_service(user_id, show_old_week=False)

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
        #current_app.cache.delete(invalidate_cache(user_id))
        #current_app.cache.delete(f'ricette_{recipe_id}_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ingrediente eliminato correttamente.'}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err), 'trace': traceback.format_exc()}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}', 'trace': traceback.format_exc()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


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
        success = save_weight(data, user_id)

        if success:
            # Calcola il peso ideale per questa data per mostrarlo nella risposta
            peso_data = get_peso_hist(user_id)
            return jsonify({'status': 'success', 'peso': peso_data}), 200

        else:
            return jsonify({'status': 'error', 'message': 'Prima di salvare i parametri, compila il tab Dieta con i tuoi Dati.'}), 400

        # Esempio di svuotamento della cache di una funzione specifica
        #current_app.cache.delete(f'get_peso_data_{user_id}')
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
        carboidrati = float(request.form['carboidrati'])
        proteine = float(request.form['proteine'])
        grassi = float(request.form['grassi'])
        dieta = request.form['dieta']
        attivita_fisica = request.form['attivita_fisica']

        salva_utente_dieta(user_id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                           meta_basale, meta_giornaliero, calorie_giornaliere, settimane_dieta, carboidrati,
                           proteine, grassi, dieta, attivita_fisica)

        #current_app.cache.delete(f'get_data_utente_{user_id}')
        #current_app.cache.delete(f'get_peso_data_{user_id}')
        return redirect(url_for('views.dashboard'))
    except SQLAlchemyError as db_err:
        print({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)})
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        print({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'})
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        print({'status': 'error', 'message': 'Errore di database.', 'details': str(e)})
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_peso_data', methods=['GET'])
#@current_app.cache.cached(timeout=300, key_prefix=lambda: f"get_peso_data_{current_user.user_id}")
@login_required
def get_peso_data():
    """
    Questa funzione recupera la cronologia completa del peso dell'utente,
    combinando dati reali (RegistroPeso) e pesi ideali (PesoIdeale).
    """
    user_id = current_user.user_id
    try:
        peso_data = get_peso_hist(user_id)
        return jsonify({'status': 'success', 'peso': peso_data}), 200
    except SQLAlchemyError as db_err:
        return jsonify({'status': 'error', 'message': 'Errore di database.', 'details': str(db_err)}), 500
    except KeyError as key_err:
        return jsonify({'status': 'error', 'message': f'Chiave mancante: {str(key_err)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@views.route('/get_data_utente', methods=['GET'])
#@current_app.cache.cached(timeout=300, key_prefix=lambda: f"get_data_utente_{current_user.user_id}")
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

        # Aggiorna la quantità del pasto nel menu
        for ricetta in menu_corrente['menu']['day'][day]['pasto'][meal]['ricette']:
            if int(ricetta['id']) == ricetta_id:
                old_qta = ricetta['qta']
                ricetta['qta'] = quantity
                aggiorna_limiti_gruppi(ricetta, menu_corrente['menu']['consumi'], old_qta, old_qta, True)
                aggiorna_limiti_gruppi(ricetta, menu_corrente['menu']['consumi'], old_qta, quantity, False)

                ricetta['ricetta'] = calcola_quantita(ricetta, 'ricetta', 'nome', old_qta, quantity)
                ricetta['ingredienti'] = calcola_quantita(ricetta, 'ingredienti', 'id_gruppo', old_qta, quantity)

                # Ricalcola i macronutrienti giornalieri e settimanali
                for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
                    difference = ricetta[macro] * (old_qta - quantity)
                    menu_corrente['menu']['day'][day][macro] += difference
                    menu_corrente['menu']['weekly'][macro] += difference


        # Salva il menu aggiornato
        update_menu_corrente_service(menu_corrente['menu'], week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti_service(menu_corrente['menu'])
        #current_app.cache.delete(f'dashboard_{user_id}')
        #current_app.cache.delete(f'menu_settimana_{week_id}_{current_user}')

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


from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from flask import send_file, jsonify, request
from io import BytesIO
from PIL import Image
import base64
from sqlalchemy.exc import SQLAlchemyError

@views.route('/generate_pdf', methods=['POST'])
@login_required
def generate_pdf():
    """
    Genera un PDF migliorato che utilizza tutto lo spazio disponibile per il menu e la lista della spesa.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        img_data = data['image']
        week_id = data['week_id']

        # Recupera il menu selezionato e la lista della spesa
        menu_selezionato = get_menu_service(user_id, menu_id=week_id)
        shopping_list = stampa_lista_della_spesa(user_id, menu_selezionato['menu'])

        # Decodifica l'immagine base64
        img_data = img_data.split(',')[1]
        img = Image.open(BytesIO(base64.b64decode(img_data)))

        # Imposta il PDF in orientamento orizzontale su foglio A4
        pdf_file = BytesIO()
        c = canvas.Canvas(pdf_file, pagesize=landscape(A4))
        width, height = landscape(A4)

        # Riduci i margini al minimo
        margin_x = inch * 0.3
        margin_y = inch * 0.3

        # Calcola le dimensioni dell'immagine per riempire il foglio
        img_width, img_height = img.size
        aspect = img_width / img_height

        # Calcola la dimensione massima possibile
        img_display_width = width - 2 * margin_x
        img_display_height = img_display_width / aspect

        # Adatta l'immagine per non superare i margini verticali
        if img_display_height > height - 2 * margin_y:
            img_display_height = height - 2 * margin_y
            img_display_width = img_display_height * aspect

        # Centra l'immagine sul foglio
        x_offset = (width - img_display_width) / 2
        y_offset = (height - img_display_height) / 2

        # Inserisci l'immagine nel PDF
        c.drawImage(ImageReader(img), x_offset, y_offset,
                    width=img_display_width, height=img_display_height)

        # Aggiungi una nuova pagina per la lista della spesa
        c.showPage()

        # Organizza la lista della spesa in colonne
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, height - margin_y, "Lista della Spesa:")
        c.setFont("Helvetica", 10)

        # Configura colonne
        column_width = (width - 2 * margin_x) / 3  # 3 colonne
        column_height = height - 2 * margin_y
        line_height = 14
        max_lines_per_column = int(column_height // line_height)

        x_start = margin_x
        y_start = height - margin_y - 20
        line_count = 0
        column = 0

        for item in shopping_list:
            if line_count >= max_lines_per_column:
                column += 1
                line_count = 0
                x_start = margin_x + column * column_width
                y_start = height - margin_y - 20

            if column > 2:  # Aggiungi una nuova pagina se superi 3 colonne
                c.showPage()
                column = 0
                line_count = 0
                x_start = margin_x
                y_start = height - margin_y - 20

            # Disegna la checkbox
            checkbox_size = 10
            checkbox_y_offset = -checkbox_size / 4  # Offset per centrare verticalmente il testo
            c.rect(x_start, y_start - line_count * line_height - checkbox_size / 2,
                   checkbox_size, checkbox_size, stroke=1, fill=0)

            # Aggiungi il testo accanto alla checkbox
            c.drawString(x_start + checkbox_size + 5,
                         y_start - line_count * line_height + checkbox_y_offset,
                         f"{item['alimento']} - {item['qta_totale']}g")
            line_count += 1

        c.save()

        # Ritorna il PDF generato
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
    try:
        current_user.tutorial_completed = True
        db.session.commit()
        #current_app.cache.delete(f'dashboard_{user_id}')
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

