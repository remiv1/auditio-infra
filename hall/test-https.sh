#!/bin/bash
# Script de test des domaines HTTPS

echo "=== Test de connectivité HTTPS ==="
echo ""

IPV6="2a01:cb10:8243:5700:b89:eaef:d828:51f9"

echo "1. IPv6 actuelle:"
ip -6 addr show dev end0 | grep "inet6.*global"
echo ""

echo "2. Résolution DNS (Google DNS 8.8.8.8):"
dig @8.8.8.8 testing.audit-io.fr AAAA +short
dig @8.8.8.8 erp.audit-io.fr AAAA +short
echo ""

echo "3. Test HTTPS testing.audit-io.fr:"
curl -I https://testing.audit-io.fr --resolve testing.audit-io.fr:443:$IPV6 2>&1 | head -5
echo ""

echo "4. Test HTTPS erp.audit-io.fr:"
curl -I https://erp.audit-io.fr --resolve erp.audit-io.fr:443:$IPV6 2>&1 | head -5
echo ""

echo "5. Vérification du certificat SSL:"
echo | openssl s_client -connect [$IPV6]:443 -servername testing.audit-io.fr 2>&1 | grep -E "subject=|issuer=|Verify return" | head -3
echo ""

echo "=== Tests terminés ==="
