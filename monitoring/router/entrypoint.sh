#!/bin/bash
set -e

echo "[router] A iniciar..."
echo "[router] IP forwarding: $(sysctl -n net.ipv4.ip_forward)"

echo "[router] Interfaces:"
ip addr show
echo "[router] Rotas:"
ip route show

# Limpeza defensiva
pkill -f snmpd 2>/dev/null || true
rm -f /var/run/snmpd.pid 2>/dev/null || true
rm -f /var/agentx/master 2>/dev/null || true
mkdir -p /var/agentx
sleep 1

echo "[router] A iniciar snmpd..."
# esta opção lê o ficheiro duas vezes:
# exec snmpd -f -Lo -c /etc/snmp/snmpd.conf 
exec snmpd -f -Lo

