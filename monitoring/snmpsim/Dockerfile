FROM python:3.11-slim

LABEL description="SNMP Simulator com CLASSROOM-MIB para demo de observabilidade"

# Instalar snmpsim-lextudio (fork mantido de snmpsim)
RUN pip install --no-cache-dir snmpsim-lextudio

# Dados de simulação (.snmprec) — o nome do ficheiro define a community string
COPY data/ /data/

EXPOSE 161/udp

# Inicia o simulador a escutar em todas as interfaces na porta 161
# Community string deriva do nome do ficheiro: classroom-manual
#
# --process-user/group: snmpsim arranca como root para abrir a porta 161
# (porta privilegiada) e depois faz drop de privilégios para nobody/nogroup
CMD ["snmpsim-command-responder", \
     "--data-dir=/data", \
     "--agent-udpv4-endpoint=0.0.0.0:161", \
     "--process-user=nobody", \
     "--process-group=nogroup", \
     "--log-level=info"]
