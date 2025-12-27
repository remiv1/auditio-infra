"""
Hall - Flask Gateway
Orchestrateur pour le réveil à la demande des serveurs
Gestion multi-domaines avec politiques configurables
+ Gestion des projets testing avec authentification
"""

import os
import json
import sqlite3
import subprocess
import ipaddress
from typing import Dict, Any, List, Callable, TypeVar, Optional
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
import requests
from flask import (
    Flask, render_template, jsonify, request, abort, session, redirect, url_for, flash, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me-in-production')

# Authentification admin simple
def require_admin_login(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login", next=request.url))
        return view_func(*args, **kwargs)
    return wrapped_view

# Route de login admin
@app.route("/admin/login", methods=["GET", "POST"], endpoint="admin_login")
def admin_login():
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        flash("Aucun mot de passe admin n'est défini. Veuillez définir la variable d'environnement ADMIN_PASSWORD.", "error")
    if request.method == "POST":
        password = request.form.get("password", "")
        if admin_password and password == admin_password:
            session["admin_authenticated"] = True
            next_url = request.args.get("next") or url_for("admin")
            return redirect(next_url)
        flash("Mot de passe incorrect", "error")
    return render_template("admin_login.html")

# Route de logout admin
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    flash("Déconnecté", "info")
    return redirect(url_for("admin_login"))

# Configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/data/hall.db")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config/domains.json")
TESTING_SERVER_IP = os.environ.get("TESTING_SERVER_IP", "")  # IP du serveur testing
PROXY_TIMEOUT = 30.0

# Cache de la configuration et de l'activité
_config_cache: Dict[str, Any] | None = None
_config_mtime: float | None = None
_activity_cache: Dict[str, Any] = {}  # {domain: last_activity_datetime}


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
    # Table pour les projets testing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS testing_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            port INTEGER NOT NULL,
            password_hash TEXT NOT NULL,
            description TEXT,
            health_check_path TEXT DEFAULT '/health',
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Table pour les logs d'accès testing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS testing_access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            project_name TEXT NOT NULL,
            client_ip TEXT,
            action TEXT NOT NULL
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


# Extraction du domaine depuis le Host header
def get_domain_from_host() -> Optional[str]:
    """Extrait le nom de domaine depuis le Host header (ex: testing.audit-io.fr -> testing)."""
    host = request.headers.get('Host', '').split(':')[0]  # Enlève le port si présent
    # Mapping des sous-domaines vers les clés de configuration
    domain_mapping = {
        'testing.audit-io.fr': 'testing',
        'erp.audit-io.fr': 'erp'
    }
    return domain_mapping.get(host)


# Routes
@app.route("/")
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


@app.route("/api/wake/<domain>", methods=["POST"])
@require_domain_access
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
@require_admin_login
def api_config():
    """API pour récupérer la configuration (admin only)."""
    # TODO: Vérifier accès admin
    config = load_config()
    # Masquer les infos sensibles
    safe_config: Dict[str, Any] = {
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
@require_admin_login
def api_reload():
    """API pour recharger la configuration."""
    # TODO: Vérifier accès admin
    try:
        load_config(force_reload=True)
        return jsonify({"success": True, "message": "Configuration rechargée"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/admin")
@require_admin_login
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


# ============================================
# GESTION DES PROJETS TESTING
# ============================================

def get_testing_project(name: str) -> Optional[Dict[str, Any]]:
    """Récupère un projet testing par son nom."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM testing_projects WHERE name = ? AND active = 1", (name,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_all_testing_projects() -> List[Dict[str, Any]]:
    """Récupère tous les projets testing."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM testing_projects ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def log_testing_access(project_name: str, action: str):
    """Log un accès à un projet testing."""
    client_ip = request.remote_addr if request else None
    conn = get_db()
    conn.execute(
        "INSERT INTO testing_access_logs (project_name, client_ip, action) VALUES (?, ?, ?)",
        (project_name, client_ip, action)
    )
    conn.commit()
    conn.close()


# Routes Admin pour les projets Testing
@app.route("/admin/testing")
@require_admin_login
def admin_testing():
    """Page d'administration des projets testing."""
    projects = get_all_testing_projects()

    # Récupérer les logs récents
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM testing_access_logs ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    conn.close()

    return render_template(
        "admin_testing.html",
        projects=projects,
        logs=logs,
        testing_server_ip=TESTING_SERVER_IP
    )


@app.route("/admin/testing/add", methods=["GET", "POST"])
@require_admin_login
def admin_testing_add():
    """Ajouter un nouveau projet testing."""
    if request.method == "POST":
        name = request.form.get("name", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        port = request.form.get("port", "").strip()
        password = request.form.get("password", "")
        description = request.form.get("description", "").strip()
        health_check_path = request.form.get("health_check_path", "/health").strip()

        # Validation
        if not name or not display_name or not port or not password:
            flash("Tous les champs obligatoires doivent être remplis", "error")
            return redirect(url_for("admin_testing_add"))

        if not name.isalnum():
            flash("Le nom doit contenir uniquement des lettres et chiffres", "error")
            return redirect(url_for("admin_testing_add"))

        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            flash("Le port doit être un nombre entre 1 et 65535", "error")
            return redirect(url_for("admin_testing_add"))

        # Vérifier que le nom n'existe pas
        if get_testing_project(name):
            flash("Un projet avec ce nom existe déjà", "error")
            return redirect(url_for("admin_testing_add"))

        # Créer le projet
        password_hash = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO testing_projects (name, display_name, port, password_hash, description, health_check_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, display_name, port, password_hash, description, health_check_path))
            conn.commit()
            flash(f"Projet '{display_name}' créé avec succès", "success")
        except sqlite3.IntegrityError:
            flash("Erreur lors de la création du projet", "error")
        finally:
            conn.close()

        return redirect(url_for("admin_testing"))

    return render_template("admin_testing_form.html", project=None)


@app.route("/admin/testing/edit/<name>", methods=["GET", "POST"])
@require_admin_login
def admin_testing_edit(name: str):
    """Modifier un projet testing."""
    project = get_testing_project(name)
    if not project:
        flash("Projet non trouvé", "error")
        return redirect(url_for("admin_testing"))

    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        port = request.form.get("port", "").strip()
        password = request.form.get("password", "")
        description = request.form.get("description", "").strip()
        health_check_path = request.form.get("health_check_path", "/health").strip()
        active = request.form.get("active") == "on"

        # Validation
        if not display_name or not port:
            flash("Nom d'affichage et port sont obligatoires", "error")
            return redirect(url_for("admin_testing_edit", name=name))

        try:
            port = int(port)
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            flash("Le port doit être un nombre entre 1 et 65535", "error")
            return redirect(url_for("admin_testing_edit", name=name))

        conn = get_db()
        if password:
            # Mettre à jour avec nouveau mot de passe
            password_hash = generate_password_hash(password)
            conn.execute("""
                UPDATE testing_projects 
                SET display_name = ?, port = ?, password_hash = ?, description = ?, 
                    health_check_path = ?, active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
                """, (
                    display_name, port, password_hash, description, health_check_path,
                    1 if active else 0, name
                )
            )
        else:
            # Garder l'ancien mot de passe
            conn.execute("""
                UPDATE testing_projects 
                SET display_name = ?, port = ?, description = ?, 
                    health_check_path = ?, active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (display_name, port, description, health_check_path, 1 if active else 0, name))
        conn.commit()
        conn.close()

        flash(f"Projet '{display_name}' mis à jour", "success")
        return redirect(url_for("admin_testing"))

    return render_template("admin_testing_form.html", project=project)


@app.route("/admin/testing/delete/<name>", methods=["POST"])
@require_admin_login
def admin_testing_delete(name: str):
    """Supprimer un projet testing."""
    conn = get_db()
    conn.execute("DELETE FROM testing_projects WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    flash(f"Projet '{name}' supprimé", "success")
    return redirect(url_for("admin_testing"))


def check_testing_project_health(project: Dict[str, Any]) -> bool:
    """Vérifie si un projet testing est accessible."""
    if not TESTING_SERVER_IP:
        return False

    health_path = project.get("health_check_path", "/health")
    url = f"http://{TESTING_SERVER_IP}:{project['port']}{health_path}"

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


@app.route("/api/testing/status/<name>")
def api_testing_status(name: str):
    """API pour vérifier le statut d'un projet testing."""
    project = get_testing_project(name)
    if not project:
        return jsonify({"error": "Projet non trouvé"}), 404

    is_healthy = check_testing_project_health(project)

    return jsonify({
        "name": project["name"],
        "display_name": project["display_name"],
        "port": project["port"],
        "active": bool(project["active"]),
        "healthy": is_healthy,
        "url": f"/testing/{project['name']}/"
    })


# Routes publiques pour les projets Testing
@app.route("/testing/<project_name>/login", methods=["GET", "POST"])
def testing_login(project_name: str):
    """Page de connexion pour un projet testing."""
    project = get_testing_project(project_name)
    if not project:
        abort(404, description="Projet non trouvé")

    if request.method == "POST":
        password = request.form.get("password", "")

        if check_password_hash(project["password_hash"], password):
            session[f"testing_auth_{project_name}"] = True
            session[f"testing_name_{project_name}"] = project["display_name"]
            log_testing_access(project_name, "login_success")

            next_url = request.args.get("next", f"/testing/{project_name}/")
            return redirect(next_url)

        log_testing_access(project_name, "login_failed")
        flash("Mot de passe incorrect", "error")

    return render_template(
        "testing_login.html",
        project=project,
        next=request.args.get("next", f"/testing/{project_name}/")
    )


@app.route("/testing/<project_name>/logout")
def testing_logout(project_name: str):
    """Déconnexion d'un projet testing."""
    session.pop(f"testing_auth_{project_name}", None)
    session.pop(f"testing_name_{project_name}", None)
    flash("Déconnecté", "success")
    return redirect(url_for("index"))


@app.route("/testing/<project_name>/", defaults={"path": ""})
@app.route("/testing/<project_name>/<path:path>")
def testing_proxy(project_name: str, path: str):
    """Proxy vers le projet testing après authentification."""
    project = get_testing_project(project_name)
    if not project:
        abort(404, description="Projet non trouvé")

    # Vérifier l'authentification
    if not session.get(f"testing_auth_{project_name}"):
        return redirect(url_for("testing_login", project_name=project_name, next=request.url))

    # Construire l'URL cible
    if not TESTING_SERVER_IP:
        abort(503, description="Serveur testing non configuré")

    target_url = f"http://{TESTING_SERVER_IP}:{project['port']}/{path}"

    # Ajouter les query params
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"

    # Préparer les headers
    headers = {
        key: value for key, value in request.headers
        if key.lower() not in ["host", "cookie", "connection"]
    }
    headers["X-Forwarded-For"] = request.remote_addr or ""
    headers["X-Forwarded-Proto"] = request.scheme
    headers["X-Project-Name"] = project_name

    try:
        with httpx.Client(timeout=PROXY_TIMEOUT) as client:
            resp = client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=request.get_data(),
            )

        # Filtrer les headers de réponse
        excluded_headers = ["content-encoding", "transfer-encoding", "connection"]
        response_headers = [
            (name, value) for name, value in resp.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(
            resp.content,
            status=resp.status_code,
            headers=response_headers
        )

    except httpx.ConnectError:
        log_testing_access(project_name, "proxy_error_connect")
        abort(503, description="Service temporairement indisponible")
    except httpx.TimeoutException:
        log_testing_access(project_name, "proxy_error_timeout")
        abort(504, description="Le service met trop de temps à répondre")
    except Exception as e:
        app.logger.error(f"Erreur proxy vers {project_name}: {e}")
        abort(500, description="Erreur interne")

# Initialisation
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
