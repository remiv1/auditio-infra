# 🏢 Auditio Infrastructure

Infrastructure d'orchestration multi-serveurs pour Audit IO, entreprise de conseil et développement numérique. Ce projet permet de gérer efficacement les ressources énergétiques tout en offrant une plateforme de développement et de test professionnelle pour les clients.

## 📋 Vue d'ensemble

**Audit IO** est une entreprise de conseil et développement numérique qui héberge :

- Un **ERP** pour la gestion interne de l'entreprise
- Une **plateforme de test** pour que les clients puissent tester les développements en cours (2 à 5 projets simultanés)

L'infrastructure utilise un **Raspberry Pi comme orchestrateur** (Hall) pour réveiller à la demande les serveurs de production et testing, permettant une **gestion fine et minimaliste de la consommation énergétique**.

## 🏗️ Architecture

### Infrastructure physique

| Composant | Matériel | OS | Statut | Rôle |
| --- | --- | --- | --- | --- |
| **Hall** | Raspberry Pi | Raspbian (Debian) | ✅ Fonctionnel | Orchestrateur, gateway d'entrée, gestion WoL |
| **Testing** | Serveur Linux | AlmaLinux | 🔨 En développement | Plateforme de test clients (2-5 projets) |
| **ERP** | Serveur Linux | AlmaLinux | ⏳ Prévu | Gestion entreprise Audit IO |

### Architecture logique

```md
                    ┌──────────────────────────────┐
                    │        Internet              │
                    └──────────────┬───────────────┘
                                   │
                         (80/443)  │
                                   ▼
                    ┌──────────────────────────────┐
                    │ Raspberry Pi (Hall)          │
                    │ - Traefik (reverse proxy)    │
                    │ - Flask Gateway              │
                    │ - Wake-on-LAN                │
                    │ - SQLite (logs)              │
                    │ - Toujours allumé            │
                    └──────────┬───────────────────┘
                               │
                               │ WoL + Redirection
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                              │
        ▼                                              ▼
┌───────────────────┐                      ┌───────────────────┐
│ Serveur Testing   │                      │ Serveur ERP       │
│ - Docker          │                      │ - Docker          │
│ - Projets clients │                      │ - Services métier │
│ - Réveil WoL      │                      │ - Réveil WoL      │
│ - AlmaLinux       │                      │ - AlmaLinux       │
└───────────────────┘                      └───────────────────┘
```

## 📂 Structure du projet

Le projet est organisé en trois modules principaux (gérés comme sous-modules Git) :

```md
auditio-infra/
├── hall/                           # Orchestrateur (Raspberry Pi)
│   ├── app/                        # Application Flask Gateway
│   ├── traefik/                    # Configuration Traefik
│   ├── wol-dedicated/              # API Wake-on-LAN
│   ├── config/                     # Configuration domaines
│   └── docker-compose.yml
│
├── testing/                        # Plateforme de test clients (⏳ en cours)
│   └── (à définir)
│
├── erp/                            # ERP Audit IO (⏳ prévu)
│   └── (à définir)
│
├── README.md                       # Ce fichier
├── ROADMAP.md                      # Feuille de route
├── DONE.md                         # Historique des modifications
└── SECURITY.md                     # Politiques de sécurité
```

## 🎯 Fonctionnalités principales

### Hall - Gateway d'orchestration (✅ Fonctionnel)

#### 1. **Gestion multi-domaines**

- Configuration centralisée dans `config/domains.json`
- Support de domaines multiples (`testing.audit-io.fr`, `erp.audit-io.fr`)
- Politiques de réveil configurables par domaine

#### 2. **Politiques de réveil**

- **always_on** : serveur toujours actif
- **scheduled** : allumage selon créneaux horaires et jours (fuseau configurable)
- **on_demand** : réveil sur activité ou requête, extinction après inactivité

#### 3. **Wake-on-LAN intelligent**

- API WoL dédiée dans conteneur séparé
- Réveil automatique ou manuel des serveurs
- Vérification de disponibilité (ping + health check HTTP)
- Logs détaillés par domaine

#### 4. **Page d'attente dynamique**

- Affichage professionnel pendant le démarrage du serveur
- Polling JavaScript (vérification toutes les 1-5 secondes)
- Redirection automatique quand le service est prêt
- Suivi en temps réel de l'état

#### 5. **Tableau de bord administrateur**

- Interface web d'administration (accès LAN uniquement)
- Logs détaillés par domaine
- Activité en temps réel
- Gestion des projets de testing
- Tests manuels (ping, WoL)

#### 6. **Sécurité**

- Filtrage IP par liste blanche (CIDR ou IPs individuelles)
- Authentification admin par mot de passe
- Journalisation des accès refusés
- Isolation réseau des services

#### 7. **Reverse proxy Traefik**

- Certificats SSL automatiques (Let's Encrypt)
- Renouvellement automatique
- Routage multi-domaine
- Redirection HTTP → HTTPS

### Testing - Plateforme clients (🔨 En développement)

Plateforme permettant aux clients de tester les développements en cours :

- Hébergement de 2 à 5 projets simultanés
- Isolation par conteneur Docker
- Réveil à la demande via Hall
- (Détails à compléter)

### ERP - Gestion Audit IO (⏳ Prévu)

Système de gestion interne pour Audit IO :

- Gestion des projets
- Facturation
- CRM
- (Spécifications à définir)

## 🚀 Démarrage rapide

### Prérequis

- Docker / Podman
- Git (avec support des sous-modules)
- Accès SSH aux serveurs (pour déploiement)

### Installation Hall

1. **Cloner le projet avec les sous-modules**

   ```bash
   git clone --recurse-submodules <url-du-depot>
   cd auditio-infra/hall
   ```

2. **Configurer les variables d'environnement**

   ```bash
   cp .env.exemple .env
   # Éditer .env avec vos paramètres
   ```

3. **Configurer les domaines**

   ```bash
   # Éditer config/domains.json avec vos serveurs
   ```

4. **Lancer les services**

   ```bash
   docker-compose up -d
   ```

Voir [hall/README.md](hall/README.md) pour plus de détails.

## 🔐 Gestion des secrets

### Variables d'environnement (.env)

- `ADMIN_PASSWORD` : Mot de passe admin pour le dashboard
- `SECRET_KEY` : Clé secrète Flask pour les sessions
- `WOL_API_KEY` : Clé API pour le service Wake-on-LAN

⚠️ **Ne jamais committer le fichier `.env`** (utiliser `.env.exemple` comme template)

### Certificats SSL

- Gestion automatique par Traefik + Let's Encrypt
- Stockage dans volume `traefik-acme`
- Renouvellement automatique 30 jours avant expiration
- Voir [hall/CERTIFICATES.md](hall/CERTIFICATES.md)

## 📊 Workflow de développement

1. **Développement local** : Tests sur machine de développement
2. **Validation** : Tests en grandeur réelle, vérification routes
3. **Déploiement** : Push vers serveur de production/testing

## 🛠️ Technologies utilisées

### Hall (Raspberry Pi)

- **Flask 3.1** : Application web Python
- **Traefik** : Reverse proxy, SSL/TLS
- **SQLite** : Base de données logs et activité
- **Gunicorn** : Serveur WSGI
- **Docker/Podman** : Conteneurisation

### Testing & ERP

- **Docker** : Orchestration des projets
- **AlmaLinux** : Distribution Linux serveur
- (Stack technique à définir par projet)

## 📚 Documentation

- [hall/README.md](hall/README.md) - Documentation complète Hall
- [hall/SERVICE.md](hall/SERVICE.md) - Service systemd
- [hall/CERTIFICATES.md](hall/CERTIFICATES.md) - Gestion certificats SSL
- [hall/WOL_CHECKLIST.md](hall/WOL_CHECKLIST.md) - Configuration WoL
- [ROADMAP.md](ROADMAP.md) - Feuille de route du projet
- [DONE.md](DONE.md) - Historique des modifications
- [SECURITY.md](SECURITY.md) - Politiques de sécurité

## 🎯 Avantages de l'architecture

### ✅ Économie d'énergie

- Serveurs éteints par défaut
- Réveil à la demande uniquement
- Raspberry Pi ultra-économe (toujours allumé)

### ✅ Expérience utilisateur

- Page d'attente professionnelle
- Redirection automatique transparente
- Pas de timeout ou erreur 503

### ✅ Maîtrise totale

- Logs centralisés
- Monitoring en temps réel
- Dashboard administrateur
- Gestion fine des politiques de réveil

### ✅ Scalabilité

- Ajout facile de nouveaux domaines/projets
- Configuration par fichier JSON
- Architecture modulaire (sous-modules Git)

## 📝 Statut du projet

| Module | Statut | Description |
| --- | --- | --- |
| Hall | ✅ Fonctionnel | Orchestrateur opérationnel en production |
| Testing | 🔨 En développement | Plateforme de test en cours de construction |
| ERP | ⏳ Prévu | Pas encore commencé |

## 🤝 Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines de contribution.

## 📄 Licence

Voir [LICENCE.md](LICENCE.md)

---

**Audit IO** - Conseil et développement numérique  
Architecture orchestrée, économe, et maîtrisée.

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

> 👉 **C’est ce qu’il faut pour rendre l’expérience fluide et professionnelle.**

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

```ascii-art
                ┌──────────────────────────────┐
                │        Internet              │
                └──────────────┬───────────────┘
                               │
                     (80/443)  │
                               ▼
                ┌──────────────────────────────┐
                │ Traefik #1 (Raspberry Pi)    │
                └──────────────┬───────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │     Flask Gateway            │
                │  - logs                      │
                │  - WoL                       │
                │  - page d’attente            │
                └──────────────┬───────────────┘
                               │ redirection
                               ▼
                ┌───────────────────────────────┐
                │ Traefik #2 (Serveur principal)│
                └──────────────┬────────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │   Conteneurs client1,2,3…    │
                └──────────────────────────────┘
```

---

## ✔️ 3. On évite les timeouts de Traefik

Traefik n’a pas besoin d’attendre 30 secondes que le serveur démarre.
C’est Flask qui gère l’attente, avec un polling JS.

---

## ✔️ 4. Tableau de bord admin très utile

Avec SQLite, on peux suivre :

- nombre de réveils
- temps moyen de boot
- projets les plus consultés
- erreurs éventuelles
- état du serveur (ping, charge, conteneurs)

Et comme on le limite au LAN, on reste simple et sécurisé.

---

### ⚠️ 1. Le Flask doit être découplé de Traefik

On dois s’assurer que :

- Flask ne passe pas par Traefik pour réveiller le serveur
- Flask peut accéder directement au LAN
- Flask peut interroger Docker sur le serveur (via API ou SSH)

---

### ⚠️ 2. Le serveur doit exposer une API minimale

Pour vérifier :

- “Docker est lancé ?”
- “Le conteneur X existe ?”
- “Le conteneur X est healthy ?”

On peux faire ça via :

- une petite API Python/Go sur le serveur
- ou un accès SSH automatisé
- ou l’API Docker Remote (mais sécurisée)

---

### ⚠️ 3. SQLite doit être protégé

Même si c’est du test, protège :

- les fichiers SQLite
- l’accès admin
- les logs sensibles

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
On crée un orchestrateur léger, souverain, économe en énergie, et parfaitement adapté au besoin de tests multi‑clients.

> **Flask comme gateway + JS pour le polling + SQLite pour les logs + Traefik pour le routage + WoL pour le serveur dormant = architecture élégante, robuste et maîtrisée.**
> *construire une mini‑plateforme d’hébergement intelligente, à la fois low‑tech et high‑efficiency.*
