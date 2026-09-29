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
| Finance | Consumidor de `ContractActivated.v1` para criar cobranca da locacao. |
| Support | Abertura de chamado, calculo de prioridade e reconciliacao de elegibilidade. |
| Workflow | Processos de retirada, atendimento, devolucao e tarefas operacionais. |
| Integration | Correlacao, IDs legados, idempotencia, outbox, inbox, auditoria e falhas. |

## Decisoes Tecnicas

- API REST versionada em `/api/v1`.
- Eventos versionados, listados em `docs/events/asyncapi.yaml`:
  `CustomerUpdated.v1`, `ContractActivated.v1`, `TicketOpened.v1`,
  `TicketEntitlementReconciled.v1` e `TicketResolved.v1`.
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
