"""
admin_bp.py
Blueprint pour les routes d'administration de Hall - Flask Gateway.
"""

import os

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session
)
from werkzeug.security import generate_password_hash

from config import load_config, TESTING_SERVER_IP
from database import (
    get_db, get_recent_logs, get_all_activity, get_all_testing_projects,
    get_testing_access_logs, get_testing_project, create_testing_project,
    update_testing_project, delete_testing_project
)
from functions import require_admin_login
from wol import ping_server


admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')


@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    """Page de login admin."""
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        flash("Aucun mot de passe admin n'est défini. Veuillez définir la variable d'environnement ADMIN_PASSWORD.", "error")
    if request.method == "POST":
        password = request.form.get("password", "")
        if admin_password and password == admin_password:
            session["admin_authenticated"] = True
            next_url = request.args.get("next") or url_for("admin_bp.admin")
            return redirect(next_url)
        flash("Mot de passe incorrect", "error")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def admin_logout():
    """Déconnexion admin."""
    session.pop("admin_authenticated", None)
    flash("Déconnecté", "info")
    return redirect(url_for("admin_bp.admin_login"))


@admin_bp.route("")
@require_admin_login
def admin():
    """Tableau de bord admin (LAN only)."""
    config = load_config()
    domains_config = config.get("domains", {})

    logs = get_recent_logs(100)
    activity = get_all_activity()

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
# GESTION DES PROJETS TESTING (ADMIN)
# ============================================

@admin_bp.route("/testing")
@require_admin_login
def admin_testing():
    """Page d'administration des projets testing."""
    projects = get_all_testing_projects()
    logs = get_testing_access_logs(50)

    return render_template(
        "admin_testing.html",
        projects=projects,
        logs=logs,
        testing_server_ip=TESTING_SERVER_IP
    )


@admin_bp.route("/testing/add", methods=["GET", "POST"])
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
            return redirect(url_for("admin_bp.admin_testing_add"))

        if not name.isalnum():
            flash("Le nom doit contenir uniquement des lettres et chiffres", "error")
            return redirect(url_for("admin_bp.admin_testing_add"))

        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                raise ValueError()
        except ValueError:
            flash("Le port doit être un nombre entre 1 et 65535", "error")
            return redirect(url_for("admin_bp.admin_testing_add"))

        # Vérifier que le nom n'existe pas
        if get_testing_project(name):
            flash("Un projet avec ce nom existe déjà", "error")
            return redirect(url_for("admin_bp.admin_testing_add"))

        # Créer le projet
        password_hash = generate_password_hash(password)
        if create_testing_project(name, display_name, port_int, password_hash, description, health_check_path):
            flash(f"Projet '{display_name}' créé avec succès", "success")
        else:
            flash("Erreur lors de la création du projet", "error")

        return redirect(url_for("admin_bp.admin_testing"))

    return render_template("admin_testing_form.html", project=None)


@admin_bp.route("/testing/edit/<name>", methods=["GET", "POST"])
@require_admin_login
def admin_testing_edit(name: str):
    """Modifier un projet testing."""
    project = get_testing_project(name)
    if not project:
        flash("Projet non trouvé", "error")
        return redirect(url_for("admin_bp.admin_testing"))

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
            return redirect(url_for("admin_bp.admin_testing_edit", name=name))

        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                raise ValueError()
        except ValueError:
            flash("Le port doit être un nombre entre 1 et 65535", "error")
            return redirect(url_for("admin_bp.admin_testing_edit", name=name))

        password_hash = generate_password_hash(password) if password else None
        update_testing_project(name, display_name, port_int, description, health_check_path, active, password_hash)

        flash(f"Projet '{display_name}' mis à jour", "success")
        return redirect(url_for("admin_bp.admin_testing"))

    return render_template("admin_testing_form.html", project=project)


@admin_bp.route("/testing/delete/<name>", methods=["POST"])
@require_admin_login
def admin_testing_delete(name: str):
    """Supprimer un projet testing."""
    delete_testing_project(name)
    flash(f"Projet '{name}' supprimé", "success")
    return redirect(url_for("admin_bp.admin_testing"))
