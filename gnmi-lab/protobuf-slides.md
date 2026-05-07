---
marp: true
theme: neobeam
paginate: true
---

# gRPC - Protocol Buffers

## O formato de serialização do gRPC

---

## RPC — Remote Procedure Call

Chamar uma função que corre noutro servidor como se fosse local:

```python
# Invocação semelhante a uma chamada local
resposta = router.get("/interface")

# Stubs do lado do cliente e do lado do servidor serializam pedido e resposta
# cliente → serializa pedido → rede → router → executa → rede → resposta
```

**gRPC** é a implementação de RPCs da Google 

| | |
|---|---|
| **HTTP/2** | Transporte multiplexado, mais eficiente que HTTP/1.1 |
| **Protobuf** | Formato binário compacto (em alternativa ao JSON/XML) |
| **`.proto`** | Definições: gera código cliente e servidor automaticamente |
| **Streaming** | Suporte nativo para streams bidirecionais |

> É a base de **gNMI, gNOI, gNSI, gRIBI** e **p4RT** em redes modernas.

---

## gRPC — Remote Procedure Call

Como é que dois sistemas trocam dados de forma eficiente?

<br>

**Texto (JSON)** — legível para humanos, à custa de overhead elevado
```json
{
  "interface": {
    "name": "mgmt0",
    "oper-state": "up",
    "mtu": 1500
  }
}
```

Só o campo `"oper-state"` ocupa **11 bytes** no nome, mais aspas, chavetas, espaços...

---

## gRPC Protobuf

### Codificação em formato binário simplificado

Os mesmos dados em formato Protobuf:

```
0a 05 6d 67 6d 74 30 12 02 75 70 18 dc 0b
```

- Ilegível por humanos
- Mas **extremamente compacto**
- Em vez do nome do campo, envia apenas um **número** que o identifica

<br>

> O receptor sabe que `1` = `name`, `2` = `oper_state`, `3` = `mtu`  
> porque ambos partilham o mesmo **ficheiro `.proto`**

---

## A analogia

<br>

| | Texto | Protobuf |
|---|---|---|
| Legibilidade | ✅ Humano | ❌ Binário |
| Tamanho | Grande | **Muito pequeno** |
| Velocidade | Lenta | **Rápida** |
| Ferramenta | Qualquer editor | Cliente específico |

<br>

> Protobuf é ao JSON o que um ZIP é a um ficheiro de texto —  
> os mesmos dados, muito menos espaço.

---

## Porquê isto importa em redes

Imagina um router a enviar telemetria de 1000 interfaces a cada segundo:

<br>

| Formato | Tamanho por mensagem | Por segundo |
|---|---|---|
| JSON | ~2 KB | ~2 MB/s |
| Protobuf | ~200 bytes | ~200 KB/s |

<br>

Com centenas de routers em produção, a diferença é **enorme**.  
É por isso que o gNMI com Protobuf substituiu o SNMP polling em redes modernas.

---

# Sintaxe `.proto`

---

## O ficheiro `.proto`

É o **contrato** entre emissor e receptor.  
Define a estrutura dos dados e as operações disponíveis.

```protobuf
syntax = "proto3";

message Interface {
  string name       = 1;
  string oper_state = 2;
  uint32 mtu        = 3;
}
```

- Cada campo tem um **número único** — é esse número que vai na mensagem binária
- `string`, `uint32`, `bool` — tipos de dados básicos
- `syntax = "proto3"` — versão do Protobuf (a atual)

---

## `message` — estruturas de dados

Equivalente a um objeto JSON ou uma struct:

```protobuf
message Interface {
  string name       = 1;   // campo 1
  string oper_state = 2;   // campo 2
  uint32 mtu        = 3;   // campo 3
}
```

Serializado em JSON seria:
```json
{
  "name": "mgmt0",
  "oper_state": "up",
  "mtu": 1500
}
```

Na wire, apenas: `01 "mgmt0"  02 "up"  03 1500`  
(simplificado — o real é binário)

---

## `repeated` — listas

Quando um campo pode ter **zero ou mais valores**:

```protobuf
message Interface {
  string          name       = 1;
  string          oper_state = 2;
  repeated string ip_address = 3;  // vários IPs possíveis
}
```

Equivalente em JSON:
```json
{
  "name": "mgmt0",
  "oper_state": "up",
  "ip_address": ["192.168.1.1/24", "10.0.0.1/32"]
}
```

Sem `repeated` → o campo só pode ter **um único valor**.

---

## `service` e `rpc` — as operações

Define as **chamadas remotas** que o servidor expõe — como uma API:

```protobuf
service InterfaceService {
  rpc GetInterface (GetRequest)  returns (Interface);
  rpc ListAll      (ListRequest) returns (InterfaceList);
}
```

- `service` — agrupa operações relacionadas
- `rpc` — cada operação individual
- `(GetRequest)` — mensagem de entrada
- `returns (Interface)` — mensagem de saída

---

## `stream` — streaming vs unário

Um `rpc` pode ser de quatro tipos:

```protobuf
// 1. Unário — um pedido, uma resposta
rpc Get (GetRequest) returns (GetResponse);

// 2. Server streaming — um pedido, múltiplas respostas
rpc Subscribe (SubscribeRequest) returns (stream SubscribeResponse);

// 3. Client streaming — múltiplos pedidos, uma resposta
rpc Set (stream SetRequest) returns (SetResponse);

// 4. Bidirectional streaming — múltiplos pedidos, múltiplas respostas
rpc Subscribe (stream SubscribeRequest) returns (stream SubscribeResponse);
```

---

## O `.proto` real do gNMI

```protobuf
service gNMI {
  rpc Capabilities (CapabilityRequest)        returns (CapabilityResponse);
  rpc Get          (GetRequest)               returns (GetResponse);
  rpc Set          (SetRequest)               returns (SetResponse);
  rpc Subscribe    (stream SubscribeRequest)  returns (stream SubscribeResponse);
}
```

Reconheces os nomes — são exatamente as operações do `gnmic`:

| `.proto` | `gnmic` |
|---|---|
| `Capabilities` | `gnmic capabilities` |
| `Get` | `gnmic get` |
| `Set` | `gnmic set` |
| `Subscribe` | `gnmic sub` |

---

## Porquê o Subscribe é bidirectional stream?

```protobuf
rpc Subscribe (stream SubscribeRequest) returns (stream SubscribeResponse);
```

- O **cliente** envia pedidos de subscrição continuamente  
  (pode adicionar/remover paths enquanto está ligado)
- O **router** responde continuamente com atualizações  
  (telemetria a cada X segundos, ou quando algo muda)

<br>

> É por isso que o terminal fica "preso" quando fazes `gnmic sub` —  
> a ligação está aberta nos dois sentidos.

---

## Como tudo se liga

```
ficheiro .proto
    │
    ├── message        define o formato dos dados (o quê)
    │     └── repeated    campos que são listas
    │
    └── service        define as operações disponíveis (como)
          └── rpc         cada operação individual
                └── stream   se for streaming ou não
```

<br>

O gRPC gera automaticamente código cliente e servidor a partir do `.proto` —  
em Python, Go, Java, e muitas outras linguagens.  
É por isso que o `gnmic` e o SR Linux falam a mesma língua.

---

## Resumo

| Conceito | O que define |
|---|---|
| `message` | Estrutura de dados (campos e tipos) |
| `repeated` | Campo que é uma lista |
| `service` | Conjunto de operações do servidor |
| `rpc` | Uma operação individual |
| `stream` | Se a operação é contínua ou pontual |

<br>

> O ficheiro `.proto` é o contrato.  
> O gRPC é o mecanismo.  
> O Protobuf é o formato.
