"""
api_bp.py
Blueprint pour les routes API et utilitaires de Hall - Flask Gateway.
"""

from flask import Blueprint, render_template, jsonify, request, current_app

from config import load_config, get_domain_config, get_global_config
from database import update_activity, update_wol_activity
from functions import (
    require_domain_access, should_be_awake, get_domain_from_host,
    require_admin_login
)
from wol import send_wol, ping_server, check_health
from logging_utils import log_event


api_bp = Blueprint('api_bp', __name__)


# Création du décorateur avec la fonction get_domain_config
domain_access = require_domain_access(get_domain_config)


@api_bp.route("/")
def index():
    """Page d'accueil ou page d'attente si domaine virtuel détecté."""
    # Si un domaine virtuel est détecté via le Host header
    domain = get_domain_from_host()
    if domain and get_domain_config(domain):
        return domain_page(domain)
    
    # Sinon, afficher la page d'accueil normale
    config = load_config()
    domains = list(config.get("domains", {}).keys())
    return render_template("index.html", domains=domains)


@api_bp.route("/<domain>")
@domain_access
def domain_page(domain: str):
    """Page d'attente pour un domaine."""
    domain_config = get_domain_config(domain)
    global_config = get_global_config()

    update_activity(domain)
    log_event(current_app, f"Accès au domaine {domain}", domain=domain)

    return render_template(
        "waiting.html",
        domain=domain,
        config=domain_config,
        polling_interval=global_config.get("polling_interval_seconds", 3)
    )


@api_bp.route("/api/status/<domain>")
@domain_access
def api_status(domain: str):
    """API pour vérifier le statut d'un domaine."""
    domain_config = get_domain_config(domain)
    global_config = get_global_config()

    if not domain_config:
        return jsonify({"error": "Domaine non configuré"}), 404

    server = domain_config.get("server", {})
    redirect_config = domain_config.get("redirect", {})

    # Vérifications
    server_online = ping_server(
        server.get("ip"),
        global_config.get("ping_timeout_seconds", 2)
    )

    service_ready = False
    if server_online and redirect_config.get("health_check"):
        service_ready = check_health(
            redirect_config.get("url"),
            redirect_config.get("health_check"),
            global_config.get("health_check_timeout_seconds", 5)
        )

    # Politique
    should_wake, wake_reason = should_be_awake(domain, domain_config)

    return jsonify({
        "domain": domain,
        "server_online": server_online,
        "service_ready": service_ready,
        "ready": server_online and service_ready,
        "redirect_url": redirect_config.get("url") if service_ready else None,
        "policy": {
            "type": domain_config.get("policy", {}).get("type"),
            "should_be_awake": should_wake,
            "reason": wake_reason
        }
    })


@api_bp.route("/api/wake/<domain>", methods=["POST"])
@domain_access
def api_wake(domain: str):
    """API pour réveiller le serveur d'un domaine."""
    domain_config = get_domain_config(domain)

    if not domain_config:
        return jsonify({"success": False, "message": "Domaine non configuré"}), 404
    policy = domain_config.get("policy", {})

    if not policy.get("wol_enabled", True):
        return jsonify({"success": False, "message": "WoL désactivé pour ce domaine"}), 400

    server = domain_config.get("server", {})
    mac = server.get("mac")

    if not mac:
        return jsonify({"success": False, "message": "MAC non configurée"}), 400

    success = send_wol(current_app, mac, domain=domain)
    update_activity(domain)
    log_event(current_app, f"[WOL] Domaine: {domain} | MAC: {mac} | Success: {success}", domain=domain)

    # Incrémenter le compteur de boot
    if success:
        update_wol_activity(domain)

    return jsonify({
        "success": success,
        "message": "WoL envoyé" if success else "Échec WoL"
    })


@api_bp.route("/api/activity/<domain>", methods=["POST"])
@domain_access
def api_activity(domain: str):
    """API pour signaler une activité (maintient le serveur éveillé)."""
    update_activity(domain)
    return jsonify({"success": True, "message": "Activité enregistrée"})


@api_bp.route("/api/config")
@require_admin_login
def api_config():
    """API pour récupérer la configuration (admin only)."""
    config = load_config()
    # Masquer les infos sensibles
    safe_config = {
        "domains": {
            name: {
                "description": d.get("description"),
                "policy": d.get("policy"),
                "server": {"ip": d["server"]["ip"]}
            }
            for name, d in config.get("domains", {}).items()
        },
        "global": config.get("global", {})
    }
    return jsonify(safe_config)


@api_bp.route("/api/reload", methods=["POST"])
@require_admin_login
def api_reload():
    """API pour recharger la configuration."""
    try:
        load_config(force_reload=True)
        return jsonify({"success": True, "message": "Configuration rechargée"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route("/api/testing/status/<name>")
def api_testing_status(name: str):
    """API pour vérifier le statut d'un projet testing."""
    from database import get_testing_project
    from wol import check_testing_project_health
    from config import TESTING_SERVER_IP
    
    project = get_testing_project(name)
    if not project:
        return jsonify({"error": "Projet non trouvé"}), 404

    is_healthy = check_testing_project_health(project, TESTING_SERVER_IP)

    return jsonify({
        "name": project["name"],
        "display_name": project["display_name"],
        "port": project["port"],
        "active": bool(project["active"]),
        "healthy": is_healthy,
        "url": f"/testing/{project['name']}/"
    })
