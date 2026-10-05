# Sécurité

[Accueil](README.md) · [Déploiement](hall/DEPLOYMENT.md) · [Configuration](hall/documentation/CONFIGURATION.md)

## Périmètre maintenu

L'architecture actuelle de Hall utilise Caddy, Flask et un catalogue TOML. Les anciennes routes d'administration, le routage par cookie, Traefik et l'API Testing retirée ne sont plus des composants maintenus ici.

L'accès aux projets est public. Si un projet contient des données privées, son application doit fournir ses propres contrôles d'accès ; Hall ne constitue pas une authentification pour nginx ou les projets.

## Frontières de confiance

| Surface | Mesure attendue |
| :--- | :--- |
| Internet | Publier seulement les ports Caddy nécessaires |
| Flask | Pas de port 5000 publié sur l'hôte |
| Administration Caddy | Socket Unix partagé seulement avec Flask |
| WoL SSH | Compte et clé limités à la commande de réveil, clé d'hôte vérifiée |
| DNS OVH | Droits limités à la zone et aux opérations utiles |
| SMTP | TLS obligatoire, identifiants hors Git |
| Projets distants | Contrôles d'accès propres aux applications et pare-feu LAN |

Flask contrôle la configuration Caddy : toute compromission de ce conteneur menace le routage. Limiter l'accès aux montages, au socket et aux fichiers de configuration. Ne pas multiplier les consommateurs de ce socket.

## Secrets et sauvegardes

- Ne pas versionner `.env`, `.env.acme`, les clés privées ou le stockage ACME.
- Protéger aussi les sauvegardes de ces fichiers et des volumes Caddy.
- Ne pas désactiver les vérifications TLS ou SSH pour contourner un incident.
- Faire tourner tout secret publié accidentellement : une suppression dans Git n'efface pas l'historique.
- Vérifier les journaux avant de les partager ; limiter leur conservation selon les besoins.

## Signaler une vulnérabilité

> [!IMPORTANT]
> Ne pas ouvrir d'issue publique contenant une vulnérabilité ou des secrets.

Contacter [rverschuur@audit-io.fr](mailto:rverschuur@audit-io.fr) avec le composant, la révision, le scénario de reproduction et l'impact estimé. Ne pas joindre de mots de passe ni de clés privées.

Un accusé de réception est prévu sous trois jours ouvrés. La correction et une éventuelle publication seront coordonnées avec le signalement ; le crédit sera proposé au découvreur.
