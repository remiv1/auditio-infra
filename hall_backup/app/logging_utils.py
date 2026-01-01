"""
logging_utils.py
Module utilitaire pour la gestion centralisée du logging Flask.
Peut être importé et utilisé dans d'autres modules de l'application.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

def get_log_path_for_domain(domain: str) -> str:
    """
    Retourne le chemin du fichier de log pour un domaine donné.
    """
    if domain == "testing":
        return "/app/logs/testing/flask.log"
    elif domain == "erp":
        return "/app/logs/erp/flask.log"
    else:
        return "/app/logs/flask.log"

_domain_handlers = {}

def get_domain_logger(app: Flask, domain: str):
    """
    Retourne un logger Flask configuré pour le domaine (handler rotatif par domaine).
    """
    global _domain_handlers
    log_path = get_log_path_for_domain(domain)
    if domain not in _domain_handlers:
        log_dir = os.path.dirname(log_path)
        os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=2)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
        handler.setFormatter(formatter)
        _domain_handlers[domain] = handler
        app.logger.addHandler(handler)
    return app.logger

def setup_logging(app: Flask, log_path: str = None):
    """
    Configure le logging Flask pour écrire dans un fichier rotatif global (fallback).
    À appeler au démarrage de l'application.
    :param app: instance Flask
    :param log_path: chemin du fichier de log (défaut: /app/logs/flask.log)
    """
    if log_path is None:
        log_path = os.environ.get('FLASK_LOG_PATH', '/app/logs/flask.log')
    log_dir = os.path.dirname(log_path)
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=2)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def log_event(app: Flask, message: str, level: str = "info", domain: str = None):
    """
    Fonction de log centralisée, loggue dans le fichier du domaine si précisé.
    :param app: instance Flask
    :param message: message à logger
    :param level: niveau ('info', 'debug', 'warning', 'error')
    :param domain: domaine (testing, erp, etc.)
    """
    logger = app.logger
    if domain:
        logger = get_domain_logger(app, domain)
    if level == "debug":
        logger.debug(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    else:
        logger.info(message)
