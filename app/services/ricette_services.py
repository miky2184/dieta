from sqlalchemy import func, literal, exists, and_, or_, not_
from sqlalchemy.orm import aliased
from sqlalchemy.sql import extract

from app.models import db
from app.models.Ricetta import Ricetta
from app.models.RicettaBase import RicettaBase
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from app.services.db_services import get_sequence_value
from app.services.util_services import print_query


def get_ricette_service(user_id, ids=None, stagionalita: bool=False, attive:bool=False, complemento=None, contorno=False, data_stagionalita=None) -> list[dict]:
    """
        Carica tutte le ricette disponibili dal database, arricchendole con informazioni nutrizionali e ingredienti.

        Args:
            user_id (int): ID dell'utente per il quale caricare le ricette.
            ids (list[int], optional): Filtra le ricette con gli ID specificati.
            stagionalita (bool, optional): Se True, applica un filtro per la stagionalità degli ingredienti.
            attive (bool, optional): Se True, filtra le ricette che sono attive.
            complemento (bool, optional): Se specificato, filtra le ricette con o senza il flag `complemento`.
            contorno (bool, optional): Se True, filtra le ricette con il flag `contorno` attivo.
            data_stagionalita (date, optional): Data specifica per applicare il filtro di stagionalità (predefinito è la data corrente).

        Returns:
            list[dict]: Lista di ricette arricchite con informazioni nutrizionali, stagionalità e ingredienti.
        """
    # Alias per le tabelle
    vr1 = aliased(VRicetta)
    vir1 = aliased(VIngredientiRicetta)
    va1 = aliased(VAlimento)

    vir2 = aliased(VIngredientiRicetta)  # Alias per la subquery di NOT EXISTS
    va2 = aliased(VAlimento)
    vr2 = aliased(VRicetta)

    # Filtri di NOT EXISTS per VIngredientiRicetta
    not_exists_vir = ~exists().where(
        and_(
            vir2.id_ricetta == vir1.id_ricetta,
            vir2.id_alimento == vir1.id_alimento,
            vir2.user_id == user_id
        )
    )

    # Filtri di NOT EXISTS per VAlimento
    not_exists_va = ~exists().where(
        and_(
            va2.id == va1.id,
            va2.user_id == user_id
        )
    )

    # Filtri di NOT EXISTS per VRicetta
    not_exists_vr = ~exists().where(
        and_(
            vr2.id == vr1.id,
            vr2.user_id == user_id
        )
    )

    # Query principale
    query = (
        db.session.query(
            vr1.user_id.label("user_id"),
            vr1.id.label("id_ricetta"),
            vr1.nome_ricetta.label("nome_ricetta"),
            func.ceil(
                func.sum(
                    (va1.carboidrati / 100) * vir1.qta * 4 +
                    (va1.proteine / 100) * vir1.qta * 4 +
                    (va1.grassi / 100) * vir1.qta * 9 +
                    (va1.fibre / 100) * vir1.qta * 2
                ).over(partition_by=vr1.id)
            ).label('kcal'),
            func.round(
                func.sum((va1.carboidrati / 100) * vir1.qta).over(partition_by=vr1.id),
                2
            ).label('carboidrati'),
            func.round(
                func.sum((va1.proteine / 100) * vir1.qta).over(partition_by=vr1.id),
                2
            ).label('proteine'),
            func.round(
                func.sum((va1.grassi / 100) * vir1.qta).over(partition_by=vr1.id),
                2
            ).label('grassi'),
            func.round(
                func.sum((va1.fibre / 100) * vir1.qta).over(partition_by=vr1.id),
                2
            ).label('fibre'),
            vr1.colazione,
            vr1.spuntino,
            vr1.principale,
            vr1.contorno,
            vr1.colazione_sec,
            vr1.complemento,
            vr1.enabled.label('attiva')
        )
        .select_from(vr1)
        .outerjoin(
            vir1,
            and_(
                vir1.id_ricetta == vr1.id,
                or_(
                    and_(vir1.user_id == user_id, not_(vir1.removed)),
                    and_(vir1.user_id == 0, not_exists_vir)
                )
            )
        )
        .outerjoin(
            va1,
            and_(
                va1.id == vir1.id_alimento,
                or_(
                    and_(va1.user_id == user_id, not_(va1.removed)),
                    and_(va1.user_id == 0, not_exists_va)
                )
            )
        )
        .filter(
            or_(
                and_(vr1.user_id == user_id, not_(vr1.removed)),
                and_(vr1.user_id == 0, not_exists_vr)
            )
        )
        .distinct()
    )

    # Applicazione dei filtri
    if stagionalita:
        data = func.current_date()
        if data_stagionalita:
            data = data_stagionalita

        query = query.filter(
            or_(
                and_(
                    va1.id_gruppo == 6, (extract('month', data) == func.any(va1.stagionalita))
                ),
                (
                        va1.id_gruppo != 6)
                )
        )

    if ids:
        query = query.filter(vr1.id == ids)

    if attive:
        query = query.filter(vr1.enabled.is_(True))

    if complemento:
        query = query.filter(vr1.complemento.is_(True))
    elif complemento is False:
        query = query.filter(vr1.complemento.is_(False))

    if contorno:
        query = query.filter(vr1.contorno.is_(True))

    ricette = []
    for row in query.order_by(vr1.nome_ricetta).all():
        ricette.append({
            'user_id': row.user_id,
            'id': row.id_ricetta,
            'nome_ricetta': row.nome_ricetta,
            'kcal': float(row.kcal or 0),
            'carboidrati': float(row.carboidrati or 0),
            'proteine': float(row.proteine or 0),
            'grassi': float(row.grassi or 0),
            'fibre': float(row.fibre or 0),
            'colazione': row.colazione,
            'spuntino': row.spuntino,
            'principale': row.principale,
            'contorno': row.contorno,
            'colazione_sec': row.colazione_sec,
            'complemento': row.complemento,
            'attiva': row.attiva,
            'ricetta': '',
            'ingredienti': []
        })

    # Visualizza la query SQL generata
    print_query(query)
    return ricette


def update_ricetta_service(nome, colazione, colazione_sec, spuntino, principale, contorno, complemento, ricetta_id, user_id):
    ricetta_base = RicettaBase.get_by_id(ricetta_id)
    if ricetta_base:
        ricetta_id = ricetta_base.id
    ricetta = Ricetta.get_by_id_and_user(ricetta_id, user_id)

    if not ricetta:
        ricetta = Ricetta(
            id=ricetta_base.id,
            nome_ricetta_override=nome.upper(),
            colazione_override=colazione,
            spuntino_override=spuntino,
            principale_override=principale,
            contorno_override=contorno,
            colazione_sec_override=colazione_sec,
            complemento_override=complemento,
            enabled=True,
            user_id=user_id
        )
        db.session.add(ricetta)
    else:
        ricetta.nome_ricetta_override = nome.upper()
        ricetta.colazione_override = colazione
        ricetta.colazione_sec_override = colazione_sec
        ricetta.spuntino_override = spuntino
        ricetta.principale_override = principale
        ricetta.contorno_override = contorno
        ricetta.complemento_override = complemento

    db.session.commit()


def attiva_disattiva_ricetta_service(ricetta_id, user_id):
    ricetta_base = RicettaBase.get_by_id(ricetta_id)
    if ricetta_base:
        ricetta_id = ricetta_base.id
    ricetta = Ricetta.get_by_id_and_user(ricetta_id, user_id)

    if not ricetta:
        ricetta = Ricetta(
            id=ricetta_base.id,
            nome_ricetta_override=ricetta_base.nome_ricetta.upper(),
            colazione_override=ricetta_base.colazione,
            spuntino_override=ricetta_base.spuntino,
            principale_override=ricetta_base.principale,
            contorno_override=ricetta_base.contorno,
            colazione_sec_override=ricetta_base.colazione_sec,
            complemento_override=ricetta_base.complemento,
            user_id=user_id,
            enabled=False,
        )
        db.session.add(ricetta)
    else:
        ricetta.id = ricetta_id
        ricetta.user_id = user_id
        ricetta.enabled = not ricetta.enabled

    db.session.commit()


def get_ingredienti_ricetta_service(recipe_id, user_id):

    vir = aliased(VIngredientiRicetta)
    vr = aliased(VRicetta)
    va = aliased(VAlimento)

    # Sottoquery EXISTS
    subquery = (
        db.session.query(vr.id)
        .filter(and_(vr.id == recipe_id, vr.user_id == user_id))
        .exists()
    )

    # Query principale
    query = (
        db.session.query(
            va.id.label("id_alimento"),
            va.nome.label("nome_alimento"),
            vr.id.label("id_ricetta"),
            vr.nome_ricetta.label("nome_ricetta"),
            vir.qta.label("quantita")
        )
        .join(va, and_(va.id == vir.id_alimento, vir.user_id == va.user_id))
        .join(vr, and_(vr.id == vir.id_ricetta, vir.user_id == vr.user_id))
        .filter(
            and_(
                vr.id == recipe_id,
                or_(
                    and_(vr.user_id == user_id, not_(vr.removed)),
                    and_(vr.user_id == 0, not_(subquery))
                )
            )
        )
    )

    results = query.all()

    r = []
    for res in results:
        r.append({
            "id": res.id_alimento,
            "nome": res.nome_alimento,
            "nome_ricetta": res.nome_ricetta,
            "qta": res.quantita,
            "id_ricetta": res.id_ricetta
        })

    return r


def salva_nuova_ricetta(name, breakfast, snack, main, side, second_breakfast, complemento, user_id):
    seq_id = get_sequence_value('dieta.seq_id_ricetta')

    ricetta = Ricetta(
        id=seq_id,
        nome_ricetta_override=name.upper(),
        colazione_override=breakfast,
        spuntino_override=snack,
        principale_override=main,
        contorno_override=side,
        colazione_sec_override=second_breakfast,
        complemento_override=complemento,
        enabled=True,
        user_id=user_id
    )

    db.session.add(ricetta)
    db.session.commit()