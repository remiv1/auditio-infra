"""
wol.py
Fonctions Wake-on-LAN et vérifications réseau pour Hall - Flask Gateway.
"""

import subprocess
import os
import requests
from typing import Dict, Any

from flask import Flask

from logging_utils import log_event


def send_wol(app: Flask, mac_address: str, domain: str = None) -> bool:
    """
    Envoie un paquet Wake-on-LAN.
    
    :param app: Instance Flask pour le logging
    :param mac_address: Adresse MAC du serveur à réveiller
    :param domain: Domaine associé (pour le logging par domaine)
    :return: True si succès, False sinon
    """
    # Appel à l'API WoL dédiée (dans le conteneur hall-wol)
    WOL_API_URL = os.environ.get("WOL_API_URL", "http://hall-wol:5001/wol")
    WOL_API_KEY = os.environ.get("WOL_API_KEY", "change-me")
    WOL_BROADCAST = os.environ.get("WOL_BROADCAST", "192.168.1.255")
    try:
        response = requests.post(
            WOL_API_URL,
            json={"mac": mac_address, "broadcast": WOL_BROADCAST},
            headers={"X-API-KEY": WOL_API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            log_event(
                app,
                f"WoL envoyé à {mac_address} via API | réponse: {response.json()}",
                domain=domain
            )
            return True
        else:
            log_event(
                app,
                f"Erreur WoL API pour {mac_address} | status: {response.status_code} | body: {response.text}",
                level="error",
                domain=domain
            )
            return False
    except Exception as e:
        log_event(
            app,
            f"Erreur lors de l'appel à l'API WoL: {e}",
            level="error",
            domain=domain
        )
        return False


def ping_server(ip_address: str, timeout: int = 2) -> bool:
    """
    Vérifie si le serveur répond au ping.
    
    :param ip_address: Adresse IP du serveur
    :param timeout: Timeout en secondes
    :return: True si le serveur répond, False sinon
    """
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), ip_address],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def check_health(url: str, endpoint: str, timeout: int = 5) -> bool:
    """
    Vérifie le health check d'un service.
    
    :param url: URL de base du service
    :param endpoint: Endpoint de health check (ex: /health)
    :param timeout: Timeout en secondes
    :return: True si le service répond avec un status 200
    """
    try:
        health_url = f"{url.rstrip('/')}{endpoint}"
        response = requests.get(health_url, timeout=timeout, verify=False)
        return response.status_code == 200
    except Exception:
        return False


def check_testing_project_health(project: Dict[str, Any], testing_server_ip: str) -> bool:
    """
    Vérifie si un projet testing est accessible.
    
    :param project: Dictionnaire contenant les infos du projet
    :param testing_server_ip: IP du serveur testing
    :return: True si le projet répond correctement
    """
    if not testing_server_ip:
        return False

    health_path = project.get("health_check_path", "/health")
    url = f"http://{testing_server_ip}:{project['port']}{health_path}"

    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
