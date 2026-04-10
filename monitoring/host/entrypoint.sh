#!/bin/bash
set -e

# GW: gateway (router) para a outra sub-rede
# SERVER: IP do iperf-server (só usado pelo cliente)
# ROLE: "server" ou "client"

echo "[host:${ROLE}] A iniciar..."

# Adicionar rota para a outra sub-rede via router
if [ -n "$GW" ]; then
    # Rota para toda a rede via gateway
    ip route add 10.10.0.0/16 via "$GW" 2>/dev/null || true
    echo "[host:${ROLE}] Rota adicionada via $GW"
fi

if [ "$ROLE" = "server" ]; then
    echo "[host:server] A iniciar iperf3 em modo servidor..."
    exec iperf3 --server --bind 0.0.0.0 --port 5201

elif [ "$ROLE" = "client" ]; then
    echo "[host:client] A aguardar que o servidor fique disponível..."
    # Esperar que o iperf-server esteja pronto
    until nc -z "${SERVER}" 5201 2>/dev/null; do
        sleep 2
    done
    echo "[host:client] Servidor disponível. A iniciar tráfego iperf3 contínuo..."

    # Loop de tráfego: iperf3 em ciclos de 20s com 20s de pausa
    # Usa TCP por defeito — gera tráfego visível nos contadores ifInOctets/ifOutOctets
    while true; do
        echo "[host:client] --- Novo ciclo iperf3 ---"
        iperf3 \
            --client "${SERVER}" \
            --port 5201 \
            --time 20 \
            --bandwidth 10M \
            --parallel 2 \
            --interval 5 \
            || true
        echo "[host:client] Pausa de 20s..."
        sleep 20
    done

else
    echo "[host] ROLE não definida. A manter container activo."
    tail -f /dev/null
fi
