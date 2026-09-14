# Integrações do Cenário 4

Este documento detalha as três integrações obrigatórias do protótipo. Os diagramas
de sequência estão em `docs/arquitetura/FLUXOS_INTEGRACAO.md`. Requisições,
respostas e eventos completos estão em `docs/EXEMPLOS_API.md`.

## Visão geral

| Fluxo | Origem | Destino | Comunicação principal | Resultado |
|---|---|---|---|---|
| F1 | CRM e Comercial | Contracts | REST síncrono e porta pública | Rascunho sem recadastro |
| F2 | Contracts | Finance e Workflow | Evento assíncrono | Cobrança e onboarding |
| F3 | Support | Contracts e Workflow | Porta síncrona e evento assíncrono | Chamado com SLA e resolução |

Os nomes CRM, Contracts, Finance, Support e Workflow representam contextos do
monólito modular e também as fronteiras dos sistemas corporativos simulados. Cada
contexto mantém suas regras e seus dados. O contexto Integration mantém
correlação, mapeamentos legados, idempotência, outbox, inbox, auditoria e falhas.

## F1: cliente do CRM para contrato

| Item exigido | Definição |
|---|---|
| Sistema de origem | CRM, acionado pelo usuário do setor Comercial |
| Sistema de destino | Contracts |
| Informação compartilhada | Identidade global do cliente e condições do serviço negociado |
| Objetivo | Criar um rascunho de contrato a partir do cliente existente, sem recadastrar seus dados |
| Tipo de comunicação | Comando REST/JSON síncrono; consulta interna síncrona por porta pública |
| API ou serviço utilizado | `POST /api/v1/contracts/drafts` e `CustomerReader` |
| Dados enviados | `customerId`, `serviceCode`, `startsOn`, `billing.amount`, `billing.currency`, `billing.cycle` e `slaHours` |
| Dados recebidos | `contractId`, `customerId`, serviço, início, cobrança, SLA e estado `DRAFT`; cabeçalhos `X-Correlation-ID` e `Idempotency-Replayed` |
| Tratamento de erros | `400` para correlação inválida, `401` ou `403` para acesso, `422` para entrada inválida ou cliente inexistente/inelegível; repetição segura por `Idempotency-Key` |

Contracts consulta o CRM somente por `CustomerReader`. A porta confirma a
existência, a elegibilidade e o consentimento e fornece os dados necessários para
a projeção do contrato. Contracts não acessa tabelas ou modelos internos do CRM.

Antes de criar o rascunho, Contracts procura o par formado pela chave idempotente e
pela operação. Em uma repetição, a API devolve a resposta armazenada, mantém o
mesmo `contractId` e informa `Idempotency-Replayed: true`. Em uma criação nova, a
mesma transação persiste contrato, registro de idempotência e auditoria.

O protótipo executa `CustomerReader` dentro do mesmo processo. Ele não simula
timeout ou indisponibilidade do CRM em F1. Esses controles devem entrar no
adaptador quando o CRM real for conectado.

## F2: contrato ativo para faturamento e onboarding

| Item exigido | Definição |
|---|---|
| Sistema de origem | Contracts |
| Sistemas de destino | Finance e Workflow; RabbitMQ recebe uma cópia do evento quando configurado |
| Informação compartilhada | Fato de ativação, identidade do cliente e do contrato, serviço, vigência, cobrança e SLA |
| Objetivo | Criar a primeira cobrança e iniciar o processo de onboarding após a ativação confirmada |
| Tipo de comunicação | Comando REST síncrono para ativar; evento assíncrono para os efeitos desacoplados |
| API ou serviço utilizado | `POST /api/v1/contracts/{contractId}/activate`, outbox, `ContractActivated.v1` e `POST /api/v1/integration/outbox/dispatch` |
| Dados enviados | Envelope com `eventId`, tipo, versão, horário, correlação, causa, produtor e payload do contrato ativo |
| Dados recebidos | A ativação devolve contrato ativo e `eventId`; o despacho devolve quantidades `processed` e `failed`; consumidores registram a conclusão na inbox e em seus próprios dados |
| Tratamento de erros | `400`, `401`, `403` e `404` na ativação; idempotência HTTP; uma tentativa por despacho; estado `FAILED` ao atingir o limite; consulta e reprocessamento protegidos |

A ativação altera o contrato e grava `ContractActivated.v1` na outbox na mesma
transação. O corpo da resposta inclui o `eventId`. Repetir o comando com a mesma
`Idempotency-Key` devolve esse mesmo evento e não grava outra ativação.

O dispatcher verifica a inbox de cada consumidor. Finance mantém uma cobrança por
contrato, e Workflow mantém uma instância por tipo e referência. Depois dos
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
continuam ativas durante o novo despacho.

## F3: chamado com contrato e SLA

| Item exigido | Definição |
|---|---|
| Sistema de origem | Support, acionado por agente do Atendimento |
| Sistemas de destino | Contracts para elegibilidade e Workflow para o processo de resolução |
| Informação compartilhada | Identificadores de cliente, contrato e serviço; categoria, estado, prioridade, SLA e prazo do chamado |
| Objetivo | Confirmar o direito ao atendimento, aplicar o SLA do contrato e iniciar a resolução |
| Tipo de comunicação | Comando REST, consulta síncrona por porta pública e evento assíncrono |
| API ou serviço utilizado | `POST /api/v1/support/tickets`, `ContractEntitlementPort`, `TicketOpened.v1`, dispatcher e rota de reconciliação |
| Dados enviados | Na abertura: `customerId`, `contractId`, `serviceCode`, `category` e `description`; no evento: dados do chamado sem a descrição |
| Dados recebidos | Elegibilidade e `slaHours` de Contracts; chamado com estado, prioridade, SLA e `dueAt`; Workflow registra uma instância de resolução |
| Tratamento de erros | `400`, `401` ou `403` para acesso/correlação; `422` para combinação inelegível; `PENDING_ENTITLEMENT` quando o adaptador está indisponível; reconciliação posterior; idempotência na abertura |

Quando o adaptador está disponível, Support consulta Contracts por
`ContractEntitlementPort`. Uma combinação ativa de contrato, cliente e serviço
devolve elegibilidade e SLA. Uma combinação inelegível interrompe a abertura com
`422`.

Quando `CONTRACT_ADAPTER_AVAILABLE=false`, Support não descarta a solicitação. Ele
cria o chamado em `PENDING_ENTITLEMENT`, sem SLA nem prazo, e grava
`TicketOpened.v1`. O consumidor de Workflow inicia a resolução com prazo padrão de
24 horas quando o evento ainda não contém SLA. Esse é o comportamento atual do
protótipo.

Depois que Contracts volta a responder, a rota
`POST /api/v1/support/tickets/{ticketId}/reconcile` consulta novamente a
elegibilidade. Uma confirmação muda o chamado para `OPEN`, preenche o SLA e
recalcula o prazo. Uma rejeição muda o estado para `REJECTED_ENTITLEMENT`. A
reconciliação não publica um segundo `TicketOpened.v1`.

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

## Formato e interoperabilidade

- As APIs usam JSON em UTF-8 sob `/api/v1`.
- Identificadores compartilhados usam UUID global; IDs legados ficam mapeados por
  sistema de origem.
- Datas usam ISO 8601. Horários de eventos e prazos usam UTC.
- Valores monetários usam decimal positivo e moeda com três letras.
- Eventos incluem `eventId`, `eventType`, `eventVersion`, `occurredAt`,
  `correlationId`, `causationId`, `producer` e `payload`.
- `correlationId` atravessa HTTP, auditoria, eventos e registros de falha.
- Mudanças incompatíveis exigem nova versão da API ou do evento; mudanças
  compatíveis devem ser aditivas.
- A fonte oficial de cada contexto prevalece. Divergências devem ser registradas
  para análise, sem sobrescrita silenciosa.

O OpenAPI contém as operações e os exemplos REST. O AsyncAPI contém os três
eventos e exemplos de envelope. Os exemplos narrativos reutilizam os mesmos UUIDs
fictícios para demonstrar a continuidade entre os fluxos.

## Limites do protótipo

Os cinco sistemas são contextos e simuladores do protótipo. Produtos, tecnologias,
interfaces, responsáveis e volumes reais da organização não constam no enunciado
e permanecem como premissas a validar. A troca por sistemas reais deve ocorrer por
adaptadores, preservando os contratos e as fronteiras descritas neste documento.
