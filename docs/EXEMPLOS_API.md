# Exemplos de APIs e eventos

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

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
simula os papéis de um provedor OIDC e não é uma credencial de produção.

Cabeçalhos comuns:

```http
Authorization: Bearer demo-admin
Content-Type: application/json
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

A API devolve `X-Correlation-ID` nas respostas processadas. Quando o cliente omite
o cabeçalho, o middleware gera um UUID. Um valor que não seja UUID recebe `400`.
Os comandos repetíveis também exigem `Idempotency-Key`.

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
    "reason": "dependência simulada indisponível",
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
  "dueAt": "2026-10-01T18:10:00Z"
}
```

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
    "dueAt": "2026-10-01T18:10:00Z"
  }
}
```

Repita a abertura com `Idempotency-Key: demo-ticket-001`. A resposta mantém o
mesmo `ticketId`, devolve `Idempotency-Replayed: true` e não cria outro evento.

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
  "dueAt": null
}
```

O protótipo grava `TicketOpened.v1` também nesse estado. Workflow inicia a resolução
com prazo operacional padrão de 24 horas porque o SLA ainda não está disponível.

Depois que Contracts volta a responder, reconcilie o chamado:

```http
POST /api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/reconcile HTTP/1.1
Authorization: Bearer demo-admin
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

Se a elegibilidade for confirmada, a resposta `200 OK` muda o estado para `OPEN`,
preenche `slaHours` e recalcula `dueAt`. Se a combinação continuar inelegível, o
estado passa para `REJECTED_ENTITLEMENT` e os campos de SLA permanecem nulos.

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

`POST /api/v1/contracts/reservations/{reservationId}/draft` com
`Idempotency-Key` cria o rascunho do contrato usando os dados da reserva e devolve
`{"reservationId": "...", "contract": {...}}`. A reserva passa a `DRAFTED` e
acompanha a ativação (`ACTIVE`) e o encerramento (`CLOSED`) do contrato.

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
