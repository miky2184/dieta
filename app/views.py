from flask import Blueprint, render_template, jsonify, request
from .services.menu_services import (definisci_calorie_macronutrienti, stampa_ricette, stampa_ingredienti_ricetta, genera_menu,
                  stampa_lista_della_spesa, orig_settimana, get_menu_corrente, salva_menu_settimana_prossima, carica_ricette,
                  get_settimane_salvate, get_menu_settima_prossima, salva_menu_corrente)
from .models.database import get_db_connection
from .models.common import printer
from copy import deepcopy
views = Blueprint('views', __name__)

@views.route('/')
def index():
    # Calcola le calorie e i macronutrienti
    macronutrienti = definisci_calorie_macronutrienti()
    # Recupera le ricette dal database
    ricette = carica_ricette()
    # Recupera gli ingredienti delle ricette dal database
    ingredienti = stampa_ingredienti_ricetta()

    # Recupera il menu corrente
    menu_corrente = get_menu_corrente()

    if not menu_corrente:
        settimana_corrente = deepcopy(orig_settimana)
        settimana_corrente = genera_menu(settimana_corrente, False, ricette)
        genera_menu(settimana_corrente, True, ricette)
        salva_menu_corrente(settimana_corrente)
        menu_corrente = settimana_corrente

    if not get_menu_settima_prossima():
        prossima_settimana = deepcopy(orig_settimana)
        prossima_settimana =  genera_menu(prossima_settimana, False, ricette)
        genera_menu(prossima_settimana, True, ricette)
        salva_menu_settimana_prossima(prossima_settimana)

    # Recupera le settimane salvate per il dropdown
    settimane_salvate = get_settimane_salvate()

    # Recupera la lista della spesa
    lista_spesa = stampa_lista_della_spesa(menu_corrente.get('all_food'))

    # Questa sarà la pagina principale, passa i dati al template
    return render_template('index.html',
                           macronutrienti=macronutrienti,
                           ricette=ricette,
                           ingredienti=ingredienti,
                           menu=menu_corrente,
                           lista_spesa=lista_spesa,
                           settimane=settimane_salvate
                           )


@views.route('/menu_settimana/<int:settimana_id>')
def menu_settimana(settimana_id):

    menu_selezionato = None
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT menu FROM dieta.menu_settimanale WHERE id = %s
        """, (settimana_id,))
        result = cur.fetchone()
        if result:
            menu_selezionato = result['menu']

    return jsonify(menu=menu_selezionato)


@views.route('/get_lista_spesa', methods=['POST'])
def get_lista_spesa():
    data = request.get_json()
    ids_all_food = data.get('ids_all_food', [])

    # Usa la funzione stampa_lista_della_spesa per ottenere la lista della spesa
    lista_spesa = stampa_lista_della_spesa(ids_all_food)

    return jsonify(lista_spesa=lista_spesa)