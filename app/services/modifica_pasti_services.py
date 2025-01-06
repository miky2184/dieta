from sqlalchemy import and_

from app.models import db
from app.models.MenuSettimanale import MenuSettimanale


def get_menu_service(user_id: int, period: dict = None, menu_id: int = None):
    """
    Recupera un menu settimanale per un utente specifico.

    Args:
        user_id (int): ID dell'utente per il quale recuperare il menu.
        period (dict, optional): Dizionario contenente le date di inizio e fine della settimana.
                                  Esempio: {"data_inizio": <data>, "data_fine": <data>}.
        menu_id (int, optional): ID specifico del menu da recuperare. Se specificato, ignora `period`.

    Returns:
        dict: Dizionario contenente il menu e la data di fine,
              con struttura {"menu": <menu>, "data_fine": <data>} se trovato.
        None: Se nessun menu corrispondente è trovato.

    Raises:
        KeyError: Se il parametro `period` è fornito ma non contiene le chiavi `data_inizio` o `data_fine`.
    """
    if period and ('data_inizio' not in period or 'data_fine' not in period):
        raise ValueError("Il parametro 'period' deve contenere 'data_inizio' e 'data_fine'.")

    query = db.session.query(
        MenuSettimanale.menu.label('menu'),
        MenuSettimanale.data_fine.label('data_fine')
    ).filter_by(user_id=user_id)

    if menu_id:
        query = query.filter(MenuSettimanale.id == menu_id)
    else:
        query = query.filter(and_(MenuSettimanale.data_inizio == period['data_inizio'],
                                  MenuSettimanale.data_fine == period['data_fine']))

    result = query.first()

    # Restituisci i valori se il risultato esiste
    if result:
        return {'menu': result.menu, 'data_fine': result.data_fine}

    return None  # Nessun risultato trovato


def update_menu_corrente_service(menu, week_id, user_id):
    menu_update = MenuSettimanale.get_by_id_and_user(week_id, user_id)
    if menu_update:
        menu_update.menu = menu
        db.session.commit()