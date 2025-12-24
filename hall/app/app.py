"""
Hall - Flask Gateway
Orchestrateur pour le réveil à la demande des serveurs
Gestion multi-domaines avec politiques configurables
"""

import os
import json
import sqlite3
import subprocess
import ipaddress
from typing import Dict, Any, List, Callable, TypeVar
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo
import requests

from flask import Flask, render_template, jsonify, request, abort

app = Flask(__name__)

# Configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/data/hall.db")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config/domains.json")

# Cache de la configuration et de l'activité
_config_cache = None
_config_mtime = None
_activity_cache = {}  # {domain: last_activity_datetime}


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

    return _config_cache


def get_domain_config(domain: str) -> Optional[Dict[str, Any]]:
    """Récupère la configuration d'un domaine."""
    config = load_config()
    return config.get("domains", {}).get(domain)


def get_global_config() -> Dict[str, Any]:
    """Récupère la configuration globale."""
    config = load_config()
    return config.get("global", {})


# Base de données
def get_db():
    """Connexion à la base de données SQLite."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialisation de la base de données."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            domain TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT,
            details TEXT,
            client_ip TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            domain TEXT PRIMARY KEY,
            last_activity DATETIME NOT NULL,
            last_wol DATETIME,
            boot_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def log_action(domain: str, action: str, status: str | None = None, details: str | None = None):
    """Enregistre une action dans les logs."""
    client_ip = request.remote_addr if request else None
    conn = get_db()
    conn.execute(
        "INSERT INTO logs (domain, action, status, details, client_ip) VALUES (?, ?, ?, ?, ?)",
        (domain, action, status, details, client_ip)
    )
    conn.commit()
    conn.close()


def update_activity(domain: str):
    """Met à jour le timestamp de dernière activité."""
    global _activity_cache
    now = datetime.now()
    _activity_cache[domain] = now

    conn = get_db()
    conn.execute("""
        INSERT INTO activity (domain, last_activity) VALUES (?, ?)
        ON CONFLICT(domain) DO UPDATE SET last_activity = ?
    """, (domain, now, now))
    conn.commit()
    conn.close()


def get_last_activity(domain: str) -> Optional[datetime]:
    """Récupère la dernière activité d'un domaine."""
    if domain in _activity_cache:
        return _activity_cache[domain]

    conn = get_db()
    row = conn.execute(
        "SELECT last_activity FROM activity WHERE domain = ?", (domain,)
    ).fetchone()
    conn.close()

    if row:
        return datetime.fromisoformat(row["last_activity"])
    return None


# Politiques de réveil
def is_within_schedule(domain_config: Dict[str, Any]) -> bool:
    """Vérifie si on est dans les horaires programmés."""
    policy = domain_config.get("policy", {})

    if policy.get("type") != "scheduled":
        return True

    schedule = policy.get("schedule", {})
    tz_name = schedule.get("timezone", "Europe/Paris")
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # Vérifier le jour
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    current_day = day_names[now.weekday()]

    if current_day not in schedule.get("days", []):
        return False

    # Vérifier l'heure
    start_hour = schedule.get("start_hour", 0)
    end_hour = schedule.get("end_hour", 24)

    return start_hour <= now.hour < end_hour


def should_be_awake(domain: str, domain_config: Dict[str, Any]) -> tuple[bool, str]:
    """
    Détermine si le serveur devrait être allumé.
    Retourne (should_wake, reason)
    """
    policy = domain_config.get("policy", {})
    policy_type = policy.get("type", "on_demand")

    if policy_type == "always_on":
        return True, "always_on"

    if policy_type == "scheduled":
        if is_within_schedule(domain_config):
            return True, "within_schedule"
        # Hors horaires : vérifier l'activité récente
        idle_timeout = policy.get("idle_timeout_minutes", 60)
        last_activity = get_last_activity(domain)
        if last_activity:
            if datetime.now() - last_activity < timedelta(minutes=idle_timeout):
                return True, "recent_activity"
        return False, "outside_schedule"

    if policy_type == "on_demand":
        idle_timeout = policy.get("idle_timeout_minutes", 20)
        last_activity = get_last_activity(domain)
        if last_activity:
            if datetime.now() - last_activity < timedelta(minutes=idle_timeout):
                return True, "recent_activity"
        # On demand : on réveille sur requête
        return False, "idle_timeout"

    return False, "unknown_policy"


# Vérifications réseau
def send_wol(mac_address: str) -> bool:
    """Envoie un paquet Wake-on-LAN."""
    try:
        subprocess.run(["wakeonlan", mac_address], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def ping_server(ip_address: str, timeout: int = 2) -> bool:
    """Vérifie si le serveur répond au ping."""
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
    """Vérifie le health check d'un service."""
    try:
        health_url = f"{url.rstrip('/')}{endpoint}"
        response = requests.get(health_url, timeout=timeout, verify=False)
        return response.status_code == 200
    except Exception:
        return False


# Sécurité
def check_ip_allowed(domain_config: Dict[str, Any], client_ip: str | None) -> bool:
    """Vérifie si l'IP du client est autorisée."""
    security = domain_config.get("security", {})
    allowed_ips = security.get("allowed_ips", [])

    if not allowed_ips:
        return True

    try:
        if client_ip is None:
            return False
        client = ipaddress.ip_address(client_ip)
        for allowed in allowed_ips:
            if "/" in allowed:
                if client in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:
                if client == ipaddress.ip_address(allowed):
                    return True
    except ValueError:
        return False

    return False

F = TypeVar("F", bound=Callable[..., Any])

def require_domain_access(f: F) -> F:
    """Décorateur pour vérifier l'accès au domaine."""
    @wraps(f)
    def decorated_function(domain: str, *args: Any, **kwargs: Any) -> Any:
        domain_config = get_domain_config(domain)
        if not domain_config:
            abort(404, description="Domaine non configuré")

        client_ip = request.remote_addr
        if not check_ip_allowed(domain_config, client_ip):
            log_action(domain, "access_denied", "forbidden", f"IP: {client_ip}")
            abort(403, description="Accès non autorisé")

        return f(domain, *args, **kwargs)
    return decorated_function  # type: ignore


# Routes
@app.route("/")
def index():
    """Page d'accueil."""
    config = load_config()
    domains = list(config.get("domains", {}).keys())
    return render_template("index.html", domains=domains)


@app.route("/<domain>")
@require_domain_access
def domain_page(domain: str):
    """Page d'attente pour un domaine."""
    domain_config = get_domain_config(domain)
    global_config = get_global_config()

    update_activity(domain)
    log_action(domain, "access", "pending")

    return render_template(
        "waiting.html",
        domain=domain,
        config=domain_config,
        polling_interval=global_config.get("polling_interval_seconds", 3)
    )


@app.route("/api/status/<domain>")
@require_domain_access
def api_status(domain: str):
    """API pour vérifier le statut d'un domaine."""
    domain_config = get_domain_config(domain)
    global_config = get_global_config()

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


@app.route("/api/wake/<domain>", methods=["POST"])
@require_domain_access
def api_wake(domain: str):
    """API pour réveiller le serveur d'un domaine."""
    domain_config = get_domain_config(domain)
    policy = domain_config.get("policy", {})

    if not policy.get("wol_enabled", True):
        return jsonify({"success": False, "message": "WoL désactivé pour ce domaine"}), 400

    server = domain_config.get("server", {})
    mac = server.get("mac")

    if not mac:
        return jsonify({"success": False, "message": "MAC non configurée"}), 400

    success = send_wol(mac)
    update_activity(domain)
    log_action(domain, "wol", "success" if success else "failed", f"MAC: {mac}")

    # Incrémenter le compteur de boot
    if success:
        conn = get_db()
        conn.execute("""
            UPDATE activity SET last_wol = ?, boot_count = boot_count + 1
            WHERE domain = ?
        """, (datetime.now(), domain))
        conn.commit()
        conn.close()

    return jsonify({
        "success": success,
        "message": "WoL envoyé" if success else "Échec WoL"
    })


@app.route("/api/activity/<domain>", methods=["POST"])
@require_domain_access
def api_activity(domain: str):
    """API pour signaler une activité (maintient le serveur éveillé)."""
    update_activity(domain)
    return jsonify({"success": True, "message": "Activité enregistrée"})


@app.route("/api/config")
def api_config():
    """API pour récupérer la configuration (admin only)."""
    # TODO: Vérifier accès admin
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


@app.route("/api/reload", methods=["POST"])
def api_reload():
    """API pour recharger la configuration."""
    # TODO: Vérifier accès admin
    try:
        load_config(force_reload=True)
        return jsonify({"success": True, "message": "Configuration rechargée"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/admin")
def admin():
    """Tableau de bord admin (LAN only)."""
    # TODO: Vérifier que l'accès vient du LAN
    config = load_config()
    domains_config = config.get("domains", {})

    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100"
    ).fetchall()
    activity = conn.execute("SELECT * FROM activity").fetchall()
    conn.close()

    # Enrichir avec les statuts
    domains_status = {}
    for name, conf in domains_config.items():
        server = conf.get("server", {})
        domains_status[name] = {
            "config": conf,
            "online": ping_server(server.get("ip"), 1)
        }

    return render_template(
        "admin.html",
        logs=logs,
        activity=activity,
        domains=domains_status,
        config=config
    )


# Initialisation
with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
