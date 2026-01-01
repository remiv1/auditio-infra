# Checklist Wake-on-LAN (WoL) – Diagnostic complet

## 1. Configuration matérielle du serveur
- [X] **Vérifier que le WoL est activé dans le BIOS/UEFI**
  - Option souvent appelée "Wake on LAN", "Power On By PCI-E", "Resume by LAN", etc.
- [X] **La carte réseau doit supporter le WoL**
  - Vérifier la documentation de la carte mère et de la carte réseau.
- [X] **La carte réseau doit rester alimentée lorsque le serveur est éteint**
  - Un voyant lumineux sur le port Ethernet doit rester allumé après extinction.
- [X] **Connexion Ethernet obligatoire**
  - Le WoL ne fonctionne pas en Wi-Fi.
- [X] **Adresse MAC utilisée**
  - S’assurer que l’adresse MAC est celle de la carte réseau connectée au réseau local.

## 2. Configuration logicielle du serveur
- [X] **Activer le WoL dans l’OS (Linux)**
  - Vérifier avec `ethtool eth0` (remplacer eth0 par l’interface réelle)
  - Le paramètre `Wake-on: g` doit être présent
  - Pour activer : `sudo ethtool -s eth0 wol g`
- [X] **Désactiver l’hibernation profonde (S5/S4)**
  - Certains modes d’extinction coupent l’alimentation de la carte réseau.

## 3. Configuration réseau
- **Le paquet WoL doit être un broadcast UDP sur le port 9 (par défaut)**
  - Vérifier que le réseau local autorise les broadcasts.
- **Switchs et routeurs**
  - Les switches doivent transmettre les paquets broadcast (certains modèles les filtrent).
  - Les routeurs ne doivent pas bloquer le port UDP 9.
  - Si le serveur est sur un VLAN, vérifier que le broadcast traverse le VLAN.
- **Pas de filtrage MAC ou IP sur le chemin**
  - Les ACL ou filtrages peuvent bloquer le paquet WoL.

## 4. Tests et vérifications
- **Test depuis l’hôte local**
  - Utiliser la commande `wakeonlan <MAC>`
- **Test depuis un autre PC du réseau**
  - Permet de vérifier la propagation du paquet WoL.
- **Sniffer le réseau**
  - Utiliser `tcpdump` ou `wireshark` pour vérifier que le paquet WoL arrive bien sur le serveur.

## 5. Points avancés
- **Mode d’extinction du serveur**
  - Privilégier l’arrêt "normal" plutôt que l’hibernation ou la veille prolongée.
- **Firmware et drivers**
  - Mettre à jour le BIOS/UEFI et les pilotes de la carte réseau.
- **Wake-on-LAN sur VLAN**
  - Certains VLAN ne propagent pas les broadcasts, il peut être nécessaire d’adapter la config.

---

**En cas d’échec, vérifier chaque étape de cette checklist.**

