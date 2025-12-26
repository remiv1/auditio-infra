#!/bin/bash

# Script de gestion du service Hall Audit IO
# Usage: ./hall-service.sh [start|stop|restart|status|logs]

SERVICE_NAME="hall-auditio.service"

case "$1" in
    start)
        echo "🚀 Démarrage du service Hall..."
        sudo systemctl start $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager -l
        ;;
    stop)
        echo "⏹️  Arrêt du service Hall..."
        sudo systemctl stop $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager -l
        ;;
    restart)
        echo "🔄 Redémarrage du service Hall..."
        sudo systemctl restart $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME --no-pager -l
        ;;
    status)
        echo "📊 Statut du service Hall:"
        sudo systemctl status $SERVICE_NAME --no-pager -l
        echo -e "\n📦 Conteneurs en cours d'exécution:"
        podman ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"
        ;;
    logs)
        echo "📋 Logs du service Hall:"
        sudo journalctl -u $SERVICE_NAME --no-pager -l -n 50
        ;;
    enable)
        echo "✅ Activation du démarrage automatique..."
        sudo systemctl enable $SERVICE_NAME
        ;;
    disable)
        echo "❌ Désactivation du démarrage automatique..."
        sudo systemctl disable $SERVICE_NAME
        ;;
    *)
        echo "🛠️  Script de gestion du service Hall Audit IO"
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "Commandes disponibles:"
        echo "  start    - Démarre le service"
        echo "  stop     - Arrête le service"
        echo "  restart  - Redémarre le service"
        echo "  status   - Affiche le statut du service et des conteneurs"
        echo "  logs     - Affiche les logs du service"
        echo "  enable   - Active le démarrage automatique"
        echo "  disable  - Désactive le démarrage automatique"
        exit 1
        ;;
esac