"""
functions.py
Fonctions utilitaires pures pour Hall - Flask Gateway.
Contient les décorateurs, vérifications de sécurité et politiques.
"""

import ipaddress
from typing import Dict, Any, Callable, TypeVar, Optional
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo
from flask import session, redirect, url_for, request, abort

from database import get_last_activity
from logging_utils import log_event


F = TypeVar("F", bound=Callable[..., Any])


def require_admin_login(view_func: F) -> F:
    """Décorateur pour protéger les routes admin."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_bp.admin_login", next=request.url))
        return view_func(*args, **kwargs)
    return wrapped_view  # type: ignore


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


def require_domain_access(get_domain_config_func: Callable[[str], Optional[Dict[str, Any]]]):
    """
    Fabrique de décorateur pour vérifier l'accès au domaine.
    Prend en paramètre la fonction get_domain_config pour éviter les imports circulaires.
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def decorated_function(domain: str, *args: Any, **kwargs: Any) -> Any:
            from flask import current_app
            domain_config = get_domain_config_func(domain)
            if not domain_config:
                abort(404, description="Domaine non configuré")

            client_ip = request.remote_addr
            if not check_ip_allowed(domain_config, client_ip):
                log_event(current_app, f"Accès refusé pour {domain} depuis IP: {client_ip}", level="warning", domain=domain)
                abort(403, description="Accès non autorisé")

            return f(domain, *args, **kwargs)
        return decorated_function  # type: ignore
    return decorator


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


def get_domain_from_host() -> Optional[str]:
    """Extrait le nom de domaine depuis le Host header (ex: testing.audit-io.fr -> testing)."""
    host = request.headers.get('Host', '').split(':')[0]  # Enlève le port si présent
    # Mapping des sous-domaines vers les clés de configuration
    domain_mapping = {
        'testing.audit-io.fr': 'testing',
        'erp.audit-io.fr': 'erp'
    }
    return domain_mapping.get(host)
