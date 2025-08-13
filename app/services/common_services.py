from sqlalchemy import asc
from app.models.MenuSettimanale import MenuSettimanale
import json
import re
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from app.models import db


def get_settimane_salvate_service(user_id):

    # Ottieni la data odierna
    oggi = datetime.now().date()

    tre_settimane_fa = oggi - timedelta(weeks=3)

    # Filtra per settimane che finiscono da 3 settimane fa in poi
    settimane = MenuSettimanale.query.order_by(asc(MenuSettimanale.data_inizio)).filter(MenuSettimanale.data_fine >= tre_settimane_fa).filter(MenuSettimanale.user_id == user_id).all()

    return [
        {
            'id': week.id,
            'name': f"Settimana {index + 1} dal {week.data_inizio.strftime('%Y-%m-%d')} al {week.data_fine.strftime('%Y-%m-%d')}",
            'attiva': week.data_inizio <= oggi <= week.data_fine
        }
        for index, week in enumerate(settimane)
    ]


def is_valid_email(email):
    # Definizione dell'espressione regolare per validare l'email
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

    # Utilizzo di re.match per verificare se l'email è valida
    if re.match(email_regex, email):
        return True
    else:
        return False

def calcola_macronutrienti_rimanenti_service(menu: json):
    remaining_macronutrienti = {}
    if menu:
        for giorno, dati_giorno in menu['day'].items():
            remaining_kcal = round(dati_giorno['kcal'],2)
            remaining_carboidrati = round(dati_giorno['carboidrati'],2)
            remaining_proteine = round(dati_giorno['proteine'],2)
            remaining_grassi = round(dati_giorno['grassi'],2)
            remaining_sale = round(dati_giorno['sale'],2)

            remaining_macronutrienti[giorno] = {
                'kcal': remaining_kcal,
                'carboidrati': remaining_carboidrati,
                'proteine': remaining_proteine,
                'grassi': remaining_grassi,
                'sale': remaining_sale
            }
    return remaining_macronutrienti


def get_sequence_value(seq_name):
    """
    Ottiene il valore successivo da una sequenza nel database.

    Args:
        seq_name (str): Nome della sequenza da cui ottenere il valore successivo.

    Returns:
        int: Il valore successivo generato dalla sequenza.

    Raises:
        ValueError: Se il nome della sequenza non è valido.
        RuntimeError: Se si verifica un errore durante l'esecuzione della query.
    """
    # Validare il nome della sequenza
    if not isinstance(seq_name, str) or not seq_name.strip():
        raise ValueError("Il nome della sequenza deve essere una stringa valida.")

    try:
        # Creare una query per ottenere il valore successivo dalla sequenza
        nextval_query = select(func.nextval(seq_name))
        # Eseguire la query
        result = db.session.execute(nextval_query)
        # Restituire il valore estratto
        return result.scalar()
    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback per sicurezza
        raise RuntimeError(f"Errore nel recupero del valore dalla sequenza: {seq_name}") from e
    except Exception as e:
        raise RuntimeError("Errore generico durante l'esecuzione della query.") from e
