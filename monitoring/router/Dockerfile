FROM ubuntu:22.04

LABEL description="Router com net-snmp (snmpd) e iperf3 para demo de monitorização"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        snmpd \
        snmp \
        iperf3 \
        iproute2 \
        iputils-ping \
        tcpdump \
        net-tools \
        procps \
    && rm -rf /var/lib/apt/lists/* 

COPY snmpd.conf /etc/snmp/snmpd.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 161/udp

ENTRYPOINT ["/entrypoint.sh"]
CMD []

