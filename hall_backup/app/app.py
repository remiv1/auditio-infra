"""
Hall - Flask Gateway
Orchestrateur pour le réveil à la demande des serveurs
Gestion multi-domaines avec politiques configurables
+ Gestion des projets testing avec authentification

Fichier principal : point d'entrée de l'application Flask.
"""

import os
from flask import Flask

from logging_utils import setup_logging
from database import init_db
from api_bp import api_bp
from admin_bp import admin_bp
from testing_bp import testing_bp


def create_app():
    """Factory pour créer l'application Flask."""
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me-in-production')

    # Configuration du logging
    setup_logging(app)

    # Enregistrement des blueprints
    app.register_blueprint(api_bp)          # Routes / et /api/*
    app.register_blueprint(admin_bp)        # Routes /admin/*
    app.register_blueprint(testing_bp)      # Routes /testing/*

    # Initialisation de la base de données
    with app.app_context():
        init_db()

    return app


# Création de l'application
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
