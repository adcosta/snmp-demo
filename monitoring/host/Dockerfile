FROM ubuntu:22.04

LABEL description="Host iperf3 — cliente ou servidor, controlado por variável ROLE"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        iperf3 \
        iproute2 \
        iputils-ping \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
