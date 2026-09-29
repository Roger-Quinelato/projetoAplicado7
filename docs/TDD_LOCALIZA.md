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
- Eventos versionados: `CustomerUpdated.v1`, `ContractActivated.v1` e
  `TicketOpened.v1`.
- `Idempotency-Key` em comandos repetiveis.
- `X-Correlation-ID` em requisicoes, auditoria, logs e eventos.
- Outbox transacional para publicar fatos de negocio.
- Inbox por consumidor para evitar duplicidade em reentregas.
- Adaptadores substituiveis para sistemas reais futuros.

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
