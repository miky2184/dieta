# 1. CONFIGURAZIONE BASE DEL LOGGER
# File: app/config/logging_config.py

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(app=None, log_level=None):
    """
    Configura il sistema di logging per l'applicazione Flask.

    Args:
        app: Istanza Flask (opzionale)
        log_level: Livello di log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """

    # Crea directory per i log se non esiste
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Determina il livello di log
    if log_level is None:
        log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())

    # Configurazione root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Rimuovi handler esistenti per evitare duplicati
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. CONSOLE HANDLER (per sviluppo)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # 2. FILE HANDLER ROTATIVO (per produzione)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)

    # 3. ERROR FILE HANDLER (solo errori)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)

    # FORMATTATORI
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Applica formattatori
    console_handler.setFormatter(simple_formatter)
    file_handler.setFormatter(detailed_formatter)
    error_handler.setFormatter(detailed_formatter)

    # Aggiungi handler al root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    # Configura logger Flask se fornito
    if app:
        app.logger.handlers = root_logger.handlers
        app.logger.setLevel(log_level)

    # Configura logger di terze parti
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    logging.info("Sistema di logging configurato correttamente")
