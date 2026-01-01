"""
wol.py
Fonctions Wake-on-LAN et vérifications réseau pour Hall - Flask Gateway.
"""

import subprocess
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
    try:
        result = subprocess.run(
            ["wakeonlan", mac_address],
            check=True,
            capture_output=True,
            text=True
        )
        log_event(
            app,
            f"WoL envoyé à {mac_address} | stdout: {result.stdout.strip()} | stderr: {result.stderr.strip()} | returncode: {result.returncode}",
            domain=domain
        )
        return True
    except subprocess.CalledProcessError as e:
        log_event(
            app,
            f"Erreur WoL pour {mac_address} | stdout: {e.stdout.strip()} | stderr: {e.stderr.strip()} | returncode: {e.returncode}",
            level="error",
            domain=domain
        )
        return False
    except FileNotFoundError:
        log_event(
            app,
            f"Commande 'wakeonlan' non trouvée. Installez-la avec 'apt install wakeonlan'",
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
