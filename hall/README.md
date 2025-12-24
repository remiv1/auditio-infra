# 🚪 Hall - Orchestrateur d'entrée

Package Docker pour Raspberry Pi servant de gateway intelligente avec réveil à la demande.

## Structure

    hall/
    ├── docker-compose.yml      # Orchestration des services
    ├── Dockerfile.traefik      # Image Traefik personnalisée
    ├── Dockerfile.flask        # Image Flask Gateway
    ├── .env.example            # Variables d'environnement
    ├── app/                    # Application Flask
    │   ├── app.py
    │   ├── requirements.txt
    │   └── templates/
    │       ├── index.html
    │       ├── waiting.html
    │       └── admin.html
    └── traefik/                # Configuration Traefik
        ├── traefik.yml
        ├── dynamic/
        └── acme/

## Démarrage rapide

1. Copier le fichier d'environnement :

        cp .env.example .env

2. Configurer les variables dans `.env`

3. Lancer les services :

        docker-compose up -d

## Services

- **Traefik** : Reverse proxy (ports 80/443)
- **Flask** : Gateway avec page d'attente et API de statut
- **SQLite** : Stockage des logs (volume persistant)

## API

- `GET /<project>` : Page d'attente pour un projet
- `GET /api/status/<project>` : Statut d'un projet
- `POST /api/wake/<project>` : Déclenche le WoL
- `GET /admin` : Tableau de bord (LAN only)
