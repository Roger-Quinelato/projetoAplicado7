# Requisitos da Arquitetura do Cenario 4 - Localiza

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Objetivo e Fontes

Este documento adapta o Cenario 4 do `Guia.pdf` para um estudo academico baseado
na Localiza, com foco em locacao de veiculos e mobilidade corporativa. O guia e
a fonte primaria da entrega: ele exige AS-IS, requisitos, TO-BE, padroes,
integracoes, interoperabilidade, qualidade, evolucao, viabilidade, demonstracao
de pelo menos tres fluxos e relatorio tecnico.

As informacoes publicas da Localiza foram usadas apenas para contextualizar o
dominio: aluguel de carros, solucoes para empresas, gestao de frotas, Webcorp,
assistencia 24h, faturamento e ciclo operacional da frota. Produtos internos,
tecnologias, volumes, SLAs reais e interfaces legadas nao foram informados pelo
professor nem pela empresa; portanto permanecem como **Premissa a validar**.

## Sistemas do Cenario

| Sistema | Papel no caso Localiza |
|---|---|
| CRM | Cadastro de clientes, empresas, contatos, preferencias e oportunidades de mobilidade. |
| Reservas e contratos | Reserva, contrato de locacao, grupo de veiculo, periodo, protecoes, condutores e SLA. |
| Financeiro e faturamento | Pre-autorizacao, fatura, pagamento, caucoes, multas, adicionais e inadimplencia. |
| Atendimento e assistencia 24h | Chamados, assistencia ao cliente, suporte durante a locacao, prioridade e historico. |
| Gestao de processos operacionais | Preparacao do veiculo, retirada, devolucao, vistoria, manutencao, sinistro e tarefas internas. |

## Prioridades

- **P0 - obrigatorio nesta entrega:** requisito necessario para atender ao guia,
  executar os tres fluxos integrados ou demonstrar seguranca, recuperacao e
  continuidade.
- **P1 - evolucao orientada por metricas:** requisito preservado no desenho,
  mas dependente de dados reais de operacao.

## Requisitos Funcionais

| ID | Prioridade | Requisito | Criterio de aceite | Rastreabilidade |
|---|---|---|---|---|
| RF-01 | P0 | Manter uma referencia unica de cliente entre os sistemas. | Todo registro integrado usa `customerId` global em UUID e pode manter identificadores legados do CRM, Webcorp, contrato, faturamento e atendimento. | F1, mapeamento de IDs e teste de idempotencia. |
| RF-02 | P0 | Criar reserva/rascunho de contrato de locacao a partir de cliente existente no CRM. | Um cliente elegivel origina contrato `DRAFT` para o produto `RENTAL-FLEX`, sem recadastro manual; repetir a mesma `Idempotency-Key` devolve o mesmo `contractId`. | F1 e `POST /api/v1/contracts/drafts`. |
| RF-03 | P0 | Ativar a locacao e iniciar faturamento e preparacao de retirada. | A ativacao registra `ContractActivated.v1`; Finance cria a primeira cobranca da locacao e Workflow inicia o processo operacional de retirada, sem duplicar efeitos por reentrega. | F2, outbox/inbox e testes de fluxo. |
| RF-04 | P0 | Abrir chamado de atendimento com contrato de locacao e SLA aplicaveis. | Support consulta a elegibilidade em Contracts, registra SLA e publica `TicketOpened.v1`; se Contracts estiver indisponivel, preserva o chamado em `PENDING_ENTITLEMENT` para reconciliacao. | F3 e testes de indisponibilidade. |
| RF-05 | P0 | Propagar alteracoes cadastrais relevantes. | O CRM publica `CustomerUpdated.v1`; consumidores atualizam projecoes locais apos registrar o `eventId`, sem substituir a fonte oficial. | Evento `CustomerUpdated.v1`. |
| RF-06 | P0 | Consultar o estado consolidado de uma operacao. | Uma consulta por `correlationId` reune auditoria e eventos da operacao de reserva, ativacao ou atendimento. | `GET /api/v1/operations/{correlation_id}`. |
| RF-07 | P0 | Consultar e reprocessar integracoes com falha permanente. | Operador autorizado consulta motivo, tentativas e correlacao, e agenda reprocessamento sem duplicar cobrancas, processos ou chamados ja confirmados. | Rotas de falha e reprocessamento. |

## Requisitos Nao Funcionais

| ID | Prioridade | Requisito | Criterio de aceite | Rastreabilidade |
|---|---|---|---|---|
| RNF-01 | P0 | Interoperabilidade | APIs e eventos usam contratos versionados, JSON UTF-8, UUID global, datas ISO 8601 UTC e valores monetarios com moeda explicita. | OpenAPI, AsyncAPI e exemplos. |
| RNF-02 | P0 | Confiabilidade e tolerancia a falhas | Outbox transacional, inbox, `Idempotency-Key` e restricoes unicas impedem efeitos duplicados em reentregas. | Testes F1, F2, F3 e falha permanente. |
| RNF-03 | P0 | Seguranca e privacidade | Rotas exigem autenticacao e papel compativel; logs e eventos nao expoem token, senha, documento completo, dado bancario, CNH, placa completa ou descricao sensivel do chamado. | Testes 403/422 e revisao dos payloads. |
| RNF-04 | P0 | Observabilidade | HTTP, logs, eventos, auditoria e falhas propagam `correlationId`; health checks e metricas permitem diagnostico. | `/health/*`, `/metrics` e consulta de operacao. |
| RNF-05 | P0 | Manutenibilidade | Contextos comunicam-se por interfaces publicas, sem importar modelos internos nem acessar tabelas de outro contexto. Mudanca estrutural exige novo ADR. | Teste estatico de fronteiras e ADR-001. |
| RNF-06 | P0 | Disponibilidade controlada | Falha temporaria de Contracts nao perde chamado de assistencia; estado pendente permite reconciliacao posterior. | Teste de F3 degradado. |
| RNF-07 | P0 | Desempenho da demonstracao | Consultas locais do prototipo apresentam p95 inferior a 500 ms, excluindo atrasos deliberados. | `scripts/performance_smoke.py`. |
| RNF-08 | P1 | Escalabilidade | API sem estado e consumidores idempotentes podem ser replicados por fila quando metricas justificarem. | Estrategia de evolucao. |
| RNF-09 | P0 | Testabilidade | Suite cobre tres fluxos, autorizacao, validacao, reentrega, indisponibilidade, falha permanente, contratos e fronteiras. | `tests/`. |

## Regras Transversais

- CRM e a fonte oficial de cliente, contatos, consentimentos e oportunidades.
- Contracts e a fonte oficial de reserva, contrato de locacao, grupo de veiculo,
  periodo, protecoes e SLA contratado.
- Finance e a fonte oficial de cobranca, fatura, pagamento, caucoes, adicionais
  e inadimplencia.
- Support e a fonte oficial de chamado, assistencia, prioridade, historico e
  resolucao.
- Workflow e a fonte oficial de tarefas operacionais, retirada, devolucao,
  vistoria, manutencao e estados de processo.
- Integration e a fonte oficial de IDs legados, correlacao, outbox, inbox,
  auditoria e falhas.
- REST atende comandos e consultas que exigem resposta imediata. Eventos
  representam fatos confirmados e efeitos desacoplados.

## Escopo e Dependencias Externas

A primeira entrega nao substitui integralmente sistemas corporativos da Localiza,
nao migra historico, nao integra meios reais de pagamento, telemetria, app,
Webcorp, antifraude ou sistemas de loja/agencia. Esses pontos podem ser
conectados futuramente por adaptadores, desde que preservem os contratos e as
fronteiras definidos nesta documentacao.
