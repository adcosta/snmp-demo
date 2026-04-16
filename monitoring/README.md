# SNMP Monitoring Lab

Demonstração de uma stack de observabilidade completa baseada em SNMP, com dois cenários independentes que partilham a mesma pipeline de recolha e visualização.

---

## Visão Geral

### Cenário 1 — Router com tráfego iperf

Um router Linux com duas interfaces encaminha tráfego gerado pelo iperf entre dois hosts. O agente SNMP do router (net-snmp, SNMPv3) expõe métricas IF-MIB e IP-MIB que o Telegraf recolhe a cada 10 segundos.

```
+--------------+   leftnet          +----------------+   rightnet   +--------------+
| iperf-client |----10.10.1.0/24----|     router     |--10.10.2.0/24-| iperf-server |
| 10.10.1.10   |                    | 10.10.1.254    |               | 10.10.2.10   |
+--------------+                    | 10.10.2.254    |               +--------------+
                                    | snmpd (SNMPv3) |
                                    +-------^--------+
                                            |  SNMPv3 (UDP/161)
                                    +-------+--------+
                                    |    Telegraf    |  ←── também em classnet
                                    +-------+--------+
                                            |
                                    +-------v--------+
                                    |    InfluxDB    |
                                    +-------^--------+
                                            |
                                    +-------+--------+
                                    |    Grafana     |
                                    |  :3000         |
                                    +----------------+
```

### Cenário 2 — Simulador SNMP com CLASSROOM-MIB

Um agente SNMP simulado (snmpsim) serve dados estáticos da CLASSROOM-MIB: salas, alunos e presenças em aula. O Telegraf recolhe estes dados via SNMPv2c e envia para o mesmo InfluxDB.

```
                                    +----------------+
                                    |    snmpsim     |
                                    | CLASSROOM-MIB  |
                                    | SNMPv2c :161   |
                                    +-------^--------+
                                            |  SNMPv2c, community=classroom-manual
                                    +-------+--------+
                                    |    Telegraf    |  (classnet)
                                    +-------+--------+
                                            |
                                    +-------v--------+
                                    |    InfluxDB    |
                                    +-------^--------+
                                            |
                                    +-------+--------+
                                    |    Grafana     |
                                    +----------------+
```

---

## Arranque Rápido

```bash
cd monitoring
docker compose up --build
```

Serviços expostos no host:

| Serviço  | URL / Porta          |
|----------|----------------------|
| Grafana  | http://localhost:3000 |
| InfluxDB | http://localhost:8086 |
| router snmpd | UDP 161         |

Credenciais Grafana por omissão: `admin` / `admin`.

NOTA: para limpar completamente dockers, imagens e volumes de execuções prévias,
fazer, dentro pasta monitoring:

```bash
cd monitoring
docker compose down --volumes --rmi all
```

---

## Passo 1 — Verificar o Simulador SNMP (snmpsim)

Confirma que o snmpsim arrancou e está a servir dados:

```bash
docker logs snmpsim
```

Deves ver algo como:

```
snmpsim: using 1 data files...
snmpsim: listening on UDP/IPv4 endpoint 0.0.0.0:161
```

Se vires o erro `Must drop privileges`, o container não tem
`--process-user` no CMD — ver `snmpsim/Dockerfile`.

---

## Passo 2 — Testar SNMP a partir do Telegraf

O container do telegraf está na mesma rede (`classnet`) que o snmpsim e tem as ferramentas net-snmp disponíveis. É o ponto ideal para testar antes de ir ao InfluxDB.

```bash
docker exec -it telegraf bash
```

### 2a. Testar o router (SNMPv3)

```bash
# System info
snmpget -v3 -u snmpadmin -l authPriv \
        -a SHA -A authpass123 \
        -x AES -X privpass123 \
        router:161 SNMPv2-MIB::sysDescr.0

# Walk às interfaces
snmpwalk -v3 -u snmpadmin -l authPriv \
         -a SHA -A authpass123 \
         -x AES -X privpass123 \
         router:161 IF-MIB::ifTable
```

### 2b. Testar o simulador CLASSROOM-MIB (SNMPv2c)

```bash
# Walk completo à CLASSROOM-MIB (OIDs numéricos)
snmpwalk -v2c -c classroom-manual snmpsim:161 1.3.6.1.3.2026

# Só a roomTable
snmpwalk -v2c -c classroom-manual snmpsim:161 1.3.6.1.3.2026.1

# Só a studentTable
snmpwalk -v2c -c classroom-manual snmpsim:161 1.3.6.1.3.2026.2

# Só a classTable
snmpwalk -v2c -c classroom-manual snmpsim:161 1.3.6.1.3.2026.3
```

Com resolução de nomes MIB (a MIB está em `/usr/share/snmp/mibs/`):

```bash
MIBS=+ALL MIBDIRS=/usr/share/snmp/mibs \
  snmpwalk -v2c -c classroom-manual snmpsim:161 CLASSROOM-MIB::classroomMIB
```

---

## Passo 3 — Verificar Dados no InfluxDB

```bash
docker exec -it influxdb influx -database snmp
```

Na shell InfluxQL:

```sql
-- Ver todas as measurements disponíveis
SHOW MEASUREMENTS

-- ── Cenário 1: Router ──────────────────────────────────────────
-- Uptime e info do sistema
SELECT last("sysUpTime") / 100 AS uptime_s FROM "snmp_router"

-- Tráfego nas interfaces (octets acumulados)
SELECT last("ifHCInOctets"), last("ifHCOutOctets")
FROM "interfaces"
GROUP BY "ifDescr"

-- ── Cenário 2: Classroom ───────────────────────────────────────
-- Salas com capacidade e estado
SELECT last("capacity"), last("adminStatus"), last("operStatus")
FROM "classroom_rooms"
GROUP BY "campus", "building"

-- Alunos com ano de curso
SELECT last("courseYear")
FROM "classroom_students"
GROUP BY "studentName", "course"

-- Presenças em aula
SELECT last("position")
FROM "classroom_classes"
GROUP BY "className", "index"
```

Se as measurements `classroom_*` não aparecerem, consulta os logs do telegraf:

```bash
docker logs telegraf --tail 50 | grep -i "classroom\|error\|warn"
```

---

## Passo 4 — Configurar o Datasource no Grafana

1. Abre **http://localhost:3000** (admin / admin)
2. Menu lateral → **Connections** → **Data sources** → **Add data source**
3. Escolhe **InfluxDB**
4. Preenche:

   | Campo        | Valor                    |
   |--------------|--------------------------|
   | Name         | `InfluxDB`               |
   | URL          | `http://influxdb:8086`   |
   | Database     | `snmp`                   |
   | HTTP Method  | `GET`                    |

5. Clica **Save & test** — deves ver *"datasource is working"*

> **Nota:** O nome `InfluxDB` (com maiúscula) é importante — é o `uid` referenciado nos dashboards JSON.

---

## Passo 5 — Importar os Dashboards

1. Menu lateral → **Dashboards** → **Import**
2. Clica **Upload dashboard JSON file**

Importa os dois ficheiros da pasta `grafana/`:

| Ficheiro                                          | Conteúdo                              |
|---------------------------------------------------|---------------------------------------|
| `SNMP Router Mini Dashboard-1775746647598.json`   | Router: uptime, tráfego, interfaces   |
| `CLASSROOM_MIB_Dashboard.json`                    | Salas, alunos, presenças em aula      |

3. Confirma o datasource **InfluxDB** no dropdown e clica **Import**

> Se os painéis aparecerem vazios, verifica que o time range está em **Last 1 hour**. Os dados do classroom são estáticos — precisam de estar dentro da janela temporal selecionada.

---

## Sequência de Observação Sugerida

### Fase 1 — Tráfego de rede em tempo real

Abre o dashboard **SNMP Router Mini Dashboard** e observa:

- **Router Uptime** — tempo desde o arranque do container
- **Inbound / Outbound Traffic per Interface** — gráfico de série temporal com o tráfego iperf a atravessar as duas interfaces do router em tempo real (atualiza a cada 10 s)
- **Interface Status** — estado admin/oper de cada interface

O iperf-client gera tráfego UDP contínuo para o iperf-server através do router. Consegues ver os octets a subir nas interfaces `eth0` e `eth1` do router.

### Fase 2 — Dados académicos via MIB customizada

Abre o dashboard **CLASSROOM-MIB Dashboard** e observa:

- **Salas** — campus, edifício, capacidade e estado operacional (codificado na MIB como inteiros; mapeados no Grafana para texto com cores)
- **Alunos** — lista com nome, curso e ano académico
- **Presenças** — registo de cada aluno numa aula com o lugar atribuído

Estes dados são servidos pelo snmpsim a partir do ficheiro `snmpsim/data/classroom-manual.snmprec`, que simula um agente SNMP real respondendo à CLASSROOM-MIB.

---

## Estrutura de Ficheiros

```
monitoring/
├── docker-compose.yml          # Stack completa
├── router/
│   ├── Dockerfile              # Ubuntu + net-snmp + iperf3
│   ├── snmpd.conf              # Configuração SNMPv3
│   └── entrypoint.sh
├── host/
│   ├── Dockerfile              # iperf3 client/server
│   └── entrypoint.sh
├── snmpsim/
│   ├── Dockerfile              # Python + snmpsim-lextudio
│   └── data/
│       └── classroom-manual.snmprec   # Dados simulados CLASSROOM-MIB
├── telegraf/
│   ├── telegraf.conf           # Inputs SNMP (router + snmpsim)
│   └── mibs/                   # MIBs para resolução de nomes
│       └── CLASSROOM-MIB.txt
└── grafana/
    ├── SNMP Router Mini Dashboard-1775746647598.json
    └── CLASSROOM_MIB_Dashboard.json
```

---

## Troubleshooting Rápido

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| `snmpsim` reinicia em loop | Erro de privilégios | Confirma `--process-user=nobody --process-group=nogroup` no Dockerfile |
| `OID not increasing` no snmpsim | Ordem dos OIDs no `.snmprec` | OIDs têm de estar em ordem crescente estrita; dentro de cada coluna, ordenar por valor do índice |
| Measurements não aparecem no InfluxDB | Telegraf não alcança o agente | Verificar redes Docker; testar com snmpwalk a partir do telegraf |
| Painéis Grafana vazios | Time range demasiado curto | Selecionar **Last 1 hour** ou mais |
| Datasource error no Grafana | UID errado | O datasource tem de se chamar exatamente `InfluxDB` |
