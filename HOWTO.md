# HOW-TO

## Como addicionar linhas a uma tabela?


```mermaid

stateDiagram-v2
    [*] --> active : createAndGo(4)

    [*] --> notReady : createAndWait(5)
    notReady --> notInService : preencher campos obrigatórios
    notInService --> active : active(1)

    active --> notInService : notInService(2)

    active --> [*] : destroy(6)
    notInService --> [*] : destroy(6)
    notReady --> [*] : destroy(6)

