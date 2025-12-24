
# DONE.md

## Travaux réalisés (synthèse)

### 1. Mise en place d'une passerelle Flask pour le réveil à la demande

- Développement d'une application Flask jouant le rôle de point d'entrée unique pour tous les domaines.
- Gestion multi-domaines avec configuration dynamique (JSON).
- Orchestration du réveil des serveurs via Wake-on-LAN.
- Page d'attente dynamique avec polling JS et redirection automatique.

### 2. Sécurité et contrôle d'accès

- Filtrage IP configurable par domaine (listes blanches, CIDR).
- Décorateur d'accès pour protéger toutes les routes critiques.
- Journalisation des accès et des refus dans une base SQLite.

### 3. Gestion de l'activité et des politiques de disponibilité

- Suivi de l'activité par domaine (cache mémoire + base SQLite).
- Politiques de disponibilité : always_on, scheduled (créneaux horaires), on_demand (veille après inactivité).
- Prise en compte des fuseaux horaires et des jours ouvrés.

### 4. Monitoring et supervision

- Vérification de l'état des serveurs par ping et health check HTTP.
- Tableau de bord d'administration (logs, activité, statut des domaines).

### 5. Conteneurisation et automatisation

- Dockerisation complète (Dockerfile, docker-compose).
- Initialisation automatique de la base de données au démarrage.

### 6. Bonnes pratiques et maintenabilité

- Typage explicite de toutes les fonctions (Python typing).
- Documentation technique et fonctionnelle à jour.
- Séparation claire des responsabilités (config, sécurité, monitoring, interface).

---

Pour toute évolution majeure, ajouter une section synthétique ici (pas le détail technique, mais la finalité et la portée du travail).
