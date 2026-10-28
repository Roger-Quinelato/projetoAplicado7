# Exemplos de APIs e eventos

> O estado atual de execução está no [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e no [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

Este documento apresenta exemplos coerentes para os três fluxos do Cenário 4.
Os contratos executáveis permanecem em `docs/api/openapi.yaml` e
`docs/events/asyncapi.yaml`. Os UUIDs abaixo são fictícios e permanecem fixos para
facilitar a leitura. A aplicação gera outros UUIDs durante a execução.

## Dados usados nos exemplos

| Dado | Valor fictício |
|---|---|
| `correlationId` | `11111111-1111-4111-8111-111111111111` |
| `customerId` | `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` |
| `contractId` | `bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb` |
| Evento de ativação | `cccccccc-cccc-4ccc-8ccc-cccccccccccc` |
| `ticketId` | `dddddddd-dddd-4ddd-8ddd-dddddddddddd` |
| Evento de chamado | `eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee` |

As chamadas protegidas da demonstração usam o token local `demo-admin`. Esse token
é mapeado a papéis locais; não há OIDC/OAuth ou provedor de identidade.
No modo público, use o segredo configurado em `DEMO_ACCESS_TOKEN`, que concede
todos os papéis por uma credencial compartilhada, sem contas individuais.

Cabeçalhos comuns:

```http
Authorization: Bearer demo-admin
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

A API devolve `X-Correlation-ID` nas respostas processadas. Quando o cliente omite
o cabeçalho, o middleware gera um UUID. Um valor que não seja UUID recebe `400`.
`Idempotency-Key` é obrigatória nos rascunhos, na ativação e na abertura do chamado;
reserva, encerramento, resolução e reconciliação individual também aceitam
execução sem chave, conforme o contrato de cada rota.

## F1: cliente do CRM para contrato

### Criar o cliente no CRM

Requisição de preparação:

```http
POST /api/v1/crm/customers HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111

{
  "name": "Cliente Frota Localiza Ltda.",
  "email": "gestor.frota@cliente-sintetico.example.com",
  "eligible": true,
  "consentService": true,
  "legacyId": "WEB-LOCALIZA-1001"
}
```

Resposta `201 Created`:

```http
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

```json
{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "name": "Cliente Frota Localiza Ltda.",
  "email": "gestor.frota@cliente-sintetico.example.com",
  "eligible": true,
  "consentService": true,
  "legacyId": "WEB-LOCALIZA-1001"
}
```

O CRM mantém o cadastro oficial. O identificador legado `WEB-LOCALIZA-1001` fica associado
ao `customerId` global no contexto de integração e pode ser resolvido por
`GET /api/v1/integration/legacy-ids/CRM/WEB-LOCALIZA-1001`, que devolve
`entityType`, `globalId`, `sourceSystem` e `legacyId`. Um e-mail ou identificador
legado já cadastrado recebe `409` com código `CONFLICT`.

### Criar o rascunho do contrato

Requisição:

```http
POST /api/v1/contracts/drafts HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
Idempotency-Key: demo-contract-001

{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "serviceCode": "RENTAL-FLEX",
  "startsOn": "2026-10-01",
  "billing": {
    "amount": 2500.00,
    "currency": "BRL",
    "cycle": "MONTHLY"
  },
  "slaHours": 8
}
```

Resposta `201 Created`:

```http
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
Idempotency-Replayed: false
```

```json
{
  "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "serviceCode": "RENTAL-FLEX",
  "startsOn": "2026-10-01",
  "billing": {
    "amount": 2500.00,
    "currency": "BRL",
    "cycle": "MONTHLY"
  },
  "slaHours": 8,
  "status": "DRAFT"
}
```

### Repetir com idempotência

Repita exatamente a criação do rascunho com
`Idempotency-Key: demo-contract-001`. A resposta mantém o mesmo corpo e o mesmo
`contractId`. O cabeçalho muda para:

```http
Idempotency-Replayed: true
```

### Erros de F1

Todos os erros usam o contrato único `application/problem+json` (RFC 9457),
descrito em [INTEGRACOES.md](INTEGRACOES.md#contrato-de-erro). `code` é estável
para tratamento automático; `correlationId` repete o cabeçalho `X-Correlation-ID`.

Cliente inexistente, inelegível ou sem consentimento, resposta `422`:

```json
{
  "type": "urn:archcorp:problem:business-rule-violation",
  "title": "Entrada inválida",
  "status": 422,
  "detail": "Cliente inexistente ou inelegível",
  "instance": "/api/v1/contracts/drafts",
  "code": "BUSINESS_RULE_VIOLATION",
  "correlationId": "11111111-1111-4111-8111-111111111111"
}
```

Um corpo estruturalmente inválido também recebe `422` com código `VALIDATION_ERROR`.
Para manter compatibilidade com a versão 1, `detail` continua sendo a lista de erros
do FastAPI; a mesma lista aparece em `errors`. Exemplo com `customerId` inválido:

```json
{
  "type": "urn:archcorp:problem:validation-error",
  "title": "Entrada inválida",
  "status": 422,
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": [
        "body",
        "customerId"
      ],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ],
  "instance": "/api/v1/contracts/drafts",
  "code": "VALIDATION_ERROR",
  "correlationId": "11111111-1111-4111-8111-111111111111",
  "errors": [
    {
      "type": "uuid_parsing",
      "loc": [
        "body",
        "customerId"
      ],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ]
}
```

Token ausente ou desconhecido, resposta `401`:

```json
{
  "type": "urn:archcorp:problem:unauthorized",
  "title": "Não autenticado",
  "status": 401,
  "detail": "Token ausente ou inválido",
  "instance": "/api/v1/contracts/drafts",
  "code": "UNAUTHORIZED",
  "correlationId": "11111111-1111-4111-8111-111111111111"
}
```

Papel sem acesso à operação, resposta `403`:

```json
{
  "type": "urn:archcorp:problem:forbidden",
  "title": "Acesso negado",
  "status": 403,
  "detail": "Papel sem permissão para esta operação",
  "instance": "/api/v1/contracts/drafts",
  "code": "FORBIDDEN",
  "correlationId": "11111111-1111-4111-8111-111111111111"
}
```

Cabeçalho de correlação inválido, resposta `400`. Como o valor recebido não é UUID,
a API gera outro `correlationId` e o devolve no corpo e em `X-Correlation-ID`:

```json
{
  "type": "urn:archcorp:problem:bad-request",
  "title": "Requisição inválida",
  "status": 400,
  "detail": "X-Correlation-ID deve ser UUID",
  "instance": "/api/v1/contracts/drafts",
  "code": "BAD_REQUEST",
  "correlationId": "22222222-2222-4222-8222-222222222222"
}
```

## F2: ativação da locação, cobrança e preparação de retirada

### Ativar o contrato

Requisição sem corpo:

```http
POST /api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/activate HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
Idempotency-Key: demo-activate-001
```

Resposta `200 OK`:

```http
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
Idempotency-Replayed: false
```

```json
{
  "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "serviceCode": "RENTAL-FLEX",
  "startsOn": "2026-10-01",
  "billing": {
    "amount": 2500.00,
    "currency": "BRL",
    "cycle": "MONTHLY"
  },
  "slaHours": 8,
  "status": "ACTIVE",
  "eventId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
}
```

A transação grava o contrato ativo, a auditoria e o evento na outbox. O dispatcher
monta o seguinte envelope `ContractActivated.v1`:

```json
{
  "eventId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "eventType": "ContractActivated.v1",
  "eventVersion": 1,
  "occurredAt": "2026-10-01T10:00:00Z",
  "correlationId": "11111111-1111-4111-8111-111111111111",
  "causationId": null,
  "producer": "contracts",
  "payload": {
    "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "serviceCode": "RENTAL-FLEX",
    "startsOn": "2026-10-01",
    "billing": {
      "amount": 2500.00,
      "currency": "BRL",
      "cycle": "MONTHLY"
    },
    "slaHours": 8,
    "status": "ACTIVE"
  }
}
```

### Despachar a outbox

Requisição sem corpo:

```http
POST /api/v1/integration/outbox/dispatch HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Resposta `200 OK` quando um evento é publicado:

```json
{
  "processed": 1,
  "failed": 0
}
```

Finance registra uma cobrança, Workflow inicia uma preparação de retirada e cada consumidor
registra o `eventId` na inbox. Um novo despacho sem eventos pendentes devolve
`{"processed": 0, "failed": 0}`.

### Consultar o resumo da outbox

```http
GET /api/v1/integration/outbox/summary HTTP/1.1
Authorization: Bearer demo-operations
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Resposta `200 OK` antes do despacho acima:

```json
{
  "pending": 1,
  "failed": 0
}
```

`pending` conta eventos `PENDING` e `failed` conta eventos `FAILED`, que já
esgotaram as tentativas. Perfis sem `operations` ou `admin` recebem `403 FORBIDDEN`.

### Repetir com idempotência

Repita a ativação com `Idempotency-Key: demo-activate-001`. A API devolve o mesmo
`eventId` e `Idempotency-Replayed: true`. Ela não grava outro evento. A inbox e as
restrições únicas também impedem efeitos duplicados caso um evento seja entregue
novamente.

### Falha de despacho e reprocessamento

Cada chamada ao dispatcher representa uma tentativa. Quando o número de tentativas
alcança o limite configurado, três por padrão, o evento recebe o estado `FAILED`.
O protótipo não implementa agendamento nem atraso exponencial entre tentativas.

Resposta ilustrativa de `GET /api/v1/integration/failures`:

```json
[
  {
    "eventId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    "eventType": "ContractActivated.v1",
    "attempts": 3,
    "reason": "Falha no despacho do evento; consulte a correlação e reprocesse após corrigir a causa",
    "correlationId": "11111111-1111-4111-8111-111111111111"
  }
]
```

Após corrigir a causa, o operador agenda o reprocessamento:

```http
POST /api/v1/integration/failures/cccccccc-cccc-4ccc-8ccc-cccccccccccc/reprocess HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Resposta `200 OK`:

```json
{
  "eventId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "status": "PENDING"
}
```

O reprocessamento registra o número anterior de tentativas na auditoria
(`previousAttempts`), zera o contador `attempts` e devolve o evento a `PENDING`.
O evento ganha uma nova janela de três tentativas. Inbox, idempotência e restrições
de negócio continuam ativas, portanto consumidores que já processaram o `eventId`
não repetem o efeito.

Contrato desconhecido na ativação, resposta `404`:

```json
{
  "type": "urn:archcorp:problem:not-found",
  "title": "Recurso não encontrado",
  "status": 404,
  "detail": "Contrato não encontrado",
  "instance": "/api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/activate",
  "code": "NOT_FOUND",
  "correlationId": "11111111-1111-4111-8111-111111111111"
}
```

## F3: chamado com contrato de locação e SLA

### Consultar a elegibilidade

Support usa a porta pública `ContractEntitlementPort`. A representação HTTP
equivalente é:

```http
GET /api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/entitlement?customerId=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa&serviceCode=RENTAL-FLEX HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Resposta `200 OK` para contrato ativo e compatível:

```json
{
  "eligible": true,
  "slaHours": 8
}
```

Uma combinação sem contrato ativo devolve `200 OK` com
`{"eligible": false, "slaHours": null}`.

### Abrir o chamado

Requisição:

```http
POST /api/v1/support/tickets HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
Idempotency-Key: demo-ticket-001

{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "serviceCode": "RENTAL-FLEX",
  "category": "OUTAGE",
  "description": "Serviço indisponível durante a demonstração"
}
```

Resposta `201 Created`:

```http
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
Idempotency-Replayed: false
```

```json
{
  "ticketId": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "serviceCode": "RENTAL-FLEX",
  "category": "OUTAGE",
  "status": "OPEN",
  "priority": "HIGH",
  "slaHours": 8,
  "dueAt": "2026-10-01T18:10:00Z",
  "openedAt": "2026-10-01T10:10:00Z",
  "resolvedAt": null,
  "slaStatus": "WITHIN"
}
```

`dueAt` é `openedAt` mais o SLA do contrato ativo (T15). `priority` é calculada pela
categoria: `OUTAGE` e `SECURITY` recebem `HIGH`; as demais, `NORMAL`. `slaStatus` é
calculado no instante da resposta: `PENDING` (sem elegibilidade), `WITHIN` ou
`BREACHED` (aberto), `MET` ou `BREACHED` (resolvido) e `NOT_APPLICABLE` (rejeitado).

A descrição permanece em Support e não aparece no evento. O dispatcher publica:

```json
{
  "eventId": "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  "eventType": "TicketOpened.v1",
  "eventVersion": 1,
  "occurredAt": "2026-10-01T10:10:00Z",
  "correlationId": "11111111-1111-4111-8111-111111111111",
  "causationId": null,
  "producer": "support",
  "payload": {
    "ticketId": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
    "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "serviceCode": "RENTAL-FLEX",
    "category": "OUTAGE",
    "status": "OPEN",
    "priority": "HIGH",
    "slaHours": 8,
    "dueAt": "2026-10-01T18:10:00Z",
    "openedAt": "2026-10-01T10:10:00Z",
    "resolvedAt": null,
    "slaStatus": "WITHIN"
  }
}
```

Repita a abertura com `Idempotency-Key: demo-ticket-001`. A resposta mantém o
mesmo `ticketId`, devolve `Idempotency-Replayed: true` e não cria outro evento. A
impressão digital da chave inclui todos os campos do pedido, inclusive a
descrição: a mesma chave com outro conteúdo recebe `409 IDEMPOTENCY_CONFLICT`.

A descrição deve conter somente dados sintéticos, sem documento, cartão,
telefone, placa ou e-mail. A API valida o tamanho (3 a 2000 caracteres), mas não
inspeciona esses conteúdos; essa restrição é responsabilidade de quem demonstra.

Contrato, cliente ou serviço sem elegibilidade, resposta `422`:

```json
{
  "type": "urn:archcorp:problem:business-rule-violation",
  "title": "Entrada inválida",
  "status": 422,
  "detail": "Contrato, serviço ou cliente sem elegibilidade",
  "instance": "/api/v1/support/tickets",
  "code": "BUSINESS_RULE_VIOLATION",
  "correlationId": "11111111-1111-4111-8111-111111111111"
}
```

Um UUID inválido no corpo também recebe `422` com a lista de validação estrutural:

```json
{
  "type": "urn:archcorp:problem:validation-error",
  "title": "Entrada inválida",
  "status": 422,
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": [
        "body",
        "contractId"
      ],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ],
  "instance": "/api/v1/support/tickets",
  "code": "VALIDATION_ERROR",
  "correlationId": "11111111-1111-4111-8111-111111111111",
  "errors": [
    {
      "type": "uuid_parsing",
      "loc": [
        "body",
        "contractId"
      ],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ]
}
```

### Indisponibilidade e reconciliação

Quando o adaptador de Contracts está desabilitado, Support preserva a solicitação:

```json
{
  "ticketId": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "serviceCode": "RENTAL-FLEX",
  "category": "QUESTION",
  "status": "PENDING_ENTITLEMENT",
  "priority": "NORMAL",
  "slaHours": null,
  "dueAt": null,
  "openedAt": "2026-10-01T10:10:00Z",
  "resolvedAt": null,
  "slaStatus": "PENDING"
}
```

O mesmo estado é usado quando o adaptador de Contracts levanta
`ContractsUnavailableError`, `TimeoutError` ou `ConnectionError`; a API registra um
log `WARNING` com `operation: support_entitlement`, `result: unavailable` e o
`correlationId`, sem a descrição.

O protótipo grava `TicketOpened.v1` também nesse estado. Workflow inicia a resolução
com prazo operacional padrão de 24 horas porque o SLA ainda não está disponível.

Depois que Contracts volta a responder, reconcilie o chamado:

```http
POST /api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/reconcile HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Se a elegibilidade for confirmada, a resposta `200 OK` muda o estado para `OPEN`,
preenche `slaHours` e calcula `dueAt` a partir de `openedAt`: o tempo em que
Contracts ficou indisponível não estende o SLA. Se a combinação continuar
inelegível, o estado passa para `REJECTED_ENTITLEMENT`, `slaStatus` vira
`NOT_APPLICABLE` e os campos de SLA permanecem nulos. Com a mesma `Idempotency-Key` opcional, repetir devolve `200` com a resposta
original persistida e `Idempotency-Replayed: true`, sem novo evento. Sem chave,
repetir após reconciliação retorna `409 INVALID_STATE`.

Se Contracts ainda estiver indisponível, a resposta é `503` e o chamado continua
pendente:

```json
{
  "type": "urn:archcorp:problem:service-unavailable",
  "title": "Dependência indisponível",
  "status": 503,
  "detail": "Contracts indisponível; o chamado permanece em PENDING_ENTITLEMENT",
  "instance": "/api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/reconcile",
  "code": "SERVICE_UNAVAILABLE",
  "correlationId": "11111111-1111-4111-8111-111111111111"
}
```

### Reconciliar todos os pendentes

Operação explícita (papéis `support`, `operations` e `admin`); não há agendador:

```http
POST /api/v1/support/tickets/reconcile-pending?limit=100 HTTP/1.1
Authorization: Bearer demo-operations
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Resposta `200 OK`:

```json
{
  "confirmed": 1,
  "rejected": 1,
  "remaining": 0,
  "contractsAvailable": true,
  "tickets": [
    {"ticketId": "dddddddd-dddd-4ddd-8ddd-dddddddddddd", "status": "OPEN", "slaHours": 8, "dueAt": "2026-10-01T18:10:00Z", "slaStatus": "WITHIN", "...": "demais campos do chamado"},
    {"ticketId": "eeeeeeee-1111-4eee-8eee-eeeeeeeeeeee", "status": "REJECTED_ENTITLEMENT", "slaHours": null, "dueAt": null, "slaStatus": "NOT_APPLICABLE", "...": "demais campos do chamado"}
  ]
}
```

Cada chamado é confirmado em sua própria transação, com evento, histórico e
auditoria. Repetir a operação só consulta os que continuam pendentes. Se Contracts
cair no meio do lote, a resposta traz `contractsAvailable: false` e `remaining > 0`;
se estiver indisponível desde o início, a resposta é `503` sem alteração.

### Atribuir, reatribuir e consultar o histórico

```http
POST /api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/assign HTTP/1.1
Authorization: Bearer demo-support
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111

{"owner": "Equipe de assistência"}
```

O responsável deve representar uma equipe ou função (2 a 80 caracteres); use
somente dados sintéticos. A v1 não usa regex para rejeitar conteúdo. Repetir o mesmo responsável não altera o histórico; outro valor gera
`REASSIGNED`. Chamado resolvido ou rejeitado recebe `409 CONFLICT`.

```http
GET /api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/history HTTP/1.1
Authorization: Bearer demo-operations
```

```json
[
  {"occurredAt": "2026-10-01T10:10:00Z", "action": "OPENED", "fromStatus": null, "toStatus": "OPEN", "owner": null, "previousOwner": null, "actorRole": "support", "slaStatus": "WITHIN", "correlationId": "11111111-1111-4111-8111-111111111111"},
  {"occurredAt": "2026-10-01T10:20:00Z", "action": "ASSIGNED", "fromStatus": "OPEN", "toStatus": "OPEN", "owner": "Equipe de assistência", "previousOwner": null, "actorRole": "support", "slaStatus": "WITHIN", "correlationId": "11111111-1111-4111-8111-111111111111"},
  {"occurredAt": "2026-10-01T11:00:00Z", "action": "REASSIGNED", "fromStatus": "OPEN", "toStatus": "OPEN", "owner": "Equipe de pátio", "previousOwner": "Equipe de assistência", "actorRole": "admin", "slaStatus": "WITHIN", "correlationId": "11111111-1111-4111-8111-111111111111"},
  {"occurredAt": "2026-10-01T12:10:00Z", "action": "RESOLVED", "fromStatus": "OPEN", "toStatus": "RESOLVED", "owner": "Equipe de pátio", "previousOwner": null, "actorRole": "support", "slaStatus": "MET", "correlationId": "11111111-1111-4111-8111-111111111111"}
]
```

`actorRole` registra o papel que autorizou a operação, nunca o token.

### Resolver

`POST /api/v1/support/tickets/{ticketId}/resolve` aceita somente chamado `OPEN`,
grava `resolvedAt`, fixa `slaStatus` em `MET` ou `BREACHED` e publica um único
`TicketResolved.v1`. Com a mesma `Idempotency-Key` opcional, repetir devolve
`200` com a resposta persistida e `Idempotency-Replayed: true`. Sem chave,
chamado resolvido, pendente ou rejeitado recebe `409 CONFLICT`. O plano não prevê reabertura nem pausa de SLA.

## Operações complementares

Estas operações apoiam os fluxos e seguem os mesmos cabeçalhos comuns. O OpenAPI
traz o schema e um exemplo de resposta para cada uma.

### Reserva e rascunho a partir da reserva

```http
POST /api/v1/contracts/reservations HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111

{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "vehicleGroup": "SUV-COMPACTO",
  "protectionCode": "BASICA",
  "serviceCode": "RENTAL-FLEX",
  "startsOn": "2027-01-04",
  "endsOn": "2027-01-08",
  "amount": 750.00,
  "currency": "BRL",
  "billingCycle": "ONCE",
  "slaHours": 8
}
```

Resposta `201 Created` com `reservationId`, os mesmos campos e `status`
`REQUESTED`. Um cliente sem consentimento recebe `422` com código
`BUSINESS_RULE_VIOLATION`.

A criação aceita `Idempotency-Key` opcional: a mesma chave com o mesmo corpo devolve
a mesma reserva com `Idempotency-Replayed: true`; com outro corpo, `409`
`IDEMPOTENCY_CONFLICT`. Início no passado, fim anterior ao início, moeda fora do
padrão `^[A-Z]{3}$` ou valor com mais de duas casas recebem `422`.

`POST /api/v1/contracts/reservations/{reservationId}/draft` com
`Idempotency-Key` cria o rascunho do contrato usando os dados da reserva, inclusive
`endsOn`, e devolve `{"reservationId": "...", "contract": {...}}` na mesma
transação que vincula a reserva. A reserva passa a `DRAFTED` e acompanha a
ativação (`ACTIVE`) e o encerramento (`CLOSED`) do contrato.
`vehicleGroup` e `protectionCode` permanecem na reserva: não são copiados para
o contrato nem retornados na elegibilidade, limitada a `eligible` e `slaHours`.
Não há alocação de frota, PSP ou integração corporativa real nesses exemplos.
`POST /api/v1/contracts/reservations/{reservationId}/cancel` cancela uma reserva
`REQUESTED` ou `DRAFTED`; o rascunho vinculado passa a `CANCELLED`.

### Encerrar o contrato

```http
POST /api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/close HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json
Idempotency-Key: demo-close-001
X-Correlation-ID: 11111111-1111-4111-8111-111111111111

{
  "endsOn": "2027-01-08",
  "reason": "Devolução do veículo"
}
```

Resposta `200 OK`:

```json
{
  "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "serviceCode": "RENTAL-FLEX",
  "startsOn": "2026-10-01",
  "endsOn": "2027-01-08",
  "billing": {
    "amount": 2500.0,
    "currency": "BRL",
    "cycle": "MONTHLY"
  },
  "slaHours": 8,
  "status": "CLOSED",
  "eventId": "18181818-1818-4181-8181-181818181818"
}
```

O corpo é opcional; sem `endsOn`, a data é a atual ou o início do contrato, o que
for posterior. O encerramento publica `ContractClosed.v1`. Repetir com a mesma
chave devolve a mesma resposta. Já encerrado, o contrato também devolve a
resposta original quando há chave; sem chave, repetir recebe `409`.
Outros estados que não sejam `ACTIVE` recebem `409 INVALID_STATE`.

### Contatos e oportunidades do CRM

```http
POST /api/v1/crm/contacts HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json

{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "name": "Pessoa Gestora Sintética",
  "email": "gestora@cliente-sintetico.example.com",
  "phone": "+5531999990000"
}
```

```http
POST /api/v1/crm/opportunities HTTP/1.1
Authorization: Bearer demo-admin
Content-Type: application/json

{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "title": "Renovação de frota 2027",
  "notes": "Proposta de 20 veículos compactos"
}
```

As duas respostas `201 Created` devolvem o identificador gerado (`contactId` ou
`opportunityId`). Um `customerId` inexistente recebe `404`.

`PATCH /api/v1/crm/opportunities/{opportunityId}` com `{"status": "WON"}` fecha a
oportunidade. `WON` e `LOST` são finais: uma nova mudança recebe `409` com código
`INVALID_STATE`. `POST /api/v1/crm/customers/{customerId}/deactivate` inativa o
cliente sem apagar o histórico; a partir daí ele não origina reserva nem contrato.

### Identificador legado

```http
GET /api/v1/integration/legacy-ids/CRM/WEB-LOCALIZA-1001 HTTP/1.1
Authorization: Bearer demo-admin
```

Resposta `200 OK`:

```json
{
  "entityType": "customer",
  "globalId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "sourceSystem": "CRM",
  "legacyId": "WEB-LOCALIZA-1001"
}
```

### Resumos dos indicadores da Visão geral

Os indicadores da Visão geral usam contagens feitas no servidor. As listagens
continuam limitadas a 200 itens e não servem para contar. Cada resumo exige os
mesmos papéis da listagem do seu contexto (`403 FORBIDDEN` fora deles).

```http
GET /api/v1/contracts/summary HTTP/1.1
Authorization: Bearer demo-contracts
```

```json
{ "total": 240, "active": 180 }
```

```http
GET /api/v1/finance/invoices/summary HTTP/1.1
Authorization: Bearer demo-finance
```

```json
{ "receivable": 3, "balances": [{ "currency": "BRL", "amount": 3100.0 }] }
```

`receivable` conta as faturas abertas, parcialmente pagas ou vencidas com saldo
positivo. `balances` soma esse saldo (valor menos pagamentos) por moeda.

```http
GET /api/v1/support/tickets/summary HTTP/1.1
Authorization: Bearer demo-support
```

```json
{ "open": 12, "withinSla": 9 }
```

`withinSla` usa a mesma regra do `slaStatus` da leitura: chamados `OPEN` com
prazo ainda não vencido no instante da consulta.

```http
GET /api/v1/workflow/processes/summary HTTP/1.1
Authorization: Bearer demo-operations
```

```json
{ "total": 250, "running": 40 }
```

`running` exclui os estados finais `COMPLETED` e `CANCELLED`.

## Consultar a correlação

Use o mesmo UUID da operação:

```http
GET /api/v1/operations/11111111-1111-4111-8111-111111111111 HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Resposta `200 OK` resumida:

```json
{
  "correlationId": "11111111-1111-4111-8111-111111111111",
  "audit": [
    {
      "occurredAt": "2026-10-01T10:00:00Z",
      "module": "contracts",
      "operation": "activate_contract",
      "result": "success",
      "entityId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      "details": {}
    }
  ],
  "events": [
    {
      "eventId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      "eventType": "ContractActivated.v1",
      "status": "PUBLISHED",
      "attempts": 0
    }
  ]
}
```

O resultado real inclui todas as auditorias e todos os eventos gravados com a
correlação informada.

## Regras de consistência dos exemplos

- Use datas e horas em ISO 8601; eventos e `dueAt` usam UTC.
- Use moeda com código de três letras e valor decimal positivo.
- Preserve os UUIDs globais em todas as chamadas do mesmo cenário.
- Não envie descrição de chamado, token, documento ou dado bancário em eventos e
  logs.
- Trate os exemplos de falha como estados operacionais. Eles não substituem a
  validação automática dos contratos técnicos e dos três fluxos.
