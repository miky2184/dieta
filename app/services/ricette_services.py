from sqlalchemy import func, and_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.sql import extract

from app.models import db
from app.models.IngredientiRicetta import IngredientiRicetta
from app.models.Ricetta import Ricetta
from app.models.RicettaBase import RicettaBase
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from app.services.db_services import get_sequence_value
from app.services.util_services import print_query


def get_ricette_service(user_id, ids=None, stagionalita:bool=False, attive:bool=False, complemento=None, contorno=False, data_stagionalita=None, percentuale:float = 1.0) -> list[dict]:
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
            percentuale (float, optional): Percentuale

        Returns:
            list[dict]: Lista di ricette arricchite con informazioni nutrizionali, stagionalità e ingredienti.
        """
    # Alias per le tabelle
    vr = aliased(VRicetta)
    vir = aliased(VIngredientiRicetta)
    va = aliased(VAlimento)

    # Filtro per gli alimenti
    filtro_va = VAlimento.filtro_alimenti(user_id, alias=va)

    # Filtro per gli ingredienti
    filtro_vir = VIngredientiRicetta.filtro_ingredienti(user_id, alias=vir)

    # Filtro per le ricette
    filtro_vr = VRicetta.filtro_ricette(user_id, alias=vr)

    # Query principale
    ricetta_subquery = (
        db.session.query(
            vir.id_ricetta.label("id_ricetta"),
            va.nome,
            func.sum(vir.qta * percentuale).label("qta")
        )
        .join(
            va,
            and_(
                va.id == vir.id_alimento,
                filtro_va,
                filtro_vir
            )
        )
        .filter(vir.id_ricetta == vr.id)
        .filter(vir.id_alimento == va.id)
        .filter(vir.user_id == vr.user_id)
        .group_by(vir.id_ricetta, va.nome)
        .subquery()
    )

    ingredienti_subquery = (
        db.session.query(
            vir.id_ricetta.label("id_ricetta"),
            va.id_gruppo,
            func.sum(vir.qta * percentuale).label("qta")
        )
        .join(
            va,
            and_(
                va.id == vir.id_alimento,
                filtro_va,
                filtro_vir
            )
        )
        .filter(vir.id_ricetta == vr.id)
        .filter(vir.id_alimento == va.id)
        .filter(vir.user_id == vr.user_id)
        .group_by(vir.id_ricetta, va.id_gruppo)
        .subquery()
    )



    # Subquery per verificare se una ricetta è vegana
    is_vegan_subquery = (
        db.session.query(
            func.bool_and(va.vegan)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("is_vegan")
    )

    # Subquery per verificare se una ricetta contiene carne rossa (id_gruppo = 4)
    is_carne_rossa_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 4)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("is_carne_rossa")
    )

    contains_fish_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 2)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_fish")
    )

    is_frutta_subquery = (
        db.session.query(
            func.bool_and(va.id_gruppo == 6)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("is_frutta")
    )

    is_verdura_subquery = (
        db.session.query(
            func.bool_and(va.id_gruppo == 7)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("is_verdura")
    )

    is_carne_bianca_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 3)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("is_carne_bianca")
    )

    contains_uova_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 1)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_uova")
    )

    contains_legumi_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 5)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_legumi")
    )

    contains_cereali_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 8)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_cereali")
    )

    contains_pane_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 9)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_pane")
    )

    contains_latticini_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 10)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_latticini")
    )

    contains_frutta_secca_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 12)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_frutta_secca")
    )

    contains_patate_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 14)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_patate")
    )

    contains_grassi_subquery = (
        db.session.query(
            func.bool_or(va.id_gruppo == 15)
        )
        .join(
            vir,
            vir.id_alimento == va.id
        )
        .filter(
            vir.id_ricetta == vr.id,
            filtro_vir,
            filtro_va
        )
        .label("contains_grassi")
    )

    # Query principale
    query = (
        db.session.query(
            vr.user_id.label("user_id"),
            vr.id.label("id_ricetta"),
            vr.nome_ricetta.label("nome_ricetta"),
            func.ceil(
                func.sum(
                    (va.carboidrati / 100) * vir.qta * 4 +
                    (va.proteine / 100) * vir.qta * 4 +
                    (va.grassi / 100) * vir.qta * 9 +
                    (va.fibre / 100) * vir.qta * 2
                )
            ).label('kcal'),
            func.round(
                func.sum((va.carboidrati / 100) * vir.qta),
                2
            ).label('carboidrati'),
            func.round(
                func.sum((va.proteine / 100) * vir.qta),
                2
            ).label('proteine'),
            func.round(
                func.sum((va.grassi / 100) * vir.qta),
                2
            ).label('grassi'),
            func.round(
                func.sum((va.fibre / 100) * vir.qta),
                2
            ).label('fibre'),
            vr.colazione,
            vr.spuntino,
            vr.principale,
            vr.contorno,
            vr.colazione_sec,
            vr.complemento,
            vr.enabled.label('attiva'),
            is_vegan_subquery.label("is_vegan"),  # Campo per indicare se la ricetta è vegana
            is_carne_rossa_subquery.label("is_carne_rossa"),
            is_carne_bianca_subquery.label("is_carne_bianca"),
            contains_fish_subquery.label("contains_fish"),
            is_frutta_subquery.label("is_frutta"),
            is_verdura_subquery.label("is_verdura"),
            contains_uova_subquery.label("contains_uova"),
            contains_legumi_subquery.label("contains_legumi"),
            contains_cereali_subquery.label("contains_cereali"),
            contains_pane_subquery.label("contains_pane"),
            contains_latticini_subquery.label("contains_latticini"),
            contains_frutta_secca_subquery.label("contains_frutta_secca"),
            contains_patate_subquery.label("contains_patate"),
            contains_grassi_subquery.label("contains_grassi"),
            func.json_agg(
                func.json_build_object(
                    'nome', ricetta_subquery.c.nome,
                    'qta', ricetta_subquery.c.qta
                )
            ).label("ricetta"),
            func.json_agg(
                func.json_build_object(
                    'id_gruppo', ingredienti_subquery.c.id_gruppo,
                    'qta', ingredienti_subquery.c.qta
                )
            ).label("ingredienti")
        )
        .select_from(vr)
        .outerjoin(
            vir,
            and_(
                vir.id_ricetta == vr.id,
                filtro_vir
            )
        )
        .outerjoin(
            va,
            and_(
                va.id == vir.id_alimento,
                filtro_va
            )
        )
        .filter(filtro_vr)
        .filter(ingredienti_subquery.c.id_ricetta == vr.id)
        .filter(ingredienti_subquery.c.id_gruppo == va.id_gruppo)
        .filter(ricetta_subquery.c.id_ricetta == vr.id)
        .filter(ricetta_subquery.c.nome == va.nome)
    )

    # Applicazione dei filtri
    if stagionalita:
        data = func.current_date()
        if data_stagionalita:
            data = data_stagionalita

        query = query.filter(
            or_(
                and_(
                    va.id_gruppo == 6, (extract('month', data) == func.any(va.stagionalita))
                ),
                (
                        va.id_gruppo != 6)
                )
        )

    if ids:
        query = query.filter(vr.id == ids)

    if attive:
        query = query.filter(vr.enabled.is_(True))

    if complemento:
        query = query.filter(vr.complemento.is_(True))

    if not complemento:
        query = query.filter(vr.complemento.is_(False))

    if contorno:
        query = query.filter(vr.contorno.is_(True))

    query = query.group_by(vr.user_id,
                           vr.id,
                           vr.nome_ricetta,
                           vr.colazione,
                           vr.spuntino,
                           vr.principale,
                           vr.contorno,
                           vr.colazione_sec,
                           vr.complemento,
                           vr.enabled)

    ricette = []
    for row in query.order_by(vr.nome_ricetta).all():

        info = []
        if row.is_vegan:
            info.append("🌱")  # Emoji per vegano
        if row.is_carne_rossa:
            info.append("🥩")  # Emoji per carne rossa
        if row.contains_fish:
            info.append("🐟")  # Emoji per pesce
        if row.is_frutta:
            info.append("🍎")  # Emoji per frutta
        if row.is_verdura:
            info.append("🥦")  # Emoji per verdura
        if row.is_carne_bianca:
            info.append("🍗")  # Emoji per carne bianca
        if row.contains_uova:
            info.append("🥚")

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
            'is_vegan': row.is_vegan,  # Flag se è vegana
            'is_carne_rossa': row.is_carne_rossa,  # Flag se contiene carne rossa
            'contains_fish': row.contains_fish,
            'is_frutta': row.is_frutta,
            'is_verdura': row.is_verdura,
            'is_carne_bianca': row.is_carne_bianca,
            'contains_uova': row.contains_uova,
            'contains_legumi': row.contains_legumi,
            'contains_cereali': row.contains_cereali,
            'contains_pane': row.contains_pane,
            'contains_latticini': row.contains_latticini,
            'contains_frutta_secca': row.contains_frutta_secca,
            'contains_patate': row.contains_patate,
            'contains_grassi': row.contains_grassi,
            'ricetta': row.ricetta,
            'ingredienti': row.ingredienti,
            'qta': percentuale,
            'info': ''.join(info)
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

    vir1 = aliased(VIngredientiRicetta)
    vr1 = aliased(VRicetta)
    va1 = aliased(VAlimento)

    # Subquery per il filtro NOT EXISTS per VAlimento
    filtro_va = VAlimento.filtro_alimenti(user_id, alias=va1)

    # Subquery per il filtro NOT EXISTS per VIngredientiRicetta
    filtro_vir = VIngredientiRicetta.filtro_ingredienti(user_id, alias=vir1)

    # Subquery per il filtro NOT EXISTS per VRicetta
    filtro_vr = VRicetta.filtro_ricette(user_id, alias=vr1)

    # Query principale
    query = (
        db.session.query(
            va1.id.label("id_alimento"),
            va1.nome.label("nome_alimento"),
            vr1.id.label("id_ricetta"),
            vr1.nome_ricetta.label("nome_ricetta"),
            vir1.qta.label("quantita")
        ).select_from(vr1)
        .outerjoin(
            vir1,
            and_(
                vir1.id_ricetta == vr1.id,
                filtro_vir
            )
        )
        .outerjoin(
            va1,
            and_(
                va1.id == vir1.id_alimento,
                filtro_va
            )
        )
        .filter(filtro_vr)
        .filter(vr1.id == recipe_id)
        .distinct()
    )

    results = query.all()

    print_query(query)

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


def salva_ingredienti_service(recipe_id, ingredient_id, quantity, user_id):

    ingredienti_ricetta = (IngredientiRicetta.query.filter(IngredientiRicetta.id_ricetta_base == recipe_id,
                                                                 IngredientiRicetta.id_alimento_base == ingredient_id,
                                                                 IngredientiRicetta.user_id == user_id)).first()

    if not ingredienti_ricetta:
        ingredienti_ricetta = IngredientiRicetta(
            id_alimento_base=ingredient_id,
            id_ricetta_base=recipe_id,
            user_id=user_id,
            qta_override=quantity,
            removed=False
        )
    else:
        ingredienti_ricetta.id_alimento_base = ingredient_id
        ingredienti_ricetta.id_ricetta_base = recipe_id
        ingredienti_ricetta.user_id = user_id
        ingredienti_ricetta.qta_override = quantity
        ingredienti_ricetta.removed = False


    db.session.add(ingredienti_ricetta)
    db.session.commit()