# Service systemd Hall Audit IO

Le service `hall-auditio.service` démarre automatiquement le déploiement Podman Compose au boot du système.

## Configuration

- **Service** : `/etc/systemd/system/hall-auditio.service`
- **Répertoire de travail** : `/home/audit-io/projects/auditio-infra/hall`
- **Utilisateur** : `audit-io`
- **Démarrage automatique** : ✅ Activé

## Gestion du service

### Via systemctl (commandes manuelles)
```bash
# Démarrer le service
sudo systemctl start hall-auditio.service

# Arrêter le service
sudo systemctl stop hall-auditio.service

# Redémarrer le service
sudo systemctl restart hall-auditio.service

# Statut du service
sudo systemctl status hall-auditio.service

# Logs du service
sudo journalctl -u hall-auditio.service -f
```

### Via le script de gestion (recommandé)
```bash
# Toutes les opérations
./hall-service.sh {start|stop|restart|status|logs|enable|disable}

# Exemples
./hall-service.sh status    # Statut complet (service + conteneurs)
./hall-service.sh restart   # Redémarrage
./hall-service.sh logs      # Affichage des logs
```

## Vérification du bon fonctionnement

Après le démarrage du service :

1. **Vérifier les conteneurs**
   ```bash
   podman ps
   ```

2. **Tester l'application**
   ```bash
   curl http://localhost
   ```

3. **Vérifier le dashboard Traefik**
   ```bash
   curl http://localhost:8080/dashboard/
   ```

## Ports exposés

- **80** : Application web (HTTP)
- **443** : Application web (HTTPS)  
- **8080** : Dashboard Traefik

## Démarrage automatique

Le service est configuré pour démarrer automatiquement au boot du système grâce à :
- `WantedBy=multi-user.target`
- `sudo systemctl enable hall-auditio.service`

## Dépannage

### Si le service ne démarre pas
1. Vérifier les logs : `sudo journalctl -u hall-auditio.service`
2. Vérifier les permissions du répertoire de travail
3. S'assurer que podman-compose est installé
4. Vérifier que l'utilisateur `audit-io` peut exécuter podman

### Si les conteneurs ne sont pas accessibles
1. Vérifier la configuration réseau de podman
2. Contrôler les fichiers de configuration Traefik
3. Vérifier les permissions des fichiers de configuration