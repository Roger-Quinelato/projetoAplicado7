# TDD - Desenho Tecnico Localiza

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Objetivo Tecnico

Demonstrar uma arquitetura corporativa para integrar capacidades de locacao de
veiculos da Localiza sem substituir os sistemas existentes. O desenho segue o
`Guia.pdf` e o ADR-001: SOA pragmatica em monolito modular, com REST para
decisoes imediatas e eventos para efeitos assíncronos.

## Componentes

| Contexto | Responsabilidade tecnica |
|---|---|
| CRM | API de cliente, elegibilidade e publicacao de alteracao cadastral. |
| Contracts | Reserva/contrato de locacao, ativacao, grupo de veiculo, vigencia e SLA. |
| Finance | Consumidores de `ContractActivated.v1` (primeira fatura) e `ContractClosed.v1` (fatura final); pagamento simulado e inadimplência por vencimento. |
| Support | Abertura de chamado, calculo de prioridade e reconciliacao de elegibilidade. |
| Workflow | Processos de retirada, atendimento, devolucao e tarefas operacionais. |
| Integration | Correlacao, IDs legados, idempotencia, outbox, inbox, auditoria e falhas. |

## Decisoes Tecnicas

- API REST versionada em `/api/v1`.
- Eventos versionados, listados em `docs/events/asyncapi.yaml`:
  `CustomerUpdated.v1`, `ContractActivated.v1`, `ContractClosed.v1`,
  `TicketOpened.v1`, `TicketEntitlementReconciled.v1` e `TicketResolved.v1`.
- Erros em `application/problem+json` com `code` estável e `correlationId`.
- `Idempotency-Key` em comandos repetiveis.
- `X-Correlation-ID` em requisicoes, auditoria, logs e eventos.
- Outbox transacional para publicar fatos de negocio.
- Inbox por consumidor para evitar duplicidade em reentregas.
- Adaptadores substituiveis para sistemas reais futuros.

## Autorização

Cada rota exige token e papel compatível (`src/archcorp/security.py`). O token
`demo-admin` e, no modo público, a credencial compartilhada acumulam todos os
papéis; não há OIDC nem contas individuais. Sem token a API responde `401`; com
papel incompatível, `403`.

### CRM

| Operação | Papéis |
|---|---|
| Listar e consultar clientes | commercial, contracts, support, admin |
| Criar, alterar e inativar cliente | commercial, admin |
| Contatos: criar, listar, consultar, alterar e remover | commercial, admin |
| Oportunidades: criar, listar, consultar e alterar | commercial, admin |

Regras do CRM verificadas em `tests/test_crm.py`:

- nomes são aparados e não podem ficar vazios; telefone segue E.164; notas têm no
  máximo 2000 caracteres;
- e-mail de cliente é único no CRM e e-mail de contato é único por cliente
  (`409 CONFLICT`);
- oportunidade `OPEN` pode ir para `WON` ou `LOST`; esses estados são finais
  (`409 INVALID_STATE`);
- cliente é inativado, não removido, para preservar o histórico; cliente inativo
  não origina reserva nem contrato;
- `CustomerUpdated.v1` é publicado somente quando nome ou e-mail mudam, que são os
  dados projetados em Contracts;
- criação, alteração e remoção são auditadas com `correlationId`.

### Reservas e contratos

| Operação | Papéis |
|---|---|
| Criar, listar, consultar e cancelar reserva; gerar rascunho a partir da reserva | commercial, contracts, admin |
| Criar rascunho de contrato | commercial, contracts, admin |
| Ativar e encerrar contrato | contracts, admin |
| Listar e consultar contratos | commercial, contracts, finance, support, admin |
| Consultar elegibilidade e SLA | support, admin |

Regras verificadas em `tests/test_contracts.py`:

- estados e transições centralizados em `src/archcorp/contracts/domain.py`;
- Contracts lê o cliente somente por `CustomerReader` (`crm/public.py`); a
  composição em `main.py` não importa modelos de outros contextos;
- rascunho e ativação exigem cliente ativo, elegível e com consentimento; a
  ativação revalida o cliente;
- `Idempotency-Key` (até 100 caracteres) é obrigatória em rascunho e ativação e
  opcional em criação de reserva e encerramento; a impressão digital do pedido
  inclui todos os campos, inclusive `slaHours`;
- um segundo rascunho para o mesmo cliente, serviço e início recebe `409` com o
  `contractId` existente;
- reserva exige início futuro, fim não anterior ao início, moeda com três letras
  maiúsculas e valor com duas casas decimais;
- o encerramento grava data e motivo, encerra a reserva vinculada, publica
  `ContractClosed.v1` e é auditado.

### Financeiro

| Operação | Papéis |
|---|---|
| Listar e consultar faturas | finance, operations, admin |
| Verificar vencimento e registrar inadimplência | finance, operations, admin |
| Registrar pagamento simulado, cancelar fatura e listar pagamentos | finance, admin |

Regras verificadas em `tests/test_finance.py`:

- estados e transições da fatura centralizados em `src/archcorp/finance/domain.py`;
  `PAID` e `CANCELLED` são finais; pagamento parcial em fatura inadimplente mantém
  `OVERDUE` até a quitação;
- primeira fatura (`INITIAL`) e fatura final (`FINAL`) são únicas por contrato e
  por `eventId` de origem; o vencimento é a data UTC do evento mais 10 dias
  (premissa a validar: prazo e data de referência; ver ADR-003);
- a fatura final cobra os ciclos iniciados entre `startsOn` e `endsOn` (premissa a
  validar) menos o total já faturado, inclusive faturas canceladas (cancelamento é
  definitivo); sem valor restante, apenas audita e grava um marcador por `eventId`,
  de modo que a reentrega fora da inbox também não repete efeito;
- pagamento: `Idempotency-Key` opcional, valor positivo com duas casas, moeda igual
  à da fatura (`422 VALIDATION_ERROR`), sem sobrepagamento (`409 CONFLICT`); fatura
  quitada mantém o `409 CONFLICT` da v1 e fatura cancelada recebe `409 INVALID_STATE`;
  a referência não vai para auditoria nem log;
- o motivo do cancelamento (até 200 caracteres) vai para a auditoria e não deve
  conter dado pessoal, bancário ou sensível;
- valores monetários saem como `number` (float) na v1 por compatibilidade; a regra
  de decimal com moeda explícita vale internamente (`Decimal`) e a troca na API é
  dívida para a v2;
- inadimplência: fatura com saldo e data UTC posterior a `dueDate`; o comando de
  verificação a registra com data e auditoria, sem repetir marcações.

## Fluxos Tecnicos

1. **F1 - Cliente para reserva/contrato:** CRM fornece `customerId`; Contracts
   cria contrato `DRAFT` para `RENTAL-FLEX`.
2. **F2 - Ativacao da locacao:** Contracts ativa o contrato e grava
   `ContractActivated.v1`; Finance cria cobranca; Workflow inicia preparacao de
   retirada.
3. **F3 - Atendimento com SLA:** Support consulta Contracts; registra chamado;
   Workflow inicia resolucao; indisponibilidade gera `PENDING_ENTITLEMENT`.

## Dados Compartilhados

O modelo compartilhado minimo contem apenas identificadores, produto de locacao,
valor, moeda, ciclo, vigencia, SLA, categoria e status. Dados sensiveis, como
documento completo, CNH, placa completa, cartao, token e descricao detalhada do
chamado, nao devem trafegar em eventos.

## Qualidade

As principais propriedades verificadas sao interoperabilidade, confiabilidade,
seguranca, observabilidade, manutenibilidade, disponibilidade controlada,
desempenho local, escalabilidade futura e testabilidade.

## Validacao

A validacao tecnica ocorre por testes automatizados, contratos OpenAPI/AsyncAPI,
roteiro de demonstracao, matriz de rastreabilidade e evidencias registradas em
`docs/EVIDENCIAS_VALIDACAO.md`.
