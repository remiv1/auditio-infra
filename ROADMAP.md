# 🗺️ Roadmap du projet d’orchestration

## 1. Hall d'entrée (Raspberry Pi)

- Mettre en place et configurer Traefik (ports 80/443)
- Développer et déployer le mini-site Flask Gateway
  - Réception des requêtes initiales
  - Identification du projet demandé
  - Déclenchement du WoL (Wake-on-LAN)
  - Page d’attente dynamique avec polling JS
  - Redirection automatique une fois prêt
  - Enregistrement des logs dans SQLite
  - Tableau de bord admin (accès LAN uniquement)
- Sécuriser l’accès à SQLite et à l’admin
- Ajouter un monitoring léger (Netdata ou Prometheus Node Exporter)
- S’assurer que Flask peut accéder au LAN et interroger le serveur principal sans passer par Traefik

---

## 2. Serveur principal (A venir)

- Installer et configurer Docker Engine
- Préparer des Docker Compose par projet
- Développer ou déployer une API de statut minimale (Python/Go ou SSH automatisé)
  - Vérification : Docker lancé ? Conteneur X présent ? Conteneur healthy ?
- Sécuriser l’accès à l’API (authentification, réseau)
- Optimiser le temps de boot et la consommation énergétique
- Prévoir l’ajout de nouveaux projets/clients facilement

---

## 3. Développement orienté utilisateur

- Créer une page d’attente propre et professionnelle
- Mettre en place le polling JS (toutes les 1–5 secondes, raisonnable)
- Afficher un suivi en temps réel de l’état du serveur et des conteneurs
- Gérer la redirection automatique dès que le service est prêt
- Concevoir un tableau de bord admin pour le suivi (nombre de réveils, temps de boot, erreurs, etc.)
- Protéger les accès sensibles (logs, admin, données)
- Prévoir l’intégration de nouveaux projets/clients via l’interface
