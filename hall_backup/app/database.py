"""
database.py
Fonctions liées à la base de données SQLite pour Hall - Flask Gateway.
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

from flask import request


DATABASE_PATH = os.environ.get("DATABASE_PATH", "/data/hall.db")

# Cache de l'activité
_activity_cache: Dict[str, datetime] = {}


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


def update_wol_activity(domain: str):
    """Met à jour le compteur WoL et le timestamp."""
    conn = get_db()
    conn.execute("""
        UPDATE activity SET last_wol = ?, boot_count = boot_count + 1
        WHERE domain = ?
    """, (datetime.now(), domain))
    conn.commit()
    conn.close()


# ============================================
# FONCTIONS POUR LES PROJETS TESTING
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


def get_recent_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Récupère les logs récents."""
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(log) for log in logs]


def get_all_activity() -> List[Dict[str, Any]]:
    """Récupère toutes les activités."""
    conn = get_db()
    activity = conn.execute("SELECT * FROM activity").fetchall()
    conn.close()
    return [dict(a) for a in activity]


def get_testing_access_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Récupère les logs d'accès testing récents."""
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM testing_access_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(log) for log in logs]


def create_testing_project(name: str, display_name: str, port: int, password_hash: str,
                           description: str, health_check_path: str) -> bool:
    """Crée un nouveau projet testing."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO testing_projects (name, display_name, port, password_hash, description, health_check_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, display_name, port, password_hash, description, health_check_path))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_testing_project(name: str, display_name: str, port: int, description: str,
                           health_check_path: str, active: bool, password_hash: Optional[str] = None):
    """Met à jour un projet testing."""
    conn = get_db()
    if password_hash:
        conn.execute("""
            UPDATE testing_projects 
            SET display_name = ?, port = ?, password_hash = ?, description = ?, 
                health_check_path = ?, active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (display_name, port, password_hash, description, health_check_path, 1 if active else 0, name))
    else:
        conn.execute("""
            UPDATE testing_projects 
            SET display_name = ?, port = ?, description = ?, 
                health_check_path = ?, active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (display_name, port, description, health_check_path, 1 if active else 0, name))
    conn.commit()
    conn.close()


def delete_testing_project(name: str):
    """Supprime un projet testing."""
    conn = get_db()
    conn.execute("DELETE FROM testing_projects WHERE name = ?", (name,))
    conn.commit()
    conn.close()
