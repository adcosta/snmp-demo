# gnmi-lab — Documento de Referência

Exercício de introdução aos protocolos de gestão de routers: **gNMI**, **gNOI**, **NETCONF** e **JSON-RPC**.

---

## Ambiente

- **Router:** Nokia SR Linux (container)
- **Orquestração:** Containerlab (dentro de VM OrbStack / Linux)
- **Topologia:** um único router

### Ficheiro de topologia (`lab.yml`)

```yaml
name: gnmi-lab

topology:
  nodes:
    srl:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux:latest
```

### Arrancar e parar o lab

```bash
sudo containerlab deploy -t lab.yml
sudo containerlab destroy -t lab.yml
```

### Configuração do cliente gnmic (`~/.gnmic.yml`)

```yaml
username: admin
password: NokiaSrl1!
skip-verify: true
encoding: json_ietf
targets:
  clab-gnmi-lab-srl:57400:
```

---

## gNMI

Porta `57400` (TLS) | Cliente: `gnmic`

### Capabilities — o que o router suporta

```bash
gnmic capabilities
```

Devolve os modelos YANG suportados e os encodings disponíveis.

### GET — ler configuração e estado

```bash
# Informação do sistema
gnmic get --path /system/information

# Todas as interfaces
gnmic get --path /interface

# Interface específica
gnmic get --path /interface[name=mgmt0]

# Campo específico
gnmic get --path /interface[name=mgmt0]/oper-state
gnmic get --path /interface[name=mgmt0]/statistics
```

### SET — modificar configuração

```bash
# Atualizar um valor
gnmic set \
  --update-path /interface[name=mgmt0]/description \
  --update-value "interface de gestao"

# Substituir um bloco
gnmic set \
  --replace-path /interface[name=mgmt0]/description \
  --replace-value "substituida com replace"

# Apagar um valor
gnmic set --delete /interface[name=mgmt0]/description
```

| Operação | Comportamento |
|---|---|
| update | Modifica só o campo indicado, mantém o resto |
| replace | Substitui o nó inteiro |
| delete | Remove o valor |

### SUBSCRIBE — telemetria em tempo real

```bash
# Amostragem a cada 5 segundos
gnmic sub \
  --path /interface[name=mgmt0]/statistics \
  --stream-mode sample \
  --sample-interval 5s

# Só quando há mudança de estado
gnmic sub \
  --path /interface[name=mgmt0]/oper-state \
  --stream-mode on-change

# Uma única leitura via stream
gnmic sub \
  --path /interface[name=mgmt0]/statistics \
  --stream-mode once
```

| Modo | Comportamento |
|---|---|
| sample | Stream contínuo a intervalos regulares |
| on_change | Stream contínuo, só quando o valor muda |
| once | Leitura única, termina de seguida |

---

## gNOI — gRPC Network Operations Interface

Porta `57400` (TLS) | Cliente: `gnoic`

O gNOI complementa o gNMI — enquanto o gNMI gere *estado* (configuração e telemetria), o gNOI executa *operações* pontuais no router.

### Instalar o gnoic

```bash
bash -c "$(curl -sL https://get-gnoic.openconfig.net)"
```

### System — operações do sistema

```bash
# Ping a partir do router
gnoic -a clab-gnmi-lab-srl:57400 \
      -u admin -p 'NokiaSrl1!' \
      --skip-verify \
      system ping --destination 8.8.8.8 --count 3

# Traceroute a partir do router
gnoic -a clab-gnmi-lab-srl:57400 \
      -u admin -p 'NokiaSrl1!' \
      --skip-verify \
      system traceroute --destination 8.8.8.8

# Hora do sistema
gnoic -a clab-gnmi-lab-srl:57400 \
      -u admin -p 'NokiaSrl1!' \
      --skip-verify \
      system time
```

### File — operações sobre ficheiros

```bash
# Ver metadados de ficheiros no router
gnoic -a clab-gnmi-lab-srl:57400 \
      -u admin -p 'NokiaSrl1!' \
      --skip-verify \
      file stat --path /etc/
```

### Operações disponíveis por serviço

| Serviço | Operação | Equivalente CLI |
|---|---|---|
| System | `Ping` | `ping 8.8.8.8` |
| System | `Traceroute` | `traceroute 8.8.8.8` |
| System | `Reboot` | `reload` |
| System | `Time` | `show clock` |
| System | `KillProcess` | matar processo interno |
| File | `Get` | copiar ficheiro do router |
| File | `Put` | enviar ficheiro para o router |
| File | `Stat` | ver metadados de ficheiros |
| Certificate | `Install` | instalar certificado TLS |
| Certificate | `Rotate` | renovar certificado |
| BGP | `ClearBGPNeighbor` | `clear bgp neighbor` |

---

## NETCONF

Porta `830` (SSH) | Cliente: `netconf-console2`

### Hello — capabilities do servidor

```bash
netconf-console2 \
  --host clab-gnmi-lab-srl --port 830 \
  -u admin -p 'NokiaSrl1!' \
  --hello
```

### Get-config — ler configuração

```bash
netconf-console2 \
  --host clab-gnmi-lab-srl --port 830 \
  -u admin -p 'NokiaSrl1!' \
  --get-config
```

### Get — ler estado operacional

```bash
netconf-console2 \
  --host clab-gnmi-lab-srl --port 830 \
  -u admin -p 'NokiaSrl1!' \
  --get
```

### Get com filtro xpath

```bash
netconf-console2 \
  --host clab-gnmi-lab-srl --port 830 \
  -u admin -p 'NokiaSrl1!' \
  --get --xpath '/interface[name="mgmt0"]'
```

---

## JSON-RPC

Porta `80` (HTTP) | Cliente: `curl`

O SR Linux implementa JSON-RPC como interface HTTP — não RESTCONF puro (RFC 8040).

### Get — ler estado

```bash
curl -s -u admin:'NokiaSrl1!' \
  http://clab-gnmi-lab-srl/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "get",
    "params": {
      "commands": [
        {
          "path": "/system/information",
          "datastore": "state"
        }
      ]
    }
  }'
```

```bash
# Interface específica
curl -s -u admin:'NokiaSrl1!' \
  http://clab-gnmi-lab-srl/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "get",
    "params": {
      "commands": [
        {
          "path": "/interface[name=mgmt0]",
          "datastore": "state"
        }
      ]
    }
  }'
```

---

## Comparação dos protocolos de gestão

| | gNMI | gNOI | NETCONF | JSON-RPC |
|---|---|---|---|---|
| Transporte | gRPC | gRPC | SSH | HTTP |
| Formato | JSON_IETF / Protobuf | Protobuf | XML | JSON |
| Porto | 57400 (TLS) / 57401 | 57400 (TLS) | 830 | 80 / 443 |
| Cliente | gnmic | gnoic | netconf-console2 | curl |
| Propósito | Configuração e telemetria | Operações pontuais | Configuração e estado | Configuração e estado |
| Telemetria | ✅ SUBSCRIBE | ❌ | ❌ | ❌ |
| Standard | OpenConfig / gNMI | OpenConfig / gNOI | RFC 6241 | Nokia SR Linux |

---

## A família gRPC em redes

Todos os protocolos abaixo correm sobre gRPC e usam Protobuf. O SR Linux tem suporte nativo para todos:

| Protocolo | Propósito |
|---|---|
| **gNMI** | Gestão de configuração e telemetria |
| **gNOI** | Operações pontuais (ping, reboot, ficheiros, certificados) |
| **gNSI** | Segurança (certificados, autenticação, autorização) |
| **gRIBI** | Injeção programática de rotas na RIB |
| **p4RT** | Programação do dataplane via P4 |

---

## Credenciais

| Campo | Valor |
|---|---|
| Utilizador | `admin` |
| Password | `NokiaSrl1!` |
| Target gNMI / gNOI | `clab-gnmi-lab-srl:57400` |
| Target NETCONF | `clab-gnmi-lab-srl:830` |
| Target JSON-RPC | `http://clab-gnmi-lab-srl/jsonrpc` |
