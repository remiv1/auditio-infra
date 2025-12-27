# Configuration des certificats TLS

## Domaines configurés

- **testing.audit-io.fr** - Serveur de test client
- **erp.audit-io.fr** - ERP entreprise

## Configuration actuelle

### Let's Encrypt
- **Email de contact** : rverschuur@audit-io.fr
- **Challenge** : HTTP (httpChallenge sur le port 80)
- **Stockage** : `/etc/traefik/acme/acme.json` (dans le volume `traefik-acme`)
- **Renouvellement** : Automatique par Traefik (vérification toutes les 24h)

### Redirections
- Tout le trafic HTTP (port 80) est automatiquement redirigé vers HTTPS (port 443)

## Prérequis pour l'obtention des certificats

Pour que Let's Encrypt puisse générer les certificats, les conditions suivantes doivent être remplies :

1. **DNS configuré** : Les domaines `testing.audit-io.fr` et `erp.audit-io.fr` doivent pointer vers l'adresse IP publique de ce serveur (enregistrement A ou AAAA)

2. **Port 80 accessible** : Let's Encrypt doit pouvoir accéder au port 80 depuis Internet pour le challenge HTTP

3. **Pare-feu ouvert** : UFW autorise déjà les ports 80 et 443

## Vérification

### Vérifier la configuration DNS
```bash
dig testing.audit-io.fr A
dig erp.audit-io.fr A
```

### Vérifier les logs Traefik
```bash
sudo podman logs hall-traefik
```

### Vérifier les certificats obtenus
```bash
sudo cat /home/audit-io/projects/auditio-infra/hall/traefik/acme/acme.json
```

## Processus de renouvellement

Traefik vérifie automatiquement l'expiration des certificats toutes les 24 heures et les renouvelle 30 jours avant expiration. Aucune intervention manuelle n'est requise.

## Première obtention des certificats

Dès que les domaines seront accessibles depuis Internet, Traefik tentera automatiquement d'obtenir les certificats lors de la première requête HTTPS sur chaque domaine.

## Dépannage

### Les certificats ne sont pas générés
1. Vérifier que les domaines pointent bien vers ce serveur
2. Vérifier que le port 80 est accessible depuis Internet (pas de NAT ou firewall qui bloque)
3. Consulter les logs : `sudo podman logs hall-traefik | grep -i acme`

### Tester manuellement l'accessibilité
```bash
curl -I http://testing.audit-io.fr/.well-known/acme-challenge/test
```

Si cette URL ne répond pas, Let's Encrypt ne pourra pas valider le domaine.
