"""
config.py
Gestion de la configuration pour Hall - Flask Gateway.
Chargement et cache du fichier domains.json.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


# Variables d'environnement
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config/domains.json")
TESTING_SERVER_IP = os.environ.get("TESTING_SERVER_IP", "")
PROXY_TIMEOUT = 30.0

# Cache de la configuration
_config_cache: Dict[str, Any] | None = None
_config_mtime: float | None = None


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """Charge la configuration depuis le fichier JSON avec cache."""
    global _config_cache, _config_mtime

    config_path = Path(CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration non trouvée: {CONFIG_PATH}")

    current_mtime = config_path.stat().st_mtime

    if force_reload or _config_cache is None or _config_mtime != current_mtime:
        with open(config_path, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
        _config_mtime = current_mtime

    if _config_cache is None:
        raise ValueError("Échec du chargement de la configuration")

    return _config_cache


def get_domain_config(domain: str) -> Optional[Dict[str, Any]]:
    """Récupère la configuration d'un domaine."""
    config = load_config()
    return config.get("domains", {}).get(domain)


def get_global_config() -> Dict[str, Any]:
    """Récupère la configuration globale."""
    config = load_config()
    return config.get("global", {})
