# Exemplos de APIs e eventos

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
  "name": "Empresa Exemplo Ltda.",
  "email": "contato@empresa-exemplo.test",
  "eligible": true,
  "consentService": true,
  "legacyId": "CRM-1001"
}
```

Resposta `201 Created`:

```http
X-Correlation-ID: 11111111-1111-4111-8111-111111111111
```

```json
{
  "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "name": "Empresa Exemplo Ltda.",
  "email": "contato@empresa-exemplo.test",
  "eligible": true
}
```

O CRM mantém o cadastro oficial. O identificador legado `CRM-1001` fica associado
ao `customerId` global no contexto de integração.

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
  "serviceCode": "SUPPORT-PREMIUM",
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
  "serviceCode": "SUPPORT-PREMIUM",
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

Cliente inexistente, inelegível ou sem consentimento, resposta `422`:

```json
{
  "detail": "Cliente inexistente ou inelegível"
}
```

Um corpo estruturalmente inválido também recebe `422`, mas usa a lista padrão de
erros de validação do FastAPI. Exemplo com `customerId` inválido:

```json
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["body", "customerId"],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ]
}
```

Token ausente ou desconhecido, resposta `401`:

```json
{
  "detail": "Token ausente ou inválido"
}
```

Papel sem acesso à operação, resposta `403`:

```json
{
  "detail": "Papel sem permissão para esta operação"
}
```

Cabeçalho de correlação inválido, resposta `400`:

```json
{
  "detail": "X-Correlation-ID deve ser UUID"
}
```

## F2: ativação, cobrança e onboarding

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
  "serviceCode": "SUPPORT-PREMIUM",
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
    "serviceCode": "SUPPORT-PREMIUM",
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

Finance registra uma cobrança, Workflow inicia um onboarding e cada consumidor
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

O reprocessamento preserva o número anterior de tentativas na auditoria. Ele altera
o estado de entrega, mas não zera o contador acumulado nem desativa inbox,
idempotência ou restrições de negócio. Portanto, uma nova falha após o
reprocessamento devolve o evento imediatamente a `FAILED`; uma nova janela de três
tentativas exigiria uma mudança explícita na política e na implementação.

Contrato desconhecido na ativação, resposta `404`:

```json
{
  "detail": "Contrato não encontrado"
}
```

## F3: chamado com contrato e SLA

### Consultar a elegibilidade

Support usa a porta pública `ContractEntitlementPort`. A representação HTTP
equivalente é:

```http
GET /api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/entitlement?customerId=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa&serviceCode=SUPPORT-PREMIUM HTTP/1.1
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
  "serviceCode": "SUPPORT-PREMIUM",
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
  "serviceCode": "SUPPORT-PREMIUM",
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
    "serviceCode": "SUPPORT-PREMIUM",
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
  "detail": "Contrato, serviço ou cliente sem elegibilidade"
}
```

Um UUID inválido no corpo também recebe `422` com a lista de validação estrutural:

```json
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["body", "contractId"],
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
  "serviceCode": "SUPPORT-PREMIUM",
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
  validação automática dos contratos e dos três fluxos.
