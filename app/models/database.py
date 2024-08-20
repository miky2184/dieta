import psycopg2
import os
from psycopg2 import extras
from contextlib import contextmanager
import logging

# Configura il logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_db_config():
    """
    Recupera la configurazione del database dalle variabili d'ambiente.

    Restituisce:
        dict: Un dizionario contenente le chiavi 'user', 'password', 'host', 'port', 'database'.

    Solleva:
        ValueError: Se una delle variabili d'ambiente necessarie non è impostata.
    """
    config = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME")
    }

    # Verifica che tutte le configurazioni siano state fornite
    missing_keys = [key for key, value in config.items() if value is None]
    if missing_keys:
        raise ValueError(f"Mancano le seguenti variabili d'ambiente per la configurazione del DB: {', '.join(missing_keys)}")

    return config

@contextmanager
def get_db_connection():
    """
    Gestisce una connessione al database PostgreSQL utilizzando un context manager.

    Esempio di utilizzo:
        with get_db_connection() as conn:
            # Usa la connessione 'conn' qui
            ...

    Se si verifica un'eccezione, viene registrato un messaggio di errore e l'eccezione viene rilanciata.
    La connessione viene chiusa automaticamente alla fine del blocco.

    Restituisce:
        conn (psycopg2.extensions.connection): Oggetto connessione al database.
    """
    try:
        conn = psycopg2.connect(**get_db_config(), cursor_factory=extras.RealDictCursor)
        yield conn
    except psycopg2.DatabaseError as db_err:
        logger.error(f"Errore nel database: {db_err}")
        raise
    except Exception as e:
        logger.error(f"Errore non gestito: {e}")
        raise
    finally:
        conn.close()
        logger.info("Connessione al database chiusa.")

def get_cursor(conn):
    """
    Ottiene un cursore dal database per eseguire query.

    Parametri:
        conn (psycopg2.extensions.connection): La connessione al database da cui ottenere il cursore.

    Restituisce:
        cursor (psycopg2.extensions.cursor): Un oggetto cursore per eseguire operazioni sul database.
    """
    try:
        return conn.cursor()
    except psycopg2.Error as e:
        logger.error(f"Errore durante l'ottenimento del cursore: {e}")
        raise
