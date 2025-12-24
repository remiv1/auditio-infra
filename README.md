# Orchestration d'un site de test

## Présentation

Hall est une passerelle Flask permettant d'orchestrer le réveil à la demande de serveurs, avec gestion multi-domaines et politiques configurables (always_on, scheduled, on_demand). L'application gère la sécurité par filtrage IP, le suivi d'activité, et propose une interface d'administration.

## Structure du projet

- hall/app/app.py : application principale Flask
- hall/app/requirements.txt : dépendances Python
- hall/app/static/ : fichiers statiques (CSS, JS)
- hall/app/templates/ : templates HTML (Jinja2)
- hall/config/ : configuration des domaines (JSON)
- hall/docker-compose.yml, Dockerfile.* : conteneurisation

## Fonctionnalités principales (Hall - Gateaway)

### 1. Chargement et cache de configuration

- Lecture de la configuration JSON (domains.json)
- Cache mémoire (_config_cache, _config_mtime) pour éviter les relectures inutiles
- Reload dynamique via /api/reload

### 2. Gestion des politiques de réveil

- always_on : serveur toujours allumé
- scheduled : allumage selon créneaux horaires et jours, avec fuseau configurable
- on_demand : réveil sur activité ou requête, extinction après inactivité
- Prise en compte de l'activité récente (base SQLite et cache mémoire)

### 3. Sécurité et accès

- Décorateur @require_domain_access : vérifie la configuration du domaine et l'autorisation IP
- Filtrage IP par liste blanche (CIDR ou IPs individuelles)
- Journalisation des accès refusés

### 4. Réseau et monitoring

- Wake-on-LAN (WoL) via subprocess (wakeonlan)
- Ping pour vérifier la disponibilité du serveur
- Health check HTTP optionnel pour valider la disponibilité applicative

### 5. API et interface

- /< domain > : page d'attente pour chaque domaine
- /api/status/< domain > : statut du serveur et de l'application
- /api/wake/< domain > : réveil du serveur (POST)
- /api/activity/< domain > : signalement d'activité (POST)
- /api/config : configuration (admin, masquée)
- /admin/... : tableau de bord (logs, activité, statuts)

### 6. Base de données

- SQLite pour journaliser les logs et l'activité par domaine
- Initialisation automatique au démarrage

## Typage et bonnes pratiques

- Typage explicite de toutes les fonctions (Dict, Optional, Callable, TypeVar...)
- Utilisation de global uniquement pour le cache mémoire
- Décorateurs typés pour compatibilité avec les outils de type
- Docstrings systématiques

## Sécurité

- TODO : Vérification d'accès admin sur /api/config et /api/reload
- TODO : Restriction d'accès LAN sur /admin

## Historique des modifications

Voir [DONE.md](./DONE.md) pour le suivi détaillé des évolutions et refactorings.

---

Idée d'architecture “serveur dormant + réveil à la demande.

**Orchestrateur léger**, un “boot manager” qui joue le rôle de tampon entre l’utilisateur et l’infrastructure.Simplicité : Flask + JS + SQLite + Traefik.

---

## 🧠 **Mini‑site Flask comme orchestrateur** (Hall)

- Un **docker‑compose de base** (toujours actif sur le Raspberry Pi)
- Un **mini‑site Flask** qui :
  - reçoit la requête initiale de l’utilisateur
  - identifie le projet demandé
  - déclenche le réveil du serveur (WoL)
  - surveille l’état du serveur et des conteneurs
  - affiche une page d’attente dynamique
  - redirige automatiquement quand tout est prêt
  - enregistre des logs dans SQLite
  - propose un tableau de bord admin (LAN only)

👉 **C’est ce qu’il faut pour rendre l’expérience fluide et professionnelle.**

---

## 🟢 **Excellence de l'approche**

### ✔️ 1. Pas de complexité pour l’utilisateur

Au lieu d’un “site indisponible”, on propose :

- une page d’attente propre
- un suivi en temps réel
- une redirection automatique

C’est professionnel.

---

### ✔️ 2. Maîtrise totale du flux de requêtes

Le Flask “gateway” devient :

- le point d’entrée unique
- le gestionnaire d’état
- le coordinateur du réveil
- le proxy logique avant Traefik

On peux même y ajouter des règles d’accès, des quotas, des logs, etc.

#### Schéma simplifié

                ┌──────────────────────────────┐
                │        Internet              │
                └──────────────┬──────────────┘
                               │
                     (80/443)  │
                               ▼
                ┌──────────────────────────────┐
                │ Traefik #1 (Raspberry Pi)    │
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │     Flask Gateway            │
                │  - logs                      │
                │  - WoL                       │
                │  - page d’attente            │
                └──────────────┬──────────────┘
                               │ redirection
                               ▼
                ┌──────────────────────────────┐
                │ Traefik #2 (Serveur principal)│
                └──────────────┬──────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │   Conteneurs client1,2,3…    │
                └──────────────────────────────┘

---

## ✔️ 3. On évite les timeouts de Traefik

Traefik n’a pas besoin d’attendre 30 secondes que le serveur démarre.
C’est Flask qui gère l’attente, avec un polling JS.

---

## ✔️ 4. On peut faire un tableau de bord admin très utile

Avec SQLite, on peux suivre :

- nombre de réveils
- temps moyen de boot
- projets les plus consultés
- erreurs éventuelles
- état du serveur (ping, charge, conteneurs)

Et comme on le limite au LAN, on reste simple et sécurisé.

---

## 🟡 **Les points à surveiller**

### ⚠️ 1. Le polling JS doit être raisonnable

Évite un ping toutes les 200 ms, toutes les 1 à 5s, c'est suffisant.

---

### ⚠️ 2. Le Flask doit être découplé de Traefik

On dois s’assurer que :

- Flask ne passe pas par Traefik pour réveiller le serveur
- Flask peut accéder directement au LAN
- Flask peut interroger Docker sur le serveur (via API ou SSH)

---

### ⚠️ 3. Le serveur doit exposer une API minimale

Pour vérifier :

- “Docker est lancé ?”
- “Le conteneur X existe ?”
- “Le conteneur X est healthy ?”

On peux faire ça via :

- une petite API Python/Go sur le serveur
- ou un accès SSH automatisé
- ou l’API Docker Remote (mais sécurisée)

---

### ⚠️ 4. SQLite doit être protégé

Même si c’est du test, protège :

- les fichiers SQLite
- l’accès admin
- les logs sensibles

---

## 🧩 **Architecture logique complète**

### 🟦 Raspberry Pi (toujours allumé)

- Traefik (ports 80/443)
- Flask Gateway (port interne)
- SQLite (logs)
- Script WoL
- Monitoring léger (Netdata ou Prometheus Node Exporter)

### 🟥 Serveur principal (dormant)

- Docker Engine
- Docker Compose par projet
- API de statut (ou SSH)
- Conteneurs des projets

---

## 🚦 **Workflow complet d’une requête**

1. L’utilisateur visite [site de base](https://testing.audit-io.fr/client1)
2. Traefik route vers Flask (car le serveur est off)
3. Flask
   - identifie le projet demandé
   - vérifie si le serveur est en ligne
   - si non → envoie WoL
   - affiche une page d’attente
4. JS dans la page :
   - ping Flask toutes les 1–5 secondes
   - Flask vérifie :
     - serveur en ligne ?
     - Docker lancé ?
     - conteneur présent ?
     - conteneur healthy ?
5. Quand tout est OK :
   - Flask renvoie “ready: true”
   - JS redirige vers le site réel
6. Traefik route vers le conteneur du projet

---

## 🧭 **Conclusion**

L'idée est **bien pensée**.
On crée un orchestrateur léger, souverain, économe en énergie, et parfaitement adapté à ton besoin de tests multi‑clients.

> **Flask comme gateway + JS pour le polling + SQLite pour les logs + Traefik pour le routage + WoL pour le serveur dormant = architecture élégante, robuste et maîtrisée.**
> *construire une mini‑plateforme d’hébergement intelligente, à la fois low‑tech et high‑efficiency.*
