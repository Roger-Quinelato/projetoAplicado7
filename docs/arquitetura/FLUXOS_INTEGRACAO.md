# Fluxos de integração

Os diagramas abaixo representam o comportamento implementado para F1, F2 e F3.
Eles complementam `docs/INTEGRACOES.md` e usam os contratos de
`docs/api/openapi.yaml` e `docs/events/asyncapi.yaml`. Os payloads completos estão
em `docs/EXEMPLOS_API.md`.

## Convenções

- Linha contínua representa chamada ou gravação síncrona.
- Linha tracejada representa resposta.
- Outbox registra o fato junto com a transação de negócio.
- Inbox registra o par formado por `eventId` e consumidor.
- `X-Correlation-ID` acompanha HTTP, auditoria e eventos.
- `Idempotency-Key` identifica uma operação mutável repetível.

## F1: cliente do CRM para contrato

O fluxo cria um rascunho usando o cliente oficial do CRM. A consulta ocorre pela
porta pública `CustomerReader`, sem acesso ao banco ou ao modelo interno do CRM.

```mermaid
sequenceDiagram
    autonumber
    actor Comercial
    participant API as API REST v1
    participant Contracts
    participant Integration
    participant CRM
    participant DB as PostgreSQL

    Comercial->>API: POST /contracts/drafts<br/>Idempotency-Key e X-Correlation-ID
    API->>API: Validar token, papel, correlação e JSON
    API->>Contracts: create_draft(dados, chave, correlação)
    Contracts->>Integration: Buscar chave da operação create_contract_draft

    alt Chave já registrada
        Integration-->>Contracts: Resposta armazenada
        Contracts-->>API: Mesmo contrato
        API-->>Comercial: 201 e Idempotency-Replayed true
    else Nova solicitação
        Contracts->>CRM: CustomerReader.get(customerId)
        CRM-->>Contracts: Cliente, elegibilidade e consentimento
        alt Cliente inexistente, inelegível ou sem consentimento
            Contracts-->>API: Erro de negócio
            API-->>Comercial: 422
        else Cliente elegível
            Contracts->>DB: Gravar contrato DRAFT
            Contracts->>Integration: Gravar idempotência e auditoria
            Integration->>DB: Confirmar a mesma transação
            DB-->>Contracts: Commit
            Contracts-->>API: contractId e contrato canônico
            API-->>Comercial: 201 e Idempotency-Replayed false
        end
    end
```

Erros de autenticação, autorização ou correlação são encerrados na API com `401`,
`403` ou `400`, antes de Contracts executar o caso de uso. O adaptador interno de
CRM não simula indisponibilidade ou timeout neste fluxo.

## F2: ativação, cobrança e onboarding

O fluxo separa a confirmação síncrona da ativação dos efeitos assíncronos em
Finance e Workflow. A ativação e o registro da outbox pertencem à mesma transação.

```mermaid
sequenceDiagram
    autonumber
    actor Contratos as Usuário de contratos
    actor Operador
    participant API as API REST v1
    participant Contracts
    participant Outbox
    participant Dispatcher
    participant Inbox
    participant Finance
    participant Workflow
    participant MQ as RabbitMQ

    Contratos->>API: POST /contracts/{id}/activate<br/>Idempotency-Key e X-Correlation-ID
    API->>Contracts: activate(contractId, chave, correlação)
    Contracts->>Outbox: Buscar chave da operação

    alt Ativação repetida
        Outbox-->>Contracts: Resposta armazenada
        Contracts-->>API: Mesmo contrato e eventId
        API-->>Contratos: 200 e Idempotency-Replayed true
    else Primeira ativação
        Contracts->>Contracts: Alterar estado para ACTIVE
        Contracts->>Outbox: Gravar ContractActivated.v1 e auditoria
        Outbox-->>Contracts: eventId na mesma transação
        Contracts-->>API: Contrato ativo e eventId
        API-->>Contratos: 200 e Idempotency-Replayed false
    end

    Operador->>API: POST /integration/outbox/dispatch
    API->>Dispatcher: dispatch_pending()
    Dispatcher->>Outbox: Selecionar eventos PENDING

    loop Finance e Workflow
        Dispatcher->>Inbox: Verificar eventId e consumidor
        alt Evento já consumido
            Inbox-->>Dispatcher: Ignorar efeito repetido
        else Primeiro consumo
            alt Consumidor Finance
                Dispatcher->>Finance: Criar primeira cobrança
                Finance-->>Dispatcher: Cobrança única por contractId
            else Consumidor Workflow
                Dispatcher->>Workflow: Iniciar onboarding
                Workflow-->>Dispatcher: Processo único por tipo e referência
            end
            Dispatcher->>Inbox: Registrar eventId e consumidor
        end
    end

    opt RABBITMQ_URL configurado
        Dispatcher->>MQ: Publicar ContractActivated.v1 persistente
        MQ-->>Dispatcher: Publicação concluída
    end

    alt Despacho concluído
        Dispatcher->>Outbox: Marcar PUBLISHED
        Dispatcher-->>API: processed 1, failed 0
        API-->>Operador: 200
    else Exceção durante o despacho
        Dispatcher->>Outbox: Incrementar attempts e registrar motivo
        alt attempts menor que RETRY_LIMIT
            Dispatcher-->>API: processed 0, failed 1<br/>Evento continua PENDING
        else attempts igual ou maior que RETRY_LIMIT
            Dispatcher->>Outbox: Marcar FAILED
            Dispatcher-->>API: processed 0, failed 1
            Operador->>API: GET /integration/failures
            API-->>Operador: eventId, motivo, tentativas e correlação
            Operador->>API: POST /integration/failures/{eventId}/reprocess
            API->>Outbox: Marcar PENDING e auditar
            API-->>Operador: 200 e status PENDING
        end
    end
```

Cada chamada ao dispatcher realiza uma tentativa. O protótipo não possui
agendador, atraso exponencial ou jitter. O operador precisa chamar o despacho
novamente após corrigir a causa. A inbox e as restrições únicas permanecem ativas
no reprocessamento.

## F3: chamado com contrato e SLA

Support consulta o contrato pela porta `ContractEntitlementPort`. O estado
pendente preserva a solicitação quando o adaptador está indisponível.

```mermaid
sequenceDiagram
    autonumber
    actor Atendimento
    actor Operador
    participant API as API REST v1
    participant Support
    participant Integration
    participant Contracts
    participant Outbox
    participant Dispatcher
    participant Inbox
    participant Workflow

    Atendimento->>API: POST /support/tickets<br/>Idempotency-Key e X-Correlation-ID
    API->>API: Validar token, papel, correlação e JSON
    API->>Support: open(dados, chave, correlação)
    Support->>Integration: Buscar chave da operação open_ticket

    alt Chave já registrada
        Integration-->>Support: Resposta armazenada
        Support-->>API: Mesmo ticketId
        API-->>Atendimento: 201 e Idempotency-Replayed true
    else Nova solicitação
        alt Adaptador de Contracts indisponível
            Support->>Support: Definir PENDING_ENTITLEMENT<br/>sem SLA e sem dueAt
            Support->>Outbox: Gravar TicketOpened.v1, auditoria e idempotência
            Support-->>API: Chamado pendente
            API-->>Atendimento: 201
        else Adaptador disponível
            Support->>Contracts: ContractEntitlementPort.entitlement(...)
            Contracts-->>Support: eligible e slaHours
            alt Contrato, cliente ou serviço inelegível
                Support-->>API: Erro de negócio
                API-->>Atendimento: 422
            else Elegibilidade confirmada
                Support->>Support: Calcular prioridade e dueAt
                Support->>Outbox: Gravar TicketOpened.v1, auditoria e idempotência
                Support-->>API: Chamado OPEN com SLA
                API-->>Atendimento: 201
            end
        end
    end

    opt Chamado gravado com TicketOpened.v1 pendente
        Operador->>API: POST /integration/outbox/dispatch
        API->>Dispatcher: Despachar TicketOpened.v1 pendente
        Dispatcher->>Inbox: Verificar eventId e consumidor Workflow
        alt Evento ainda não consumido
            Dispatcher->>Workflow: Iniciar processo TICKET_RESOLUTION
            Note over Workflow: Usa slaHours ou 24 horas<br/>quando o chamado está pendente
            Dispatcher->>Inbox: Registrar eventId e consumidor
        else Evento já consumido
            Inbox-->>Dispatcher: Ignorar efeito repetido
        end
        Dispatcher->>Outbox: Marcar PUBLISHED
    end

    opt Chamado em PENDING_ENTITLEMENT e Contracts restabelecido
        Operador->>API: POST /support/tickets/{ticketId}/reconcile
        API->>Support: reconcile(ticketId, correlação)
        Support->>Contracts: Consultar elegibilidade novamente
        Contracts-->>Support: eligible e slaHours
        alt Elegibilidade confirmada
            Support->>Support: Mudar para OPEN e recalcular dueAt
            Support-->>Operador: 200 com SLA
        else Elegibilidade rejeitada
            Support->>Support: Mudar para REJECTED_ENTITLEMENT
            Support-->>Operador: 200 sem SLA
        end
    end
```

`TicketOpened.v1` nunca contém a descrição. A reconciliação atualiza o chamado e a
auditoria, mas não publica outro evento e não recalcula o prazo do processo já
iniciado em Workflow.

## Rastreabilidade operacional

Depois de qualquer fluxo, o operador usa
`GET /api/v1/operations/{correlationId}`. A resposta reúne auditorias e eventos
gravados com a mesma correlação. O endpoint não agrega registros que receberam
outro `X-Correlation-ID`, mesmo quando pertencem à mesma demonstração.

Os diagramas descrevem o protótipo acadêmico. Produtos, interfaces e topologia dos
sistemas reais continuam como premissas a validar com a organização.
