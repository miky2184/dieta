import os
import random
from datetime import datetime, timedelta, date
from copy import deepcopy
import re
import sqlalchemy
from app.models.Utente import Utente
from app.models import db
from app.models.VAlimento import VAlimento
from app.models.VIngredientiRicetta import VIngredientiRicetta
from app.models.VRicetta import VRicetta
from app.models.GruppoAlimentare import GruppoAlimentare
from app.models.Alimento import Alimento
from app.models.AlimentoBase import AlimentoBase
from app.models.Ricetta import Ricetta
from app.models.RicettaBase import RicettaBase
from app.models.IngredientiRicetta import IngredientiRicetta
from app.models.IngredientiRicettaBase import IngredientiRicettaBase
from sqlalchemy.orm import aliased
from sqlalchemy.sql import extract
from sqlalchemy.dialects.postgresql import insert
import json
from sqlalchemy import insert, update, and_, or_, case, func, exists, asc, String, true, false, select, desc
from collections import defaultdict
from decimal import Decimal
from app.services.util_services import printer
from sqlalchemy.exc import SQLAlchemyError


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
