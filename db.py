import psycopg2
from psycopg2 import extensions
from psycopg2 import extras
import os
from dotenv import load_dotenv
from typing import Optional

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Ora le variabili d'ambiente sono disponibili come variabili Python
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")


def connect_to_db(real_dict_cursor: bool=True) -> Optional[psycopg2.extensions.connection]:

    try:
        return psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            database=DB_NAME,
            port=DB_PORT,
            cursor_factory=extras.RealDictCursor if real_dict_cursor else None
        )
    except (Exception, psycopg2.Error) as error:
        print(f"Errore durante la connessione al database: {error}")
        return None


