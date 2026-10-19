# ADR-005 — Rotas e schemas por módulo; fachada pública de integração

- Status: Aceito para execução do planejamento autorizado pelo responsável do projeto
- Data: 2026-10-15
- Relaciona-se com ADR-001, ADR-003 e ADR-004

A composição `main.py` acumulava rotas de Contracts, Support e Integration e
schemas sem proprietário. Módulos de negócio importavam IdempotencyRecord e
utilitários de integration.service, contrariando a fronteira pública prevista.

As rotas passam aos routers dos contextos correspondentes. `main.py` mantém
composição dos adaptadores/serviços, inicialização, middleware, health checks,
métricas, estado da demonstração e arquivos estáticos. A configuração explícita
dos serviços nos routers preserva o padrão existente; não introduz contêiner de
injeção nem novos serviços distribuídos.

Schemas de CRM, Contracts, Support e Integration ficam em cada contexto.
`archcorp.schemas` continua como fachada dos imports públicos anteriores, usando
as mesmas classes. Exemplos sintéticos e metadados de erro HTTP ficam separados
de estado e casos de uso em api_examples.py e api_docs.py.

A fachada `integration.public` expõe idempotência, auditoria, eventos e IDs
legados. Os negócios deixam de importar modelos e implementação internos de
Integration. Consultas/gravações legadas de idempotência ficam encapsuladas,
preservando fingerprints ausentes e replay anterior da ativação/encerramento.
A implementação transversal ainda usa SQLAlchemy e permanece em Integration;
não se declara arquitetura hexagonal completa nem implementação movida para
infrastructure. O domínio permanece independente de HTTP e persistência.

O PR29 antigo foi examinado e não foi integrado por causa da base desatualizada e
dos conflitos. A eliminação da consulta duplicada de idempotência foi reaplicada
com um método público proporcional. Não foram incorporadas mudanças gerais de
docstrings ou simplificações sem relação com a estabilização.

Verificação: comparação integral do OpenAPI antes/depois da extração, testes de
comportamento existentes, fronteiras por AST e imports legados por identidade.
Um baseline independente da main 5e344e2 protege operações, status, mídias,
parâmetros e propriedades existentes, além de campos obrigatórios de entrada e
garantias de resposta. Somente as duas diferenças de schema do ADR-003
(InvoiceResponse.status e PaymentInput.amount) têm exceções exatas no fixture.
Esse controle não substitui as caracterizações HTTP, migrações e F1–F3, nem
pretende provar compatibilidade de todo comportamento Python por análise estática.

## Diagramas

Os diagramas abaixo foram adicionados em 2026-10-19 para ilustrar a decisão já
aceita; não alteram o seu conteúdo. Eles descrevem o comportamento implementado
no protótipo (código em `src/archcorp`), com dados sintéticos. Setas cheias são
a ida; setas tracejadas são a volta (resposta ou retorno de chamada).

### Fronteiras após a extração

`main.py` só compõe e opera a aplicação. Cada contexto tem `routes.py` e
`schemas.py` próprios, e os módulos de negócio usam Integration apenas pela
fachada `integration.public`. A importação direta de modelos ou do serviço
interno de Integration por um módulo de negócio é proibida e verificada por
análise de AST nos testes. `archcorp.schemas` (fachada dos imports antigos),
`api_examples.py` e `api_docs.py` foram omitidos para legibilidade.

```mermaid
flowchart LR
  CLI["Cliente HTTP<br/>Swagger, Postman, web"]

  subgraph MAIN["main.py — composição"]
    direction TB
    MW["Middlewares<br/>correlação e métricas"]
    ERR["Tratadores de erro<br/>Problem Details"]
    OPS["Health, métricas,<br/>estado da demo, estáticos"]
    CFG["configure(...)<br/>injeta serviços montados"]
  end

  subgraph NEG["Contextos de negócio"]
    direction TB
    subgraph CRM["crm"]
      CRMR["routes + schemas"] --> CRMS["service"]
    end
    subgraph CT["contracts"]
      CTR["routes + schemas"] --> CTS["service + domain"]
    end
    subgraph FIN["finance"]
      FINR["routes"] --> FINS["service + domain"]
    end
    subgraph SUP["support"]
      SUPR["routes + schemas"] --> SUPS["service + domain"]
    end
    subgraph WF["workflow"]
      WFR["routes"] --> WFS["service"]
    end
  end

  subgraph INT["integration"]
    direction TB
    PUB["public.py<br/>IdempotencyStore · LegacyIdService<br/>audit · enqueue"]
    INTR["routes + schemas<br/>dispatch · failures · reprocess<br/>legacy-ids · operations"]
    INTS["service.py + models.py<br/>internos: outbox, inbox,<br/>auditoria, idempotência, EventDispatcher"]
    PUB --> INTS
    INTR --> INTS
  end

  CLI -->|"ida: /api/v1/..."| MW
  MW -.->|"volta: resposta + X-Correlation-ID"| CLI
  MW --> CRMR & CTR & FINR & SUPR & WFR & INTR

  CRMS -->|"LegacyIdService, audit, enqueue"| PUB
  CTS -->|"IdempotencyStore, audit, enqueue"| PUB
  FINS -->|"IdempotencyStore, audit"| PUB
  SUPS -->|"IdempotencyStore, audit, enqueue"| PUB
  WFS -->|"audit"| PUB
  CTS -. "CustomerReader (ADR-006)" .-> CRMS
  SUPS -. "ContractEntitlementPort" .-> CTS

  CTS -. "proibido: importar modelos ou service interno" .-x INTS

```

### Ida e volta de um comando HTTP (ativação do contrato)

Exemplo com `POST /api/v1/contracts/{id}/activate`. O comando atravessa os
middlewares e o router de Contracts; o caso de uso grava contrato, outbox,
idempotência e auditoria na mesma transação. Na volta, a resposta recebe
`Idempotency-Replayed` no router e `X-Correlation-ID` no middleware. Qualquer
erro volta pelo mesmo caminho, convertido em Problem Details, e a sessão é
fechada sem commit.

```mermaid
sequenceDiagram
  autonumber
  actor CLI as Cliente HTTP
  participant COR as correlation_middleware
  participant MET as metrics_middleware
  participant ERR as Tratadores de erro
  participant RT as contracts.routes
  participant SVC as ContractService
  participant PUB as integration.public
  participant DB as Sessão SQL

  CLI->>COR: POST /api/v1/contracts/{id}/activate<br/>Idempotency-Key, X-Correlation-ID opcional
  opt X-Correlation-ID informado e não é UUID
    COR-->>CLI: volta imediata: 400 Problem Details + X-Correlation-ID gerado
  end
  COR->>COR: correlation_id_var = UUID recebido ou novo
  COR->>MET: call_next
  MET->>RT: roteia para o contexto proprietário
  RT->>RT: valida entrada, require_roles("contracts", "admin"), get_session
  RT->>SVC: activate(session, id, key, correlationId)
  SVC->>PUB: IdempotencyStore.previous("activate_contract:{id}", key)
  PUB->>DB: consulta registro de idempotência
  DB-->>PUB: registro ou nada
  alt chave já usada: replay
    PUB-->>SVC: resposta armazenada
    SVC-->>RT: (resposta, replay = true)
  else primeira execução
    PUB-->>SVC: nada
    SVC->>DB: carrega contrato e valida transição DRAFT → ACTIVE
    SVC->>SVC: cliente elegível via CustomerReader resiliente (ADR-006)
    SVC->>PUB: enqueue("ContractActivated.v1", payload, correlationId)
    PUB->>DB: INSERT outbox (PENDING)
    SVC->>PUB: IdempotencyStore.save_legacy(key, operação, resposta)
    SVC->>PUB: audit(correlationId, "contracts", "activate_contract", "success")
    SVC->>DB: COMMIT único: contrato, reserva, outbox, idempotência, auditoria
    DB-->>SVC: confirmado
    SVC-->>RT: (resposta + eventId, replay = false)
  end
  alt sucesso ou replay
    RT-->>MET: 200 + Idempotency-Replayed: true | false
  else erro de domínio, permissão ou validação
    RT-->>ERR: DomainError, HTTPException ou RequestValidationError
    Note over RT,DB: sessão fechada sem commit: nada é gravado
    ERR-->>MET: Problem Details 403, 404, 409, 422 ou 503 com code e correlationId
  end
  MET-->>COR: contabiliza status e latência
  COR-->>CLI: volta final: resposta + X-Correlation-ID e log estruturado
  Note over COR,CLI: exceção não tratada vira 500 Problem Details no middleware de correlação
```

### Volta assíncrona: outbox, consumidores, retentativa e reprocessamento

O evento gravado na ativação só produz efeitos em Finance e Workflow quando o
despacho é acionado por `POST /api/v1/integration/outbox/dispatch`; não há laço
automático em segundo plano no protótipo. Cada evento roda em savepoint, cada
consumidor registra o `eventId` na inbox e a reentrega não duplica efeitos. A
cópia no RabbitMQ só é publicada quando `RABBITMQ_URL` está configurado.

```mermaid
sequenceDiagram
  autonumber
  actor OP as Operador ou script
  participant IR as integration.routes
  participant D as EventDispatcher
  participant DB as Outbox e inbox
  participant FIN as Finance
  participant WF as Workflow
  participant MQ as RabbitMQ (opcional)

  OP->>IR: POST /api/v1/integration/outbox/dispatch<br/>papel operations ou admin
  IR->>D: dispatch_pending(session)
  D->>DB: lista eventos PENDING por occurredAt
  DB-->>D: eventIds
  loop cada evento, com bloqueio SKIP LOCKED e savepoint
    Note over D,WF: consumidores de ContractActivated.v1, na ordem da composição
    D->>DB: inbox tem (eventId, "finance")?
    alt já processado
      DB-->>D: sim: pula, sem cobrança duplicada
    else novo
      D->>FIN: handle_contract_activated(envelope)
      FIN-->>D: cobrança criada
      D->>DB: INSERT inbox (eventId, "finance")
    end
    D->>DB: inbox tem (eventId, "workflow-preparacao-retirada")?
    alt já processado
      DB-->>D: sim: pula, sem processo duplicado
    else novo
      D->>WF: workflow_contract_activated(envelope)
      WF-->>D: preparação de retirada iniciada
      D->>DB: INSERT inbox (eventId, "workflow-preparacao-retirada")
    end
    D->>MQ: publica envelope, se RABBITMQ_URL
    alt sucesso
      D->>DB: status PUBLISHED e COMMIT
    else falha em consumidor, broker ou commit
      D->>DB: desfaz o savepoint, attempts + 1 e COMMIT da tentativa
      Note over D,DB: attempts ≥ retry_limit (padrão 3) → FAILED,<br/>senão segue PENDING para o próximo despacho
    end
  end
  D-->>IR: { processed, failed }
  IR-->>OP: 200 DispatchResponse + X-Correlation-ID
```

O ciclo de vida do evento na outbox mostra as voltas possíveis. `FAILED` é um
status na tabela de outbox, não uma fila de erro no broker.

```mermaid
stateDiagram-v2
  [*] --> PENDING: enqueue na transação do caso de uso
  PENDING --> PUBLISHED: despacho com sucesso
  PENDING --> PENDING: falha e attempts < retry_limit<br/>(volta no próximo despacho)
  PENDING --> FAILED: falha e attempts ≥ retry_limit
  FAILED --> PENDING: POST /integration/failures/{eventId}/reprocess<br/>auditado, attempts zerado
  PUBLISHED --> [*]
```
