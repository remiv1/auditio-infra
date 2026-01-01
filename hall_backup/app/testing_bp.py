"""
testing_bp.py
Blueprint pour les routes des projets testing de Hall - Flask Gateway.
Routes publiques pour l'accès aux projets testing avec authentification.
"""

import os
import httpx

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    session, abort, Response, current_app
)
from werkzeug.security import check_password_hash

from config import TESTING_SERVER_IP, PROXY_TIMEOUT
from database import get_testing_project, log_testing_access
from logging_utils import log_event


testing_bp = Blueprint('testing_bp', __name__, url_prefix='/testing')


@testing_bp.route("/<project_name>/login", methods=["GET", "POST"])
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
            log_event(current_app, f"Login réussi pour projet testing: {project_name}", domain="testing")

            next_url = request.args.get("next", f"/testing/{project_name}/")
            return redirect(next_url)

        log_testing_access(project_name, "login_failed")
        log_event(current_app, f"Login échoué pour projet testing: {project_name}", level="warning", domain="testing")
        flash("Mot de passe incorrect", "error")

    return render_template(
        "testing_login.html",
        project=project,
        next=request.args.get("next", f"/testing/{project_name}/")
    )


@testing_bp.route("/<project_name>/logout")
def testing_logout(project_name: str):
    """Déconnexion d'un projet testing."""
    session.pop(f"testing_auth_{project_name}", None)
    session.pop(f"testing_name_{project_name}", None)
    log_testing_access(project_name, "logout")
    flash("Déconnecté", "success")
    return redirect(url_for("api_bp.index"))


@testing_bp.route("/<project_name>/", defaults={"path": ""})
@testing_bp.route("/<project_name>/<path:path>")
def testing_proxy(project_name: str, path: str):
    """Proxy vers le projet testing après authentification."""
    project = get_testing_project(project_name)
    if not project:
        abort(404, description="Projet non trouvé")

    # Vérifier l'authentification
    if not session.get(f"testing_auth_{project_name}"):
        return redirect(url_for("testing_bp.testing_login", project_name=project_name, next=request.url))

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
        log_event(current_app, f"Erreur connexion proxy vers {project_name}", level="error", domain="testing")
        abort(503, description="Service temporairement indisponible")
    except httpx.TimeoutException:
        log_testing_access(project_name, "proxy_error_timeout")
        log_event(current_app, f"Timeout proxy vers {project_name}", level="error", domain="testing")
        abort(504, description="Le service met trop de temps à répondre")
    except Exception as e:
        current_app.logger.error(f"Erreur proxy vers {project_name}: {e}")
        abort(500, description="Erreur interne")
