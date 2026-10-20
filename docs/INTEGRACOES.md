# Integrações do Cenário 4

> O estado atual de execução está no [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e no [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

Este documento detalha as três integrações obrigatórias do protótipo. Os diagramas
de sequência estão em `docs/arquitetura/FLUXOS_INTEGRACAO.md`. Requisições,
respostas e eventos completos estão em `docs/EXEMPLOS_API.md`.

## Visão geral

| Fluxo | Origem | Destino | Comunicação principal | Resultado |
|---|---|---|---|---|
| F1 | CRM e canais digitais | Contracts | REST síncrono e porta pública | Reserva/contrato sem recadastro |
| F2 | Contracts | Finance e Workflow | Evento assíncrono | Cobrança e preparação de retirada |
| F3 | Support | Contracts e Workflow | Porta síncrona e evento assíncrono | Chamado com SLA e resolução |

Os nomes CRM, Contracts, Finance, Support e Workflow representam contextos do
monólito modular e também as fronteiras dos sistemas corporativos simulados. Cada
contexto mantém suas regras e seus dados. O contexto Integration mantém
correlação, mapeamentos legados, idempotência, outbox, inbox, auditoria e falhas.

## F1: cliente do CRM para reserva/contrato

| Item exigido | Definição |
|---|---|
| Sistema de origem | CRM, acionado por canais digitais ou equipe comercial |
| Sistema de destino | Contracts |
| Informação compartilhada | Identidade global do cliente e condições da locação negociada |
| Objetivo | Criar um rascunho de contrato de locação a partir do cliente existente, sem recadastrar seus dados |
| Tipo de comunicação | Comando REST/JSON síncrono; consulta interna síncrona por porta pública |
| API ou serviço utilizado | `POST /api/v1/contracts/drafts` e `CustomerReader` |
| Dados enviados | `customerId`, `serviceCode`, `startsOn`, `billing.amount`, `billing.currency`, `billing.cycle` e `slaHours` |
| Dados recebidos | `contractId`, `customerId`, produto de locação, início, cobrança, SLA e estado `DRAFT`; cabeçalhos `X-Correlation-ID` e `Idempotency-Replayed` |
| Tratamento de erros | `400` para correlação inválida, `401` ou `403` para acesso; `422` com lista para validação estrutural ou com mensagem para cliente inexistente, inelegível ou sem consentimento; repetição segura por `Idempotency-Key` |

Contracts consulta o CRM somente por `CustomerReader`. A porta confirma a
existência, a elegibilidade e o consentimento e fornece os dados necessários para
a projeção do contrato. Contracts não acessa tabelas ou modelos internos do CRM.

Antes de criar o rascunho, Contracts procura o par formado pela chave idempotente e
pela operação. Em uma repetição, a API devolve a resposta armazenada, mantém o
mesmo `contractId` e informa `Idempotency-Replayed: true`. Em uma criação nova, a
mesma transação persiste contrato, registro de idempotência e auditoria.

No rascunho a partir da reserva (`POST /api/v1/contracts/reservations/{id}/draft`),
o pedido não tem corpo: Contracts usa o `customerId` e as condições gravadas na
reserva. A impressão digital idempotente desse pedido inclui o `reservationId`
(a operação continua `create_contract_draft`; a separação entre os dois caminhos é feita
pela impressão digital, leitura da regra 11 do ADR-001 registrada aqui): reutilizar a mesma `Idempotency-Key` em outra reserva ou uma
chave já usada em `POST /api/v1/contracts/drafts` retorna `409` com
`IDEMPOTENCY_CONFLICT`, sem criar nem vincular contrato.

O protótipo executa `CustomerReader` dentro do mesmo processo, envolvido pelo
adaptador `ResilientCustomerReader` (ADR-006). `TimeoutError` e `ConnectionError`
são repetidos com atraso exponencial, teto e jitter, até `CRM_READER_MAX_ATTEMPTS`
tentativas (padrão 3) e dentro do prazo total `CRM_READER_TIMEOUT_SECONDS` (padrão
2 s). Cada tentativa falha gera log `WARNING` com o `correlationId`. Ao esgotar, a API
responde `503 SERVICE_UNAVAILABLE` em problem+json, sem gravar reserva, contrato,
vínculo ou chave idempotente; o chamador repete com a mesma `Idempotency-Key`. O
mesmo vale para criação de reserva, rascunho direto e revalidação na ativação.
Outros erros não são repetidos. O prazo limita tentativas e esperas, mas não
interrompe uma leitura no mesmo processo; o corte por chamada cabe ao cliente HTTP
do conector quando o CRM sair do processo. A API não oferece chave para simular a
falha do CRM; o comportamento é verificado com simuladores em
`tests/test_f1_cliente_reserva_contrato.py` e `tests/test_crm_reader_resiliente.py`.

## F2: contrato ativo para faturamento e preparação de retirada

| Item exigido | Definição |
|---|---|
| Sistema de origem | Contracts |
| Sistemas de destino | Finance e Workflow; RabbitMQ recebe uma cópia do evento quando configurado |
| Informação compartilhada | Fato de ativação, identidade do cliente e do contrato, grupo de veículo, vigência, cobrança e SLA |
| Objetivo | Criar a primeira cobrança da locação e iniciar o processo de preparação de retirada após a ativação confirmada |
| Tipo de comunicação | Comando REST síncrono para ativar; evento assíncrono para os efeitos desacoplados |
| API ou serviço utilizado | `POST /api/v1/contracts/{contractId}/activate`, outbox, `ContractActivated.v1` e `POST /api/v1/integration/outbox/dispatch` |
| Dados enviados | Envelope com `eventId`, tipo, versão, horário, correlação, causa, produtor e payload do contrato ativo |
| Dados recebidos | A ativação devolve contrato ativo e `eventId`; o despacho devolve quantidades `processed` e `failed`; consumidores registram a conclusão na inbox e em seus próprios dados |
| Tratamento de erros | `400`, `401`, `403` e `404` na ativação; idempotência HTTP; uma tentativa por despacho; estado `FAILED` ao atingir o limite; consulta e reprocessamento protegidos |

A ativação altera o contrato e grava `ContractActivated.v1` na outbox na mesma
transação. O corpo da resposta inclui o `eventId`. Repetir o comando com a mesma
`Idempotency-Key` devolve esse mesmo evento e não grava outra ativação.

O dispatcher verifica a inbox de cada consumidor. Finance mantém uma primeira cobrança
por contrato e por `eventId`, e Workflow mantém uma instância por tipo e referência. Depois dos
consumidores internos, o dispatcher publica o envelope no RabbitMQ quando
`RABBITMQ_URL` está configurado. Uma publicação concluída muda o evento para
`PUBLISHED`.

Cada chamada a `/api/v1/integration/outbox/dispatch` representa uma tentativa dos
eventos que permanecem `PENDING`. Uma exceção incrementa `attempts` e registra o
motivo. O evento muda para `FAILED` ao alcançar `RETRY_LIMIT`, que vale três por
padrão. O protótipo não agenda tentativas automaticamente e não implementa atraso
exponencial ou jitter.

O operador consulta `GET /api/v1/integration/failures` e, depois de corrigir a
causa, usa `POST /api/v1/integration/failures/{eventId}/reprocess`. O comando muda
o evento para `PENDING` e registra a ação na auditoria. Inbox e restrições únicas
continuam ativas durante o novo despacho. A auditoria guarda o número anterior de
tentativas e o contador `attempts` volta a zero, o que abre uma nova janela de três
tentativas.

## F3: chamado com contrato de locação e SLA

| Item exigido | Definição |
|---|---|
| Sistema de origem | Support, acionado por agente do atendimento e assistência 24h |
| Sistemas de destino | Contracts para elegibilidade e Workflow para o processo de resolução |
| Informação compartilhada | Identificadores de cliente, contrato e produto de locação; categoria, estado, prioridade, SLA e prazo do chamado |
| Objetivo | Confirmar o direito à assistência, aplicar o SLA do contrato de locação e iniciar a resolução |
| Tipo de comunicação | Comando REST, consulta síncrona por porta pública e evento assíncrono |
| API ou serviço utilizado | `POST /api/v1/support/tickets`, `ContractEntitlementPort`, `TicketOpened.v1`, dispatcher, reconciliação individual (`POST /support/tickets/{ticketId}/reconcile`) e em lote (`POST /support/tickets/reconcile-pending`), atribuição, resolução e histórico |
| Dados enviados | Na abertura: `customerId`, `contractId`, `serviceCode`, `category` e `description`; no evento: dados do chamado sem a descrição |
| Dados recebidos | Elegibilidade e `slaHours` de Contracts; chamado com estado, prioridade, SLA, `openedAt`, `dueAt` e `slaStatus`; Workflow registra uma instância de resolução |
| Tratamento de erros | `400`, `401` ou `403` para acesso/correlação; `422` com lista para validação estrutural (inclusive descrição com documento, cartão, telefone, placa ou e-mail) ou com mensagem para combinação inelegível; `PENDING_ENTITLEMENT` quando o adaptador está desativado ou levanta indisponibilidade/timeout; `503` na reconciliação enquanto Contracts não volta; `409 INVALID_STATE` fora da máquina de estados; idempotência na abertura, na resolução e na reconciliação |

Quando o adaptador está disponível, Support consulta Contracts por
`ContractEntitlementPort`. Uma combinação ativa de contrato, cliente e produto de locação
devolve elegibilidade e SLA. Uma combinação inelegível interrompe a abertura com
`422`.

Quando `CONTRACT_ADAPTER_AVAILABLE=false`, ou quando o adaptador levanta
`ContractsUnavailableError` (declarada em `contracts/public.py`), `TimeoutError` ou
`ConnectionError`, Support não descarta a solicitação. Ele cria o chamado em
`PENDING_ENTITLEMENT`, sem SLA nem prazo, registra um log `WARNING` com a
correlação e grava `TicketOpened.v1`. O consumidor de Workflow inicia a resolução
com prazo padrão de 24 horas quando o evento ainda não contém SLA. O adaptador
interno roda no mesmo processo e não tem timeout de rede; a indisponibilidade é
exercitada pela configuração e por simuladores nos testes.

O prazo do chamado é `openedAt` mais o SLA do contrato ativo; a prioridade vem da
categoria e não altera o prazo (premissa do protótipo, sem regra no enunciado). O
relógio é injetado em `TicketService`, o que torna o cálculo determinístico nos
testes. `slaStatus` é calculado a cada leitura e fixado na resolução (`MET` ou
`BREACHED`); não há agendador que publique o vencimento.

Depois que Contracts volta a responder, a reconciliação é explícita:
`POST /api/v1/support/tickets/{ticketId}/reconcile` para um chamado ou
`POST /api/v1/support/tickets/reconcile-pending` para todos os pendentes. Uma
confirmação muda o chamado para `OPEN`, preenche o SLA e calcula o prazo a partir
da abertura. Uma rejeição muda o estado para `REJECTED_ENTITLEMENT`. Cada
chamado reconciliado publica um único `TicketEntitlementReconciled.v1`, ganha uma
entrada no histórico e na auditoria; repetir a operação não produz novo efeito, e
a atualização é condicionada ao estado lido para que execuções concorrentes não
dupliquem o evento. Enquanto Contracts não responde, a reconciliação devolve `503`
e o chamado continua pendente. A reconciliação não publica um segundo
`TicketOpened.v1`.

Atribuição, reatribuição e resolução ficam em Support, com histórico próprio
(`support_ticket_history`) e auditoria. O histórico guarda o papel que autorizou a
ação, nunca o token. A resolução repetida devolve o mesmo chamado sem publicar
outro `TicketResolved.v1`.

A descrição do chamado permanece no banco de Support. Ela não entra no evento, nos
logs estruturados ou na resposta da API, o que reduz a exposição de conteúdo
sensível.

## Fluxo auxiliar: propagação cadastral

O CRM publica `CustomerUpdated.v1` depois de alterar nome ou e-mail. Contracts
registra o `eventId` na inbox e atualiza sua projeção local. O CRM continua como
fonte oficial. O consumidor não aplica a estratégia de última escrita vence e não
altera o cadastro proprietário do CRM.

Esse fluxo sustenta o requisito de atualização cadastral, mas não substitui F1, F2
ou F3 entre as três integrações avaliadas.

## Fluxo auxiliar: encerramento, faturamento final e inadimplência (T12)

| Item | Definição |
|---|---|
| Origem | Contracts (`ContractClosed.v1`) e operador financeiro (API Finance) |
| Destino | Finance (consumidor `finance-faturamento-final`), depois do consumidor de Workflow |
| Informação | Contrato, cliente, vigência (`startsOn`, `endsOn`) e cobrança (`amount`, `currency`, `cycle`) do payload público; nenhum dado interno de Contracts |
| Comunicação | Evento assíncrono para a fatura final; REST síncrono para pagamento simulado, verificação de vencimento e cancelamento |
| APIs | `POST /api/v1/finance/invoices/{id}/payments` (`Idempotency-Key` opcional), `POST /api/v1/finance/invoices/overdue-check`, `POST /api/v1/finance/invoices/{id}/cancel`, `GET /api/v1/finance/invoices?contractId=` |
| Erros | `404` fatura inexistente; `409 CONFLICT` sobrepagamento, referência reutilizada ou fatura quitada (códigos da v1; o `detail` da fatura quitada passou a "Fatura já quitada"); `409 INVALID_STATE` fatura cancelada ou cancelamento inválido (caminhos novos); `409 IDEMPOTENCY_CONFLICT`; `422 VALIDATION_ERROR` entrada inválida, inclusive valor com mais de duas casas (antes aceito e arredondado; mudança não aditiva aceita no ADR-003), ou moeda diferente (código da v1); `422 BUSINESS_RULE_VIOLATION` data de referência futura sem simulação |

A fatura final cobra os ciclos iniciados entre `startsOn` e `endsOn` menos o que já
foi faturado ao contrato, inclusive faturas canceladas, cujo cancelamento é
definitivo (premissa a validar). O vencimento é a data UTC do evento mais 10 dias
(premissa a validar; ADR-003). Sem valor a faturar, Finance só audita e grava um
marcador por `eventId`. Ela é única por contrato e por
`eventId`: a inbox descarta a reentrega e, se o registro da inbox se perder, a
unicidade `source_event_id` e a unicidade por contrato e tipo impedem a duplicação.
Sem a primeira fatura, o consumidor falha antes de qualquer escrita; o evento segue
o caminho normal de tentativas, `FAILED` e reprocessamento.

A inadimplência é registrada por comando explícito, não por agendador: a
verificação marca como `OVERDUE` as faturas `OPEN` ou `PARTIALLY_PAID` com
`dueDate` anterior à data UTC de referência, grava `overdueSince` e uma auditoria
por fatura com o `correlationId` da requisição. Repetir o comando não marca de
novo. Na leitura, uma fatura vencida ainda não registrada já aparece como
`OVERDUE`, com `delinquent: false`. Nenhum evento de inadimplência é publicado,
porque nenhum contexto o consome. O pagamento é simulado: não há PSP, conciliação
bancária, nota fiscal nem cobrança real. Uma fatura em aberto com pagamento parcial, antes
`OPEN`, passa a `PARTIALLY_PAID` (mudança não aditiva aceita no ADR-003). Os valores
monetários da v1 seguem como `number`; a representação decimal em string é dívida para a v2.

## Formato e interoperabilidade

- As APIs usam JSON em UTF-8 sob `/api/v1`.
- Identificadores compartilhados usam UUID global gerado pelo contexto
  proprietário; IDs legados ficam mapeados por sistema de origem na tabela
  `integration_legacy_ids` e são resolvidos por
  `GET /api/v1/integration/legacy-ids/{sourceSystem}/{legacyId}`.
- Datas usam ISO 8601. Horários de eventos e prazos usam UTC.
- Valores monetários usam decimal positivo e moeda com três letras.
- Eventos incluem `eventId`, `eventType`, `eventVersion`, `occurredAt`,
  `correlationId`, `causationId`, `producer` e `payload`.
- `correlationId` atravessa HTTP, auditoria, eventos e registros de falha.
- Mudanças incompatíveis exigem nova versão da API ou do evento; mudanças
  compatíveis devem ser aditivas.
- A fonte oficial de cada contexto prevalece. Divergências devem ser registradas
  para análise, sem sobrescrita silenciosa.

O OpenAPI contém as operações, os exemplos REST e as respostas de erro em
`application/problem+json`; ele é gerado por `tools/export_openapi.py` a partir
da aplicação. O AsyncAPI contém todos os eventos publicados pela outbox, os
exemplos de envelope, os consumidores internos e o binding AMQP da exchange
`archcorp.events`. Os testes validam os dois documentos contra seus schemas e
validam os envelopes realmente gravados na outbox contra o AsyncAPI. Os exemplos narrativos reutilizam os mesmos UUIDs
fictícios para demonstrar a continuidade entre os fluxos.

## Contrato de erro

Todas as respostas de erro da API usam `application/problem+json` (RFC 9457),
implementado em `src/archcorp/errors.py` e publicado no OpenAPI como
`ProblemDetails`:

| Campo | Conteúdo |
|---|---|
| `type` | URN estável do problema, por exemplo `urn:archcorp:problem:not-found` |
| `title` | Resumo do status HTTP |
| `status` | Código HTTP |
| `detail` | Mensagem legível; em `422` de validação mantém a lista de erros da versão 1 |
| `instance` | Caminho da requisição |
| `code` | Código estável para o cliente tratar o erro |
| `correlationId` | Mesmo valor do cabeçalho `X-Correlation-ID` |
| `errors` | Lista de erros de validação, presente somente em `VALIDATION_ERROR` |

| Status | `code` | Situação |
|---|---|---|
| 400 | `BAD_REQUEST` | `X-Correlation-ID` que não é UUID; a API gera outro `correlationId` |
| 401 | `UNAUTHORIZED` | Token ausente ou inválido |
| 403 | `FORBIDDEN` | Papel sem permissão |
| 404 | `NOT_FOUND` | Recurso inexistente |
| 409 | `CONFLICT` | Violação de unicidade, como e-mail ou identificador legado repetido |
| 409 | `IDEMPOTENCY_CONFLICT` | `Idempotency-Key` reutilizada com outro conteúdo |
| 409 | `INVALID_STATE` | Transição de estado não permitida |
| 422 | `VALIDATION_ERROR` | Corpo, cabeçalho ou parâmetro inválido |
| 422 | `BUSINESS_RULE_VIOLATION` | Regra de negócio, como cliente sem consentimento |
| 500 | `INTERNAL_ERROR` | Falha inesperada, registrada em log com `correlationId` e sem payload |
| 503 | `SERVICE_UNAVAILABLE` | Banco indisponível em `/health/ready` |

Os casos de uso levantam exceções de `src/archcorp/exceptions.py`, sem depender
de HTTP. A camada de API converte essas exceções, `HTTPException`, erros de
validação e `IntegrityError` do banco no mesmo formato. A mudança é aditiva:
clientes da versão 1 que leem `detail` continuam funcionando.

## Limites do protótipo

Os cinco sistemas são contextos e simuladores do protótipo. Produtos, tecnologias,
interfaces, responsáveis e volumes reais da organização não constam no enunciado
e permanecem como premissas a validar. A troca por sistemas reais deve ocorrer por
adaptadores, preservando os contratos técnicos e as fronteiras descritas neste documento.

### Estabilização v1: privacidade e recuperação da outbox

Erros 422 preservam `detail` e `errors` como listas idênticas, com `type`, `loc`
e `msg`. Por exceção de segurança, não retornam `input`, `ctx` ou mensagens que
possam interpolar dados da entrada; `msg` é genérica, exceto campo obrigatório.
O código `VALIDATION_ERROR`, status e correlação permanecem iguais. Clientes não
devem depender do eco de dados rejeitados. A interface (`describeIssue` em
`web/src/api.ts`) monta o texto pelo `type` e pelo campo em `loc`, sem limites
inventados quando `ctx` não vem; o caso de e-mail é identificado pelo campo.

Cada evento da outbox usa uma transação: todos os consumidores internos e inbox
são confirmados juntos. Consumidores e cópia no broker rodam num SAVEPOINT dentro
da transação que bloqueou o evento (`FOR UPDATE SKIP LOCKED`). Em falha, o
SAVEPOINT desfaz os efeitos parciais e a tentativa é registrada na mesma
transação, sem liberar o bloqueio; os próximos eventos continuam. Só uma falha no
commit final usa transação nova e relê o evento antes de contar a tentativa.
No SQLite, `infrastructure/db.py` faz o pysqlite emitir `BEGIN` explícito, para
que o SAVEPOINT não vire a transação externa. Métrica de falha e log são emitidos
após o commit da tentativa. Ao atingir
`retry_limit`, o evento fica `FAILED`. Reprocessamento preserva inbox e restrições
de negócio. Logs registram somente tipo da exceção, ID e correlação, sem SQL,
parâmetros, traceback ou mensagem da exceção.

A cópia opcional no RabbitMQ usa publisher confirms e `mandatory=True`, dentro do
SAVEPOINT do evento. O despachante declara a fila durável `archcorp.events.all`
ligada à exchange com `#`; mensagem sem rota (`UnroutableError`) ou recusada
(`NackError`) conta como falha da tentativa e o evento não vira `PUBLISHED`.
A entrega ao broker é ao menos uma vez: uma falha depois da confirmação e antes do
commit pode causar nova publicação do mesmo `eventId`. Consumidores externos devem
deduplicar por `eventId`.

Limites da publicação (`config.py`): `rabbitmq_blocked_timeout_seconds` (10 s;
broker que bloqueia publicadores por memória ou disco gera
`ConnectionBlockedTimeout`), `rabbitmq_socket_timeout_seconds` (5 s), heartbeat de
30 s e uma tentativa de conexão. Enquanto publica, o despachante segura o bloqueio
do evento; esses limites devolvem o controle, desfazem os efeitos pelo SAVEPOINT e
registram a tentativa.

Estratégia operacional da fila `archcorp.events.all`: o protótipo não tem consumidor
que a esvazie; ela é a cópia durável para consumidores externos futuros e para
inspeção no console do RabbitMQ. Tem limite `x-max-length`
(`rabbitmq_queue_max_length`, 10.000) com `x-overflow=reject-publish`: cheia, recusa
novas publicações (nack) em vez de descartar as antigas. A recusa conta como falha da
tentativa e, como broker e consumidores internos estão no mesmo SAVEPOINT, o evento
inteiro fica pendente até `retry_limit` e depois `FAILED`, reprocessável após
esvaziar a fila. A métrica `archcorp_broker_queue_messages` (profundidade lida a cada
declaração) permite monitorar o acúmulo. Alterar o limite exige recriar a fila,
porque o RabbitMQ recusa redeclaração com argumentos diferentes.

Fronteira de continuidade: falhas de consumidor ou broker não interrompem o lote.
Se o commit que registra a tentativa também falhar (banco indisponível), a
transação é desfeita, o evento segue `PENDING` com a contagem anterior, o log
`attempt_not_recorded` é emitido sem mensagem da exceção e a falha sobe ao chamador,
interrompendo o lote.

Verificação: `pika` simulado nos testes padrão (ordem das chamadas, limites e falha
em cada etapa) e RabbitMQ 3.13 real no job `rabbitmq` da CI
(`tests/test_rabbitmq_real.py`: publicação confirmada na fila e nack com fila cheia).
