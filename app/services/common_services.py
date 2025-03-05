from datetime import datetime

from sqlalchemy import asc

from app.models.MenuSettimanale import MenuSettimanale


def get_settimane_salvate_service(user_id, show_old_week: bool = False):
    # Ottieni la data odierna
    oggi = datetime.now().date()

    query = MenuSettimanale.query.order_by(asc(MenuSettimanale.data_inizio))

    if not show_old_week:
        query = query.filter(MenuSettimanale.data_fine >= oggi)

    settimane = query.filter(MenuSettimanale.user_id == user_id).all()

    return [
        {
            'id': week.id,
            'name': f"Settimana {index + 1} dal {week.data_inizio.strftime('%Y-%m-%d')} al {week.data_fine.strftime('%Y-%m-%d')}",
            'attiva': week.data_inizio <= oggi <= week.data_fine
         }
        for index, week in enumerate(settimane)
    ]


# def recupera_settimane_service(user_id):
#     weeks = get_settimane_salvate_service(user_id, show_old_week=True)
#     return [
#         {'id': week.id, 'name': f"Settimana {index + 1} dal {week.data_inizio.strftime('%Y-%m-%d')} al {week.data_fine.strftime('%Y-%m-%d')}"}
#         for index, week in enumerate(weeks)
#     ]