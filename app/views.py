from flask import Blueprint, render_template, redirect, url_for, request, send_file, jsonify, current_app
from .services.menu_services import (definisci_calorie_macronutrienti, save_weight, genera_menu,
                                     stampa_lista_della_spesa, get_menu,
                                     carica_ricette, get_settimane_salvate,
                                     salva_menu, get_settimana, aggiorna_ricetta,
                                     attiva_o_disattiva_ricetta, get_ricette, elimina_ingredienti, salva_utente_dieta,
                                     salva_nuova_ricetta, salva_ingredienti,
                                     get_peso_hist, get_dati_utente,
                                     calcola_macronutrienti_rimanenti,
                                     carica_alimenti, salva_alimento, elimina_alimento, salva_nuovo_alimento,
                                     aggiungi_ricetta_al_menu, update_menu_corrente, rimuovi_pasto_dal_menu,
                                     delete_week_menu, elimina_ricetta, ordina_settimana_per_kcal,
                                     recupera_ricette_per_alimento, copia_menu, recupera_settimane, cancella_tutti_pasti_menu,
                                     recupera_ingredienti_ricetta)
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
    macronutrienti = definisci_calorie_macronutrienti(user_id)

    period = {
        "data_inizio": datetime.now().date(),
        "data_fine": datetime.now().date()
    }
    # Recupera il menu corrente dal database.
    menu_corrente = get_menu(user_id, period)

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

    # Recupera le settimane salvate per la selezione.
    settimane_salvate = get_settimane_salvate(user_id)

    # Calcola i macronutrienti rimanenti per ogni giorno del menu.
    remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

    show_tutorial = not current_user.tutorial_completed

    # Rende la pagina index con tutti i dati necessari.
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           menu=menu_corrente,
                           settimane=settimane_salvate,
                           remaining_macronutrienti=remaining_macronutrienti,
                           show_tutorial=show_tutorial
                           )


@views.route('/recupera_alimenti')
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"recupera_alimenti_{current_user.user_id}")
@login_required
def recupera_alimenti():
    user_id = current_user.user_id
    try:
        # Recupera tutti gli alimenti dal database.
        alimenti = carica_alimenti(user_id)
        return jsonify({'status': 'success', 'alimenti': alimenti}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/recupera_ricette', methods=['GET', 'POST'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"recupera_ricette_{current_user.user_id}")
@login_required
def recupera_ricette():
    user_id = current_user.user_id
    try:
        # Recupera le ricette disponibili dal database.
        ricette = carica_ricette(user_id, stagionalita=False)
        return jsonify({"status": 'success', 'ricette': ricette}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/generate_menu', methods=['POST'])
@login_required
def generate_menu():
    """
    Questa funzione gestisce la generazione del menu per la settimana corrente e quella successiva.
    Viene chiamata tramite una richiesta POST e restituisce un aggiornamento del progresso della generazione.
    """
    user_id = current_user.user_id
    try:
        macronutrienti = definisci_calorie_macronutrienti(user_id)
        if not macronutrienti.calorie_giornaliere:
            return jsonify({'status': 'error', 'message': 'Macronutrienti non definiti!!!'}), 500

        ricette_menu = carica_ricette(user_id, stagionalita=True)

        progress = 0
        total_steps = 4  # Numero totale di passaggi nella generazione del menu
        # Calcola l'inizio e la fine della prossima settimana
        oggi = datetime.now().date()
        giorni_indietro = (oggi.weekday() - 0) % 7
        lunedi_corrente = oggi - timedelta(days=giorni_indietro)
        domenica_corrente = lunedi_corrente + timedelta(days=6)

        period = {
            "data_inizio": lunedi_corrente,
            "data_fine": domenica_corrente
        }

        # Generazione del menu per la settimana corrente

        if not get_menu(user_id, period=period):
            settimana_corrente = deepcopy(get_settimana(macronutrienti))
            genera_menu(settimana_corrente, False, ricette_menu, user_id)
            progress += 1 / total_steps * 100
            time.sleep(1)  # Simula tempo di elaborazione

            # Ordina la settimana in base alle kcal giornaliere rimanenti in ordine decrescente
            settimana_corrente_ordinata = ordina_settimana_per_kcal(settimana_corrente)

            genera_menu(settimana_corrente_ordinata, True, ricette_menu, user_id)
            progress += 1 / total_steps * 100
            time.sleep(1)

            salva_menu(settimana_corrente_ordinata, user_id, period=period)
            progress += 1 / total_steps * 100
        else:
            progress += 3 / total_steps * 100

        lunedi_prossimo = oggi + timedelta(days=(7 - oggi.weekday()))
        domenica_prossima = lunedi_prossimo + timedelta(days=6)

        period = {
            "data_inizio": lunedi_prossimo,
            "data_fine": domenica_prossima
        }

        # Generazione del menu per la settimana successiva
        if not get_menu(user_id, period=period):
            prossima_settimana = deepcopy(get_settimana(macronutrienti))
            genera_menu(prossima_settimana, False, ricette_menu, user_id)
            progress += 1 / total_steps * 100
            time.sleep(1)

            # Ordina la settimana in base alle kcal giornaliere rimanenti in ordine decrescente
            prossima_settimana_ordinata = ordina_settimana_per_kcal(prossima_settimana)

            genera_menu(prossima_settimana_ordinata, True, ricette_menu, user_id)
            salva_menu(prossima_settimana_ordinata, user_id, period=period)
        else:
            prossima_settimana = deepcopy(get_settimana(macronutrienti))
            genera_menu(prossima_settimana, False, ricette_menu, user_id)
            progress += 1 / total_steps * 100
            time.sleep(1)

            # Ordina la settimana in base alle kcal giornaliere rimanenti in ordine decrescente
            prossima_settimana_ordinata = ordina_settimana_per_kcal(prossima_settimana)

            genera_menu(prossima_settimana_ordinata, True, ricette_menu, user_id)
            salva_menu(prossima_settimana_ordinata, user_id)

        current_app.cache.delete(f'dashboard_{user_id}')
        return jsonify({'status': 'success', 'progress': progress}), 200
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/menu_settimana/<int:settimana_id>', methods=['GET'])
@current_app.cache.cached(timeout=300)
@login_required
def menu_settimana(settimana_id):
    """
    Questa funzione gestisce la richiesta di visualizzazione di un menu specifico per una settimana data.
    Restituisce il menu selezionato e i macronutrienti rimanenti per quella settimana.
    """
    user_id = current_user.user_id
    try:
        menu_selezionato = get_menu(user_id, ids=settimana_id)
        macronutrienti_rimanenti = calcola_macronutrienti_rimanenti(menu_selezionato)

        return jsonify({'status':'success', 'menu': menu_selezionato, 'remaining_macronutrienti': macronutrienti_rimanenti}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/get_lista_spesa/<int:settimana_id>', methods=['GET'])
@login_required
def get_lista_spesa(settimana_id):
    """
    Questa funzione gestisce la richiesta POST per ottenere la lista della spesa basata sugli ID degli alimenti
    forniti dal client. Restituisce la lista della spesa corrispondente.
    """
    user_id = current_user.user_id
    try:
        menu = get_menu(user_id, ids=settimana_id)

        # Genera la lista della spesa basata sugli ID degli alimenti.
        lista_spesa = stampa_lista_della_spesa(user_id, menu)

        return jsonify({'status': 'success', 'lista_spesa': lista_spesa}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/salva_ricetta', methods=['POST'])
@login_required
def salva_ricetta():
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

        aggiorna_ricetta(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id)

        current_app.cache.delete(f'recupera_ricette_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ricetta salvata con successo!'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/attiva_disattiva_ricetta', methods=['POST'])
@login_required
def attiva_disattiva_ricetta():
    """
    Questa funzione attiva o disattiva una ricetta specifica nel database, basandosi sull'ID della ricetta.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ricetta_id = data['id']

        attiva_o_disattiva_ricetta(ricetta_id, user_id)

        current_app.cache.delete(f'recupera_ricette_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ricetta modificata con successo!'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_ricetta/<int:recipe_id>', methods=['GET'])
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"recipe_{request.view_args['recipe_id']}_{current_user.user_id}")
@login_required
def recipe(recipe_id):
    """
    Questa funzione restituisce i dettagli di una ricetta specifica basata sul suo ID.
    """
    user_id = current_user.user_id
    try:
        ricette = get_ricette(recipe_id, user_id)
        return jsonify({'status': 'success', 'ricette': ricette}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/delete_ingredient', methods=['POST'])
@login_required
def delete_ingredient():
    """
    Questa funzione elimina un ingrediente da una ricetta basata sugli ID forniti.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ingredient_id = data['ingredient_id']
        recipe_id = data['recipe_id']
        user_id = current_user.user_id

        elimina_ingredienti(ingredient_id, recipe_id, user_id)
        current_app.cache.delete(f'recupera_ricette_{user_id}')
        current_app.cache.delete(f'recipe_{recipe_id}_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ingrediente eliminato correttamente.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_all_ingredients', methods=['GET'] )
@login_required
@current_app.cache.cached(timeout=300, key_prefix=lambda: f"get_all_ingredients_{current_user.user_id}")
def get_all_ingredients():
    """
    Questa funzione restituisce tutti gli ingredienti disponibili nel database.
    """
    user_id = current_user.user_id
    try:
        alimenti = carica_alimenti(user_id)
        return jsonify({'status': 'success', 'alimenti': alimenti}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
        current_app.cache.delete(f'recupera_ricette_{user_id}')
        current_app.cache.delete(f'recipe_{recipe_id}_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ingrediente inserito correttamente.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
        current_app.cache.delete(f'recipe_{recipe_id}_{user_id}')
        current_app.cache.delete(f'recupera_ricette_{user_id}')
        return jsonify({'status': 'success', 'message': 'Quantità aggiornata correttamente.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/nuova_ricetta', methods=['POST'])
@login_required
def nuova_ricetta():
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
        current_app.cache.delete(f'recupera_ricette_{user_id}')

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/nuovo_alimento', methods=['POST'])
@login_required
def nuovo_alimento():
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
        verdura = 'verdura' in request.form
        frutta = 'frutta' in request.form
        pesce = 'pesce' in request.form
        confezionato = 'confezionato' in request.form
        vegan = 'vegan' in request.form
        carne_bianca = 'carne-bianca' in request.form
        carne_rossa = 'carne-rossa' in request.form

        salva_nuovo_alimento(name, carboidrati, proteine, grassi, fibre, frutta, carne_bianca, carne_rossa, verdura,
                             confezionato, vegan, pesce, user_id)

        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'get_all_ingredients_{user_id}')
        current_app.cache.delete(f'recupera_alimenti_{user_id}')
        current_app.cache.delete(f'recupera_ricette_{user_id}')

        return jsonify({'status': 'success'}), 200
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
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
        diet = request.form['diet']

        salva_utente_dieta(id, nome, cognome, sesso, eta, altezza, peso, tdee, deficit_calorico, bmi, peso_ideale,
                           meta_basale, meta_giornaliero, calorie_giornaliere, settimane_dieta, carboidrati,
                           proteine, grassi, diet)

        current_app.cache.delete(f'get_data_utente_{user_id}')
        current_app.cache.delete(f'get_peso_data_{user_id}')
        return redirect(url_for('views.dashboard'))
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
        utente = get_dati_utente(user_id)
        return jsonify(utente), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/save_alimento', methods=['POST'])
@login_required
def save_alimento():
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
        frutta = data.get('frutta')
        carne_bianca = data.get('carne_bianca')
        carne_rossa = data.get('carne_rossa')
        verdura = data.get('verdura')
        confezionato = data.get('confezionato')
        vegan = data.get('vegan')
        pesce = data.get('pesce')

        salva_alimento(alimento_id, nome, carboidrati, proteine, grassi, fibre, frutta, carne_bianca, carne_rossa, verdura,
                       confezionato, vegan, pesce, user_id)
        current_app.cache.delete(f'get_all_ingredients_{user_id}')
        current_app.cache.delete(f'recupera_alimenti_{user_id}')
        return jsonify({'status': 'success', 'message': 'Alimento salvato con successo!'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/delete_alimento', methods=['POST'])
@login_required
def delete_alimento():
    """
    Questa funzione elimina un alimento dal database basandosi sul suo ID.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        alimento_id = data.get('id')

        elimina_alimento(alimento_id, user_id)
        current_app.cache.delete(f'get_all_ingredients_{user_id}')
        current_app.cache.delete(f'recupera_alimenti_{user_id}')
        return jsonify({'status': 'success', 'message': 'Alimento eliminato con successo!'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_available_meals', methods=['GET'])
@login_required
def get_available_meals():
    """
    Questa funzione restituisce le ricette disponibili per un pasto specifico in un giorno specifico,
    escludendo quelle già presenti nel menu corrente.
    """
    user_id = current_user.user_id
    try:
        meal_type = request.args.get('meal')
        day = request.args.get('day')
        week_id = request.args.get('week_id')

        meal_type_mapping = {
            'colazione': ['colazione', 'colazione_sec'],
            'spuntino_mattina': ['spuntino'],
            'pranzo': ['principale'],
            'spuntino_pomeriggio': ['spuntino'],
            'cena': ['principale'],
            'spuntino_sera': ['spuntino']
        }

        generic_meal_types = meal_type_mapping.get(meal_type)
        # Recupera tutte le ricette attive
        ricette = carica_ricette(user_id, stagionalita=True, attive=True, complemento=False)

        # Filtra le ricette disponibili in base al tipo di pasto
        available_meals = [ricetta for ricetta in ricette if
                           any(ricetta[generic_meal_type] for generic_meal_type in generic_meal_types)]

        # Esclude le ricette già presenti nel pasto del giorno specificato
        menu_corrente = get_menu(user_id, ids=week_id)
        if menu_corrente:
            if meal_type in ('pranzo', 'cena'):
                ricette_presenti_ids = menu_corrente['all_food']
            else:
                ricette_presenti_ids = [r['id'] for r in menu_corrente['day'][day]['pasto'][meal_type]['ricette']]
            available_meals = [ricetta for ricetta in available_meals if ricetta['id'] not in ricette_presenti_ids]

        return jsonify(available_meals), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/aggiungi_ricetta_menu/<int:week_id>', methods=['POST'])
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
        menu_corrente = get_menu(user_id, ids=week_id)

        # Aggiunge i pasti selezionati al menu
        for meal_id in selected_meals:
            aggiungi_ricetta_al_menu(menu_corrente, day, meal, meal_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)

        # Salva il menu aggiornato nel database
        update_menu_corrente(menu_corrente, week_id, user_id)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')
        return jsonify({
            'status': 'success',
            'menu': menu_corrente,  # Restituisce il menu aggiornato
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/rimuovi_ricetta/<int:week_id>', methods=['POST'])
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
        menu_corrente = get_menu(user_id, ids=week_id)

        # Rimuove il pasto dal menu
        rimuovi_pasto_dal_menu(menu_corrente, day, meal, meal_id)

        # Salva il menu aggiornato nel database
        update_menu_corrente(menu_corrente, week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')
        return jsonify({
            'status': 'success',
            'menu': menu_corrente,
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
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
        menu_corrente = get_menu(user_id, ids=week_id)

        ingredienti_ricetta = recupera_ingredienti_ricetta(ricetta_id, user_id, quantity)

        # Aggiorna la quantità del pasto nel menu
        for ricetta in menu_corrente['day'][day]['pasto'][meal]['ricette']:
            if int(ricetta['id']) == ricetta_id:
                old_qta = ricetta['qta']
                ricetta['qta'] = quantity
                ricetta['ricetta'] = ingredienti_ricetta

                # Ricalcola i macronutrienti giornalieri e settimanali
                for macro in ['kcal', 'carboidrati', 'proteine', 'grassi']:
                    difference = ricetta[macro] * (old_qta - quantity)
                    menu_corrente['day'][day][macro] += difference
                    menu_corrente['weekly'][macro] += difference

        # Salva il menu aggiornato
        update_menu_corrente(menu_corrente, week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti(menu_corrente)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')

        return jsonify({
            'status': 'success',
            'menu': menu_corrente,
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
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
        menu_selezionato = get_menu(user_id, ids=week_id)

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

        # Inserisci l'immagine nel PDF con margini
        c.drawImage(ImageReader(img), margin_x, height - img_display_height - margin_y,
                    width=img_display_width, height=img_display_height)

        # Aggiungi una nuova pagina al PDF per la lista della spesa
        c.showPage()

        # Aggiungi la lista della spesa al PDF
        y = height - margin_y  # Posiziona la lista sotto l'immagine
        shopping_list = stampa_lista_della_spesa(user_id, menu_selezionato, True)
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
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/delete_menu/<int:week_id>', methods=['DELETE'])
@login_required
def delete_menu(week_id):
    # Elimina il menu dal database
    user_id = current_user.user_id
    try:
        delete_week_menu(week_id, user_id)

        # Svuota la cache correlata
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')
        return jsonify({'status': 'success', 'message': 'Menu eliminato con successo!'}), 200
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
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/delete_ricetta', methods=['POST'])
@login_required
def delete_ricetta():
    """
    Questa funzione cancella una ricetta basata sui dati forniti dal form.
    """
    user_id = current_user.user_id
    try:
        data = request.get_json()
        ricetta_id = data['id']

        elimina_ricetta(ricetta_id, user_id)

        current_app.cache.delete(f'recupera_ricette_{user_id}')
        return jsonify({'status': 'success', 'message': 'Ricetta cancellata con successo!'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/inverti_pasti/<int:week_id>', methods=['POST'])
@login_required
def inverti_pasti(week_id):
    user_id = current_user.user_id
    try:
        data = request.json
        day = data.get('day')

        # Recupera il menu della settimana per l'utente
        settimana = get_menu(user_id, ids=week_id)

        if not settimana:
            return jsonify({'status': 'error', 'message': 'Menu non trovato'}), 404

        # Inverti i pasti per il giorno specificato
        pranzo = settimana['day'][day]['pasto']['pranzo']
        cena = settimana['day'][day]['pasto']['cena']

        settimana['day'][day]['pasto']['pranzo'] = cena
        settimana['day'][day]['pasto']['cena'] = pranzo

        # Salva le modifiche nel database
        update_menu_corrente(settimana, week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti(settimana)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')
        return jsonify({
            'status': 'success',
            'menu': settimana,
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/delete_meal_daily/<int:week_id>', methods=['POST'])
@login_required
def delete_meal_daily(week_id):
    user_id = current_user.user_id
    try:
        data = request.json
        day = data.get('day')
        meal_type = data.get('meal_type')
        ids_remove = []

        # Recupera il menu della settimana per l'utente
        settimana = get_menu(user_id, ids=week_id)

        if not settimana:
            return jsonify({'status': 'error', 'message': 'Menu non trovato'}), 404

        if meal_type == 'colazione':
            cancella_tutti_pasti_menu(settimana, day, 'colazione')
        elif meal_type == 'principali':
            cancella_tutti_pasti_menu(settimana, day, 'pranzo')
            cancella_tutti_pasti_menu(settimana, day, 'cena')
        elif meal_type == 'spuntini':
            cancella_tutti_pasti_menu(settimana, day, 'spuntino_mattina')
            cancella_tutti_pasti_menu(settimana, day, 'spuntino_pomeriggio')
            cancella_tutti_pasti_menu(settimana, day, 'spuntino_sera')
        else:
            cancella_tutti_pasti_menu(settimana, day, 'colazione')
            cancella_tutti_pasti_menu(settimana, day, 'pranzo')
            cancella_tutti_pasti_menu(settimana, day, 'cena')
            cancella_tutti_pasti_menu(settimana, day, 'spuntino_mattina')
            cancella_tutti_pasti_menu(settimana, day, 'spuntino_pomeriggio')
            cancella_tutti_pasti_menu(settimana, day, 'spuntino_sera')

        # Salva le modifiche nel database
        update_menu_corrente(settimana, week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti(settimana)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')
        return jsonify({
            'status': 'success',
            'menu': settimana,
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/inverti_pasti_giorni/<int:week_id>', methods=['POST'])
@login_required
def inverti_pasti_giorni(week_id):
    user_id = current_user.user_id
    try:
        data = request.json
        day1 = data.get('day1')
        day2 = data.get('day2')

        # Recupera il menu della settimana per l'utente
        settimana = get_menu(user_id, ids=week_id)

        if not settimana:
            return jsonify({'status': 'error', 'message': 'Menu non trovato'}), 404

        # Inverti i pasti dei due giorni specificati
        temp_day = deepcopy(settimana['day'][day1])
        settimana['day'][day1] = deepcopy(settimana['day'][day2])
        settimana['day'][day2] = temp_day

        # Salva le modifiche nel database
        update_menu_corrente(settimana, week_id, user_id)

        # Ricalcola i macronutrienti rimanenti
        remaining_macronutrienti = calcola_macronutrienti_rimanenti(settimana)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_id}')

        return jsonify({
            'status': 'success',
            'menu': settimana,
            'remaining_macronutrienti': remaining_macronutrienti
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_complemento', methods=['GET'])
@login_required
def get_complemento():
    """
    Questa funzione restituisce le ricette disponibili per un pasto specifico in un giorno specifico,
    escludendo quelle già presenti nel menu corrente.
    """
    user_id = current_user.user_id
    meal_type = request.args.get('meal')

    meal_type_mapping = {
        'colazione': ['colazione', 'colazione_sec'],
        'spuntino_mattina': ['spuntino'],
        'pranzo': ['principale'],
        'spuntino_pomeriggio': ['spuntino'],
        'cena': ['principale'],
        'spuntino_sera': ['spuntino']
    }

    generic_meal_types = meal_type_mapping.get(meal_type)

    try:
        # Recupera tutte le ricette complemento
        ricette = carica_ricette(user_id, complemento=True)

        # Filtra le ricette disponibili in base al tipo di pasto
        available_meals = [ricetta for ricetta in ricette if
                           any(ricetta[generic_meal_type] for generic_meal_type in generic_meal_types)]

        return jsonify({'status':'success', 'ricette':available_meals}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_contorno', methods=['GET'])
@login_required
def get_contorno():
    """
    Questa funzione restituisce le ricette disponibili per un pasto specifico in un giorno specifico,
    escludendo quelle già presenti nel menu corrente.
    """
    user_id = current_user.user_id
    try:
        # Recupera tutte le ricette complemento
        results = carica_ricette(user_id, attive=True, contorno=True)

        return jsonify({'status':'success', 'ricette':results}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_ricette_con_alimento/<int:alimento_id>', methods=['GET'])
@login_required
def get_ricette_con_alimento(alimento_id):
    user_id = current_user.user_id
    try:
        ricette_data = recupera_ricette_per_alimento(alimento_id, user_id)
        return jsonify({'status': 'success', 'ricette': ricette_data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/copy_week', methods=['POST'])
@login_required
def copy_week():
    user_id = current_user.user_id
    try:
        data = request.json
        week_from = data.get('week_from')
        week_to = data.get('week_to')
        # Ottieni il menu della settimana di origine
        menu_from = get_menu(current_user.user_id, ids=week_from)

        if not menu_from:
            return jsonify({'status': 'error', 'message': 'Settimana non trovata.'}), 404

        # Copia il menu dalla settimana di origine alla settimana di destinazione
        copia_menu(menu_from, week_to, user_id)
        current_app.cache.delete(f'dashboard_{user_id}')
        current_app.cache.delete(f'view//menu_settimana/{week_to}')
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/get_weeks', methods=['GET'])
@login_required
def get_weeks():
    user_id = current_user.user_id
    try:
        weeks_list = recupera_settimane(user_id)
        return jsonify({'status': 'success', 'weeks': weeks_list}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
