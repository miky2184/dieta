#app/models/common.py
import json
import os
import re
import sys
from datetime import datetime


def printer(text, level="DEBUG", include_timestamp=False, output=sys.stdout):
    """
    Stampa il testo fornito se il livello di log è maggiore o uguale al livello corrente di log.

    Parametri:
    text (str): Il testo che deve essere stampato.
    level (str): Il livello di log del messaggio ('DEBUG', 'INFO', 'WARNING', 'ERROR'). Default è 'DEBUG'.
    include_timestamp (bool): Se True, include un timestamp nel messaggio di log. Default è False.
    output (file-like object): L'output dove inviare il log (default è sys.stdout).

    Funzionamento:
    - La funzione controlla la variabile d'ambiente 'LOG_LEVEL'.
    - Se il livello del messaggio è maggiore o uguale al livello impostato, il testo viene stampato.
    - Se `include_timestamp` è True, un timestamp viene aggiunto al messaggio.
    - Il messaggio è inviato all'output specificato (console, file, ecc.).

    Livelli di log supportati:
    - DEBUG: Log dettagliato per il debug.
    - INFO: Informazioni generali sull'esecuzione del programma.
    - WARNING: Messaggi di avvertimento.
    - ERROR: Errori che potrebbero impedire il corretto funzionamento del programma.

    Utilizzo:
    - Questa funzione è utile per una gestione flessibile e strutturata del logging.
    """

    log_levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
    current_level = log_levels.get(os.getenv('LOG_LEVEL', 'DEBUG').upper(), 10)
    message_level = log_levels.get(level.upper(), 10)

    if message_level >= current_level:
        if include_timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            text = f"[{timestamp}] {level.upper()}: {text}"
        else:
            text = f"{level.upper()}: {text}"

        print(text, file=output)


def is_valid_email(email):
    # Definizione dell'espressione regolare per validare l'email
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

    # Utilizzo di re.match per verificare se l'email è valida
    if re.match(email_regex, email):
        return True
    else:
        return False


def print_query(in_query, level="DEBUG"):
    printer(str(in_query.statement.compile(compile_kwargs={"literal_binds": True})), level)


def calcola_macronutrienti_rimanenti_service(menu: json):
    remaining_macronutrienti = {}
    if menu:
        for giorno, dati_giorno in menu['day'].items():
            remaining_kcal = round(dati_giorno['kcal'],2)
            remaining_carboidrati = round(dati_giorno['carboidrati'],2)
            remaining_proteine = round(dati_giorno['proteine'],2)
            remaining_grassi = round(dati_giorno['grassi'],2)

            remaining_macronutrienti[giorno] = {
                'kcal': remaining_kcal,
                'carboidrati': remaining_carboidrati,
                'proteine': remaining_proteine,
                'grassi': remaining_grassi
            }
    return remaining_macronutrienti