# Contribution

[Accueil](README.md) · [Hall](hall/README.md) · [Sécurité](SECURITY.md)

## Deux dépôts, deux responsabilités

Le dépôt parent contient la documentation d'infrastructure. `hall` est un sous-module avec son propre historique : les changements de l'application se font dans ce dépôt, puis le parent peut référencer sa nouvelle révision.

```bash
git submodule update --init hall
git status --short
git -C hall status --short
```

Ne pas faire de mise à jour de sous-module qui écrase des changements locaux. Les fichiers non suivis de configuration et les clés SSH doivent rester locaux.

## Environnement de développement

Depuis `hall`, utiliser Python 3.11 ou supérieur ; le conteneur de production utilise Python 3.14.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests -q
docker compose config --quiet
bash -n entrypoint.sh hall-service.sh test-https.sh utilitaires/wol_persistant.sh
```

Les tests existants couvrent le catalogue, le rechargement Caddy, les routes publiques, le réveil et les alertes. Par défaut, réutiliser leurs simulations plutôt qu'appeler le LAN ou le relais SMTP. Le [test SMTP réel](hall/README.md#vérifier-le-relais-smtp-réel) est ignoré sans son option d'autorisation explicite.

## Conventions

| Sujet | Attendu |
| :--- | :--- |
| Python | Annotations de types, noms explicites, fonctions ciblées |
| Docstrings publiques | Français, format Google |
| Commentaires et commits | Français, justification utile plutôt que narration |
| Tests | pytest, comportement métier et cas limites clairement définis |
| Documentation | Liens relatifs, exemples sans secrets, diagrammes Mermaid |

## Proposer un changement

1. Décrire le problème, le comportement attendu et le périmètre.
2. Modifier le composant concerné, sans nettoyage sans rapport.
3. Exécuter les contrôles ciblés et mettre à jour la documentation.
4. Présenter les validations, limites et impacts opérationnels dans la pull request.
5. Publier la révision Hall avant de proposer sa référence dans le dépôt parent.

> [!WARNING]
> Construire ou recréer les conteneurs de production, modifier systemd, réveiller le serveur ou envoyer un courriel réel demande une intervention prévue. Les tests locaux ne doivent pas effectuer ces actions.

Ne jamais ajouter `.env`, `.env.acme`, une clé privée ou un stockage de certificats à Git. Pour une vulnérabilité, suivre [SECURITY.md](SECURITY.md) plutôt qu'ouvrir une issue publique. Les échanges suivent le [code de conduite](CODE_OF_CONDUCT.md).
