---
title: GVR - Exercicio MIB
created: 2025-10-15 22:19
---

# GVR - Exercicio MIB

## Problema

- registar presenças dos alunos numa sala de aula via SNMP :-)

## Pressupostos

- existe uma câmara de filmar que captura imagem da sala
- os alunos são identificados por módulo de identificação de rosto (vamos fingir que não há RGPD :-) )
- os objetos são definidos numa MIB experimental 
- agente SNMP simulado com snmsim
- estação de gestão com net-snmp (linha de comando)

## Figura

![[figure-overview.png]]

## Ferramentas a usar

- [SMI Tools](https://www.ibr.cs.tu-bs.de/projects/libsmi/tools.html): para validar a MIB (validar e corrigir a syntaxe)
- [snmpsim](https://docs.lextudio.com/snmpsim/): simulador do agente snmp
- [net-snmp](https://www.ibr.cs.tu-bs.de/projects/libsmi/tools.html) ou [PySNMP](https://docs.lextudio.com/snmp/) para clientes de linha (snmpget, snmpbulkget, etc)

## Como instalar (Ubuntu ou Windows WSL):

| **Package**           | **Como instalar**                          | **Descrição**                                  |
| --------------------- | ------------------------------------------ | ---------------------------------------------- |
| **SNMP Simulator**    | pip install snmpsim                        | snmpsim-command-responder, snmpsim-record-mibs |
| **libsmi / smitools** | sudo apt install smitools                  | smilint, smidump                               |
| **Net-SNMP**          | sudo apt install snmp snmp-mibs-downloader | snmpget, snmpwalk, etc.                        |
| **PySNMP**            | pip install --upgrade pysnmp pysmi         | snmpget, snmpwalk, etc.                        |

Ver o que está instalado no python:
```bash
pip show snmpsim pysnmp pysmi pysnmp-mibs snmpsim-data
```

Ver o que está obsoleto 
```bash
pip list --outdated
```

Atualização para última versão (opcional)
```bash
pip install --upgrade ssnmpsim pysnmp pysmi pysnmp-mibs snmpsim-data
```

## Como instalar (MacOS)

NOTA: usar *apenas uma* das ferramentas de gestão de pacotes [brew](https://brew.sh/) ou [port](https://www.macports.org/), de acordo com a sua preferência

- ou com mac brew 
```
brew install libsmi
sudo port install libsmi 
```

- ou com MacPorts
```
sudo port install libsmi 
```

E depois instalar do mesmo modo os módulos python com pip install...


## Teste rápido das ferramentas

```bash
smilint -h
smidump -h
smidump -f tree IF-MIB
snmpget
snmpwalk
snmpsim-command-responder
```

## Criação e teste da MIB

### Sumário

**Etapa 1**: Planear a MIB (definir objetos, syntax, acesso) e a SMI (árvore de OIDs dos objetos definidos)
**Etapa 2**: Descarregar uma MIB exemplo NET-SNMP  para facilitar a edição/criação da nova MIB
**Etapa 3**: Editar a MIB de acordo com o planeamento feito
**Etapa 4**: Validar a MIB com a ferramenta **smilint**
**Etapa 5**: Inventar dados para simular a MIB (à mão ou com gerador de dados)
**Etapa 6** Executar o simulador - agente SNMP com os dados gerados
**Etapa 7**: Interrogar o agente (testes)

### Etapa 1:  Planear a MIB e a SMI

- Nome do módulo (em letras maiúsculas): CLASSROOM-MIB
- Prefixo a usar nos objetos (em letras minúsculas):  classroom
- OID da raíz da MIB (top-level OID): abaixo de experimental(1.3.6.1.3), usando OID 2025

```md
iso(1).org(3).dod(6).internet(1).experimental(3)
  └─ classroomMIB(2025)
     ├─ roomId(1)
     └─ roomName(2)
     ...
```


ACESSOS

| **MAX-ACCESS value**      | **Meaning**                                                                        | **Typical usage**                                                |
| ------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **not-accessible**        | Object exists for indexing or structure only; cannot be retrieved or set directly. | Table & entry nodes; index columns                               |
| **read-only**             | Can only be read (GET, GETNEXT, GETBULK).                                          | Counters, status, statistics                                     |
| **read-write**            | Can be read and modified (GET, SET).                                               | Configurable parameters                                          |
| **read-create**           | Same as read-write, _plus_ the ability to create new table rows.                   | Columns in tables that support dynamic creation (with RowStatus) |
| **accessible-for-notify** | Used only in notification definitions.                                             | Trap/notification parameters                                     |

Objetos:
- Uma sala, tem um id (inteiro), um nome (string), capacidade (inteiro), estado (conjunto de valores), estado administrativo (conjunto de valores)
- Depois temos uma tabela com o numero do lugar, estudante que lá está (nº de estudante, nome, ano, curso)

Sala de aula:

- roomName (DisplayString), **read-write**
- roomCapacity (Integer32), **read-write**
- roomOperStatus (INTEGER { available(1), occupied(2), closed(3) }), **read-write** (runtime)
- roomAdminStatus (INTEGER { up(1), down(2) }), **read-write** (optional control)

Tabela de estudantes detetados pela camara e módulo de processamento de imagem:
- studentTable (table), studentEntry (row)
    - id (Unsigned32), not-accessible (index)
    - studentName (DisplayString), **read-create**   
    - studentYear (INTEGER { first(1), second(2), third(3), fourth(4), fifth(5), other(99) }), **read-create**
    - studentCourse (DisplayString), **read-create**
    - status  (RowStatus), **read-create** (para gerir esta linha da tabela: apagar, criar, alterar)

### Etapa 2:  Descarregar MIB exemplo

```bash
wget http://net-snmp.sourceforge.net/docs/mibs/NET-SNMP-EXAMPLES-MIB.txt
cp NET-SNMP-EXAMPLES-MIB.txt CLASSROOM-MIB.mib
```

### Etapa 3:  Editar MIB de acordo com o planeamento

Esta primeira versão tem naturalmente um conjunto de erros, que podem ser corrigidos depois da compilação, seguindo as dicas do compilador:


```mib
CLASSROOM-MIB DEFINITIONS ::= BEGIN

--
-- MIB objects for classroom monitoring example implementations
--

IMPORTS
    MODULE-IDENTITY, OBJECT-TYPE, Integer32,
    NOTIFICATION-TYPE                       FROM SNMPv2-SMI
    RowStatus, StorageType                  FROM SNMPv2-TC
    InetAddressType, InetAddress            FROM INET-ADDRESS-MIB
;

-- MODLUE IDENTITY: classromMIB
-- REVISION e LAST-UPDATED sao datas no formato AAAAMMDDHHMM
-- Tem de haver um REVISION igual a LAST-UPDATED 


classroomMIB MODULE-IDENTITY
    LAST-UPDATED "202510160000Z"
    ORGANIZATION "www.net-snmp.org"
    CONTACT-INFO    
    "postal:   Campus de Azurem
                4800-058 GUIMARAES
                Portugal
      email:    gvr@uminho.pt"

    "Aula de Gestao e Virtualizacao de Redes do MIETI"
    DESCRIPTION
    "MIB objects for classroom monitoring example implementations"
    REVISION     "202510160000Z"
    DESCRIPTION
    "Classroom monitoring MIB: a single room (scalars) and a table of students."
    ::= { experimental 2025 }

-- Top-level branch for objects
classroomObjects OBJECT IDENTIFIER ::= { classroomMIB 1 }

-- ---------- Textual Conventions ----------
RoomOperStatus ::= INTEGER { available(1), occupied(2), closed(3) }
RoomAdminStatus ::= INTEGER { open(1), closed(2) }
StudentYear     ::= INTEGER { first(1), second(2), third(3), fourth(4), fifth(5), other(99) }

-- ======================================================
-- Room (single instance) — scalars
-- ======================================================

roomName OBJECT-TYPE
  SYNTAX        DisplayString (SIZE (0..64))
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Human-readable room name."
  ::= { classroomObjects 1 }

roomCapacity OBJECT-TYPE
  SYNTAX        Integer32 (0..10000)
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Maximum occupants allowed in the room."
  ::= { classroomObjects 2 }

roomOperStatus OBJECT-TYPE
  SYNTAX        RoomOperStatus
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Operational status of the room (runtime)."
  ::= { classroomObjects 3 }

roomAdminStatus OBJECT-TYPE
  SYNTAX        RoomAdminStatus
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Administrative enable/disable of the room."
  ::= { classroomObjects 4 }

-- ======================================================
-- Students (in the single room) — table
-- ======================================================

studentTable OBJECT-TYPE
  SYNTAX        SEQUENCE OF StudentEntry
  MAX-ACCESS    not-accessible
  STATUS        current
  DESCRIPTION   "Students present/registered for the (single) room."
  ::= { classroomObjects 10 }

studentEntry OBJECT-TYPE
  SYNTAX        StudentEntry
  MAX-ACCESS    not-accessible
  STATUS        current
  DESCRIPTION   "One student row. Managed via RowStatus (create, modify, delete)."
  INDEX         { studentId }
  ::= { studentTable 1 }

StudentEntry ::=
  SEQUENCE {
    studentId        Unsigned32,
    studentName      DisplayString,
    studentYear      StudentYear,
    studentCourse    DisplayString,
    studentStatus    RowStatus
  }

studentId OBJECT-TYPE
  SYNTAX        Unsigned32
  MAX-ACCESS    not-accessible
  STATUS        current
  DESCRIPTION   "Row index (unique student identifier within this agent)."
  ::= { studentEntry 1 }

studentName OBJECT-TYPE
  SYNTAX        DisplayString (SIZE (0..64))
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Student full name."
  ::= { studentEntry 2 }

studentYear OBJECT-TYPE
  SYNTAX        StudentYear
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Academic year."
  ::= { studentEntry 3 }

studentCourse OBJECT-TYPE
  SYNTAX        DisplayString (SIZE (0..64))
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Course/program (e.g., MIETI)."
  ::= { studentEntry 4 }

studentStatus OBJECT-TYPE
  SYNTAX        RowStatus
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION
    "Row lifecycle: use createAndGo(4)/createAndWait(5) to create;
     set active(1)/notInService(2) to enable/disable; destroy(6) to delete."
  ::= { studentEntry 5 }

END

```


### Etapa 4:  Validar a MIB

```bash
smilint -s -m -l 6 -p /usr/share/snmp/mibs/  ./CLASSROOM-MIB.mib
```

ou simplesmente:
```bash
smilint -s -m -l 3 ./CLASSROOM-MIB.mib
```

Nota: a opção -l 6 aumenta o nível de avisos que são enviados (warnings). O default é 3.

Depois será melhor copiar a MIB validada para a uma das pastas em que as ferramentas SNMP as podem ler. Normalmente em ```~/snmp/mibs``` mas pode ser noutro local. 

```bash
mkdir -p ~/snmp/mibs
cp ./CLASSROOM-MIB.mib ~/snmp/mibs/CLASSROOM-MIB.txt
```


O que é obrigatório fazer é definir as variáveis de ambiente adequadas para ajudar a localizar as MIBS. Algo do género, que pode mesmo ser colocado no ficheiro de configuração da bash ```.bashrc```ou equivalente:

Em **Linux/Windows** deve bastar algo como:
```bash
export MIBDIRS=$HOME/snmp/mibs:/usr/share/snmp/mibs
export MIBS=+ALL
```

Em **MacOS**, supondo que se usa *Homebrew* ou *MacPorts*, talvez acrescentar essas duas pastas adicionais:
```bash
export MIBDIRS=$HOME/snmp/mibs:/usr/share/snmp/mibs:/opt/local/share/snmp/mibs:/opt/homebrew/share/snmp/mibs
export MIBS=+ALL
```

O que permitirá ver traduzir os OID de números para nomes e vice-versa. Passará a ser indiferente usar uns ou outros. Podemos testar com:

```bash
snmptranslate -Td -OS CLASSROOM-MIB::studentTable
```

Nesta altura deveremos ter uma versão da MIB já sem errors nenhuns. 
Algo do género de (**CLASSROOM-MIB.mib**):

```mib
CLASSROOM-MIB DEFINITIONS ::= BEGIN

--
-- MIB objects for classroom monitoring example implementations
--

IMPORTS
    MODULE-IDENTITY, OBJECT-TYPE, Integer32, Unsigned32, experimental,
    NOTIFICATION-TYPE                       FROM SNMPv2-SMI
    RowStatus, StorageType, DisplayString   FROM SNMPv2-TC
    InetAddressType, InetAddress            FROM INET-ADDRESS-MIB
;

-- MODLUE IDENTITY: classromMIB
-- REVISION e LAST-UPDATED sao datas no formato AAAAMMDDHHMM
-- Tem de haver um REVISION igual a LAST-UPDATED 


classroomMIB MODULE-IDENTITY
    LAST-UPDATED "202510230000Z"
    ORGANIZATION "www.net-snmp.org"
    CONTACT-INFO    
    "postal:   Campus de Azurem
                4800-058 GUIMARAES
                Portugal
      email:    gvr@uminho.pt"
    DESCRIPTION
    "MIB objects for classroom monitoring example implementations"
    REVISION     "202510230000Z"
    DESCRIPTION
    "Classroom monitoring MIB: a single room (scalars) and a table of students."
    ::= { experimental 2025 }

-- Top-level branch for objects
classroomObjects OBJECT IDENTIFIER ::= { classroomMIB 1 }

-- Textual Conventions ----------
RoomOperStatus ::= INTEGER { available(1), occupied(2), closed(3) }
RoomAdminStatus ::= INTEGER { open(1), closed(2) }
StudentYear     ::= INTEGER { first(1), second(2), third(3), fourth(4), fifth(5), other(99) }

-- ======================================================
-- Room (single instance) — scalars
-- ======================================================

roomName OBJECT-TYPE
  SYNTAX        DisplayString (SIZE (0..64))
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Human-readable room name."
  ::= { classroomObjects 1 }

roomCapacity OBJECT-TYPE
  SYNTAX        Integer32 (0..10000)
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Maximum occupants allowed in the room."
  ::= { classroomObjects 2 }

roomOperStatus OBJECT-TYPE
  SYNTAX        RoomOperStatus
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Operational status of the room (runtime)."
  ::= { classroomObjects 3 }

roomAdminStatus OBJECT-TYPE
  SYNTAX        RoomAdminStatus
  MAX-ACCESS    read-write
  STATUS        current
  DESCRIPTION   "Administrative enable/disable of the room."
  ::= { classroomObjects 4 }

-- ======================================================
-- Students (in the single room) — table
-- ======================================================

studentTable OBJECT-TYPE
  SYNTAX        SEQUENCE OF StudentEntry
  MAX-ACCESS    not-accessible
  STATUS        current
  DESCRIPTION   "Students present/registered for the (single) room."
  ::= { classroomObjects 10 }

studentEntry OBJECT-TYPE
  SYNTAX        StudentEntry
  MAX-ACCESS    not-accessible
  STATUS        current
  DESCRIPTION   "One student row. Managed via RowStatus (create, modify, delete)."
  INDEX         { studentId }
  ::= { studentTable 1 }

StudentEntry ::=
  SEQUENCE {
    studentId        Unsigned32,
    studentName      DisplayString,
    studentYear      StudentYear,
    studentCourse    DisplayString,
    studentRoomSeatNumber  Unsigned32,
    studentStatus    RowStatus
  }

studentId OBJECT-TYPE
  SYNTAX        Unsigned32
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Row index (unique student identifier within this agent)."
  ::= { studentEntry 1 }

studentName OBJECT-TYPE
  SYNTAX        DisplayString
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Student full name."
  ::= { studentEntry 2 }

studentYear OBJECT-TYPE
  SYNTAX        StudentYear
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Academic year."
  ::= { studentEntry 3 }

studentCourse OBJECT-TYPE
  SYNTAX        DisplayString
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Course/program (e.g., MIETI)."
  ::= { studentEntry 4 }

studentRoomSeatNumber OBJECT-TYPE
  SYNTAX        Unsigned32
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION   "Room place number where the student was identified"
  ::= { studentEntry 5 }

studentStatus OBJECT-TYPE
  SYNTAX        RowStatus
  MAX-ACCESS    read-create
  STATUS        current
  DESCRIPTION
    "Row lifecycle: use createAndGo(4)/createAndWait(5) to create;
     set active(1)/notInService(2) to enable/disable; destroy(6) to delete."
  ::= { studentEntry 6 }

END

```

### Etapa 5:  Inventar dados para simulação

Correr o mib compiler, que provavelmente se pode executar apenas como **mibdump**

```bash 
mibdump --help
```

No entanto, se o comando não existir, pode-se correr desta outra forma, e, nesse caso, fará sentido criar um *alias* para ter o comando na forma alternativa mibdump:

```bash
python -m pysmi.tools.mibdump --help
alias mibdump="python -m pysmi.tools.mibdump"
mibdump --help
```

Criar diretorias e compilar a MIB para Python para que as ferramentas do PySNMP as possam usar (simulador, gerador de dados, etc):

```bash
mkdir -p ~/snmp/mibs
mkdir -p ~/.pysnmp/mibs
mibdump  --mib-source ~/snmp/mibs --destination-directory ~/.pysnmp/mibs ./CLASSROOM-MIB.mib
```

A operação anterior deve criar uma versão python na pasta ```~/.pysnmp/mibs```. Confirmar com um comando ```ls -lisat ~/.pysnmp/mibs```.

E depois gerar os dados, totalmente aleatórios e sem sentido (*classroom-auto.snmprec*):

```bash
mkdir -p data
snmpsim-record-mibs --mib-module CLASSROOM-MIB --output-file data/classroom-auto.snmprec
```

ou gerar de forma mais manual e controlada (4 alunos, com nomes editados):

```bash
mkdir -p data
snmpsim-record-mibs --mib-module CLASSROOM-MIB --output-file data/classroom-manual.snmprec --table-size=4 --manual-values
```

Exemplo de dados num ficheiro criado manualmente (*classroom-manual.snmprec*):

```txt
1.3.6.1.3.2025.1.1.0|4|Lab 1.38 - Ed 11 - Campus de Azurem
1.3.6.1.3.2025.1.2.0|2|30
1.3.6.1.3.2025.1.3.0|2|1
1.3.6.1.3.2025.1.4.0|2|2
1.3.6.1.3.2025.1.10.1.1.11111|66|11111
1.3.6.1.3.2025.1.10.1.1.22222|66|22222
1.3.6.1.3.2025.1.10.1.1.33333|66|33333
1.3.6.1.3.2025.1.10.1.1.44444|66|44444
1.3.6.1.3.2025.1.10.1.2.11111|4|Alvaro Campos
1.3.6.1.3.2025.1.10.1.2.22222|4|Rita Manuela
1.3.6.1.3.2025.1.10.1.2.33333|4|Fernando Manuel
1.3.6.1.3.2025.1.10.1.2.44444|4|Rui Silva
1.3.6.1.3.2025.1.10.1.3.11111|2|4
1.3.6.1.3.2025.1.10.1.3.22222|2|1
1.3.6.1.3.2025.1.10.1.3.33333|2|1
1.3.6.1.3.2025.1.10.1.3.44444|2|5
1.3.6.1.3.2025.1.10.1.4.11111|4|Mestrado Integrado em Eng. Telecomunicações e Informática
1.3.6.1.3.2025.1.10.1.4.22222|4|Mestrado em Eng. Telecomunicações e Informática
1.3.6.1.3.2025.1.10.1.4.33333|4|Mestrado em Eng. Telecomunicações e Informática
1.3.6.1.3.2025.1.10.1.4.44444|4|Mestrado Integrado em Eng. Telecomunicações e Informática
1.3.6.1.3.2025.1.10.1.5.11111|66|11
1.3.6.1.3.2025.1.10.1.5.22222|66|12
1.3.6.1.3.2025.1.10.1.5.33333|66|20
1.3.6.1.3.2025.1.10.1.5.44444|66|21
1.3.6.1.3.2025.1.10.1.6.11111|2|3
1.3.6.1.3.2025.1.10.1.6.22222|2|1
1.3.6.1.3.2025.1.10.1.6.33333|2|1
1.3.6.1.3.2025.1.10.1.6.44444|2|6
```

### Etapa 6:  Executar o simulador

```bash
snmpsim-command-responder --data-dir ./data --agent-udpv4-endpoint 127.0.0.1:2001
```

O simulador indica que as comunidades de acesso são derivados do nome dos ficheiros de dados. Por exemplo o ficheiro *classroom-manual.snmprec* é carregado pelo agente e deve ser acedido com a comunidade "classroom-manual". Por seu lado o ficheiro de dados *classroom-auto.snmprec* é também carregado pelo agente mas acessível comunidade "classroom-auto".

### Etapa 7:  Interrogar e testar o agente

```bash
snmpwalk -v2c -c classroom-manual 127.0.0.1:2001 experimental.classroomMIB
snmpwalk -v2c -c classroom-manual 127.0.0.1:2001 .1.3.6.1.3.2025
snmptable -v2c -c classroom-manual  127.0.0.1:2001 experimental.classroomMIB.classroomObjects.studentTable

snmpwalk -v2c -c classroom-auto  127.0.0.1:2001 experimental.classroomMIB
snmpwalk -v2c -c classroom-auto 127.0.0.1:2001 .1.3.6.1.3.2025
snmptable -v2c -c classroom-auto  127.0.0.1:2001 experimental.classroomMIB.classroomObjects.studentTable

```

## Perguntas

- Como podemos melhorar o modelo para em vez de apenas uma sala ter todas as salas do Campus? (redefinição da MIB)
- Como responder às seguintes perguntas  (comandos SNMP):
    - "quantos lugares tem a sala"
    - "quantos alunos estão na sala"
    - "quais os números e nomes dos alunos nos 3 primeiros lugares sentados"
- Pense num algoritmo para marcar as presenças dos alunos na aula de GVR (por exemplo)

## Referências

- [md_RFC 2579 Textual Conventions for SMIv2](https://www.rfc-editor.org/rfc/rfc2579.html)
- [md_libsmi - A Library to Access SMI MIB Information](https://www.ibr.cs.tu-bs.de/projects/libsmi/)
- [md_Tools](https://www.ibr.cs.tu-bs.de/projects/libsmi/tools.html)
- [md_Complete MIB Database - All SNMP MIBs and OIDs](https://mibs.observium.org/all/)
- [md_net-snmpmibs](https://github.com/hardaker/net-snmp/tree/master/mibs)
- [md_Net-SNMP](https://www.net-snmp.org/docs/mibs/)
- [md_Net-SNMP](https://www.net-snmp.org/)
- [md_PySNMP 7 Homepage](https://docs.lextudio.com/snmp/)
- [md_SNMP Simulator Documentation](https://docs.lextudio.com/snmpsim/)

-------
`path:` [[As Minhas Smart Notes]] 
`seeAlso:` 

