# Matriz de rastreabilidade do Cenário 4

> Revisão documental: **28/10/2026**, base `f1669d7` (`main`, integração #75). Consulte o [Estado da implementação](ESTADO_IMPLEMENTACAO.md), o [índice de entrega](ENTREGA_FINAL.md) e o [panorama de prontidão](PANORAMA_PRONTIDAO.md).

Nesta matriz, **Atendido** indica cobertura documental ou implementação no escopo acadêmico, sujeita aos limites de cada linha; não declara aceite docente, deploy ou conclusão da entrega. Nomes de testes indicam cobertura versionada. Contagens e demonstrações datadas são históricas e não são, por si só, novas execuções de testes.

A [CI da base `f1669d7`, run 40199072801](https://github.com/Roger-Quinelato/projetoAplicado7/actions/runs/40199072801), foi consultada remotamente em 28/10/2026: `rabbitmq`, `e2e`, `application` e `postgresql` concluídos com `success`. É evidência remota da versão-base, distinta das execuções locais históricas e da execução local registrada nesta revisão. Não comprova publicação externa.

A execução da CI ocorreu em **25/10/2026** e foi consultada em **28/10/2026**. As contagens abaixo foram conferidas nos logs obtidos do GitHub Actions, com checkout de `f1669d78f01e2d279b3de60a999ed778e6c9916e`:

| Job / etapa | Resultado registrado |
|---|---|
| `application` / testes Python | 252 aprovados, 14 ignorados |
| `postgresql` / testes Python | 262 aprovados, 4 ignorados |
| `rabbitmq` / testes do broker e regressões | 22 aprovados |
| `e2e` / fluxos no navegador | 25 aprovados |
| `e2e` / varredura axe | 1 aprovado |

As suítes se sobrepõem e **não devem ser somadas**. São resultados da CI da base, não uma reexecução local em 28/10/2026.

| ID | Requisito | Implementação ou documento | Verificação | Estado |
|---|---|---|---|---|
| PRD-01 | Contexto, problema, publico-alvo, valor e escopo do produto Localiza | `docs/PRD_LOCALIZA.md` e `docs/VISAO_NEGOCIO.md` | Revisão contra eixo de Empreendedorismo do guia | Atendido |
| DDD-01 | Linguagem ubiqua, contextos e regras de dominio | `docs/DDD_LOCALIZA.md` | Revisão de aderencia aos sistemas do Cenario 4 | Atendido |
| TDD-01 | Desenho tecnico, componentes, contratos e fluxos | `docs/TDD_LOCALIZA.md`, OpenAPI, AsyncAPI e ADR-001 | Revisão contra itens 3, 4, 5 e 7 do guia | Atendido |
| ASIS-01 | Sistemas, setores, usuários, processos, dados, dependências e problemas | `docs/arquitetura/AS_IS.md` | Revisão contra páginas 2 e 3 do enunciado | Atendido com premissas identificadas |
| RF-01 | Referência única de cliente | UUID em CRM, `integration_legacy_ids` e `GET /integration/legacy-ids/{sourceSystem}/{legacyId}` | `test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia` e `test_identificador_legado_resolve_uuid_global` | Atendido |
| RF-02 | Reserva/contrato de locação a partir do CRM | `CustomerReader` envolvido por `ResilientCustomerReader` (ADR-006), `POST /contracts/reservations`, `POST /contracts/drafts` e rascunho a partir da reserva | Teste F1, `tests/test_contracts.py`, `tests/test_f1_cliente_reserva_contrato.py` (caminho pela reserva, rejeições, validação 4xx, CRM indisponível com `503` sem efeito, falha transitória absorvida, erro não transitório sem retentativa, idempotência e correlação), `tests/test_crm_reader_resiliente.py` e `scripts/demo_f1.py` | Atendido localmente em 17/10/2026; ADR-006 aguarda aceite; o prazo não interrompe leitura no mesmo processo (corte por chamada fica para o conector de rede) |
| RF-03 | Ativação da locação cria cobrança e preparação de retirada | Outbox, Finance e Workflow | Teste F2 com repetição | Atendido |
| RF-04 | Chamado usa contrato, grupo de veículo e SLA | `ContractEntitlementPort`, `src/archcorp/support/` (`domain.py`, `service.py`) | Teste F3, `test_indisponibilidade_de_contratos_cria_estado_pendente` e `tests/test_t15_atendimento.py` | Parcial em relação ao plano: contrato ativo, cliente, serviço e SLA implementados; grupo de veículo não é consultado nem exposto pelo contrato de elegibilidade. O caminho pela reserva transfere o SLA ao contrato; o rascunho direto também define SLA |
| RF-05 | Propagação cadastral | `CustomerUpdated.v1` e projeção Contracts | `test_atualizacao_cadastral_chega_a_contratos` | Atendido |
| RF-06 | Estado consolidado por correlação | auditoria, eventos e `GET /operations/{correlation_id}` | OpenAPI e roteiro | Atendido |
| RF-07 | Reprocessamento seguro | estados da outbox, falhas e rota de reprocessamento | `test_falha_permanente_pode_ser_listada_e_reprocessada` | Atendido |
| ARQ-01 | Componentes, serviços, bancos, consumidores, comunicação e fronteiras | `docs/arquitetura/TO_BE.md` | Revisão arquitetural | Atendido |
| PAD-01 | Seleção e justificativa do estilo | ADR-001 a ADR-007 (ADR-006 proposto) | Opções, consequências e critérios de revisão | Atendido |
| INT-01 | Pelo menos três integrações detalhadas | `docs/INTEGRACOES.md` e `docs/arquitetura/FLUXOS_INTEGRACAO.md` | F1, F2, F3 e ramificações alternativas | Atendido |
| CORP-01 | Papel dos sistemas corporativos | AS-IS e TO-BE | Tabelas de responsabilidade | Atendido |
| INTEROP-01 | Padronização, contratos técnicos, IDs, sincronização e inconsistência | OpenAPI, AsyncAPI, `docs/EXEMPLOS_API.md` e plano | `test_openapi_valido_com_exemplos_e_erros_problem_json`, `test_exemplos_asyncapi_validam_contra_os_schemas` e `test_envelopes_publicados_validam_contra_asyncapi` | Atendido |
| ERR-01 | Contrato único de erro | `src/archcorp/errors.py`, `ProblemDetails` no OpenAPI e seção "Contrato de erro" em `docs/INTEGRACOES.md` | `test_contrato_de_erro_problem_json_para_status_comuns` e `test_conflitos_de_unicidade_retornam_409_e_nao_500` | Atendido |
| DATA-01 | Dados sintéticos e evolução controlada do esquema | `docs/DADOS_SINTETICOS.md`, `scripts/seed_sintetico.py`, ADR-002, exceção ADR-003 e convergência ADR-004 (`0005_merge_finance_support`) | `tests/test_foundation.py`, `tests/test_migration_convergence.py` e job `postgresql` da CI da base | Atendido no protótipo, com exceção financeira não aditiva explicitamente aceita; PostgreSQL publicado pendente |
| CRM-01 | CRM completo: clientes, contatos e oportunidades com validação e autorização | `src/archcorp/crm/` | `tests/test_crm.py` | Atendido |
| CTR-01 | Reservas e contratos: reserva, rascunho, ativação idempotente e encerramento | `src/archcorp/contracts/` e `ContractClosed.v1` | `tests/test_contracts.py`, `test_composicao_da_aplicacao_nao_le_modelos_dos_contextos` | Atendido; Finance consome o encerramento (FIN-01) |
| FIN-01 | Financeiro: fatura com ciclo de vida, faturamento final, pagamento simulado e inadimplência por vencimento (T12) | `src/archcorp/finance/` (`domain.py`, `service.py`, `routes.py`), consumidores `finance` e `finance-faturamento-final`, `POST /finance/invoices/overdue-check`, `POST /finance/invoices/{id}/cancel`, migração `0004_finance_lifecycle` e ADR-003 | `tests/test_finance.py` (transições, saldo, vencimento UTC com relógio injetado, ciclos iniciados, reentrega sem duplicar fatura, `Idempotency-Key`, validações, autorização, migração e downgrade), guarda aditiva com exceção datada em `tests/test_foundation.py`, F2 sem regressão e demonstração contra `uvicorn` em 14/10/2026 (20/20) | Integrado à `main` em #75; cobertura SQLite e PostgreSQL na CI da base. Demonstração de 14/10 é histórica; sem PSP, nota fiscal, agendador ou banco publicado comprovado; regra de faturamento final e prazo são premissas |
| SUP-01 | Atendimento completo (T15): abertura, SLA, responsável, resolução e reconciliação | `src/archcorp/support/` (máquina de estados, relógio injetável, histórico `support_ticket_history`), migração `0004_support_sla_history`, rotas `/support/tickets/{id}/history` e `/support/tickets/reconcile-pending`, campos `openedAt`/`resolvedAt`/`slaStatus` no OpenAPI e AsyncAPI | `tests/test_t15_atendimento.py` (48 casos: transições, SLA com relógio, idempotência, validação, reentrega, reconciliação individual/lote/interrompida, 401/403 por papel, migração) e demonstração contra `uvicorn` local em 14/10/2026 (32/32) | Integrado à `main` em #75; cobertura na CI da base. Os 48 casos e a demonstração de 14/10 são registros históricos; sem agendador de vencimento nem central de atendimento real |
| QUA-01 | Pelo menos cinco atributos de qualidade | `docs/ATRIBUTOS_QUALIDADE.md` | Nove atributos com necessidade, risco, estratégia, resultado esperado, evidência e limite | Atendido documentalmente; avaliação não equivale à implementação de todas as estratégias ou a validação de produção |
| EVO-01 | Escalabilidade, manutenção e evolução | `docs/EVOLUCAO_MANUTENCAO.md` | Revisão das perguntas do enunciado | Atendido |
| NEG-01 | Público, problema, valor, benefícios e viabilidade | `docs/VISAO_NEGOCIO.md` | Revisão do eixo de empreendedorismo | Atendido |
| DEMO-01 | Três fluxos funcionando | API, `scripts/demo.ps1` e `scripts/demo_f1.py`, `demo_f2.py` e `demo_f3.py` (Python, sem dependência específica de SO; código de saída ≠ 0 em falha) | Testes F1, F2 e F3; em 17/10/2026, contra `uvicorn` local em Windows: F1 20/20, F2 14/14, F3 15/15 | Atendido localmente; URL HTTPS pública não verificada |
| DOC-01 | Diagramas atual e proposto, componentes, integração e comunicação | arquivos em `docs/arquitetura`, PNGs em `docs/arquitetura/img/` (`tools/render_diagrams.py`) e relatório | Dez PNGs em `docs/arquitetura/img/`, gerados por `tools/render_diagrams.py` e embutidos no relatório e na apresentação; renderização inspecionada em 17/10/2026 | Atendido |
| DOC-02 | APIs e exemplos de requisição e resposta | `docs/api/openapi.yaml` (gerado por `tools/export_openapi.py`), `docs/events/asyncapi.yaml` e `docs/EXEMPLOS_API.md` | Igualdade com `app.openapi()`, validação OpenAPI 3.1, exemplo em toda resposta 2xx JSON, erros em problem+json e exemplos AsyncAPI validados contra os schemas | Atendido |
| DOC-03 | Relatório técnico de 15 a 20 páginas | `output/Relatorio_Tecnico_Cenario_4.docx` (`tools/build_report.py`) | Registro histórico de 20 páginas na renderização revisada de 28/10/2026; evidência anterior no LibreOffice em 17/10/2026; estrutura do Guia, fundamentação e citações autor-data; versão atual não renderizada nesta atividade | Autoria informada: Roger Quinelato (backend, produto e negócio) e Raquel Pereira (frontend e levantamento de requisitos); conferir coerência com o código e paginação de 15–20 páginas da versão a submeter |
| DOC-04 | Apresentação técnica | `output/Apresentacao_Cenario_4.pptx` (`tools/build_presentation.mjs`) | Registro histórico de 18 slides e conferência de integridade/layout em 17/10/2026; não reconferidos nesta atividade | Autoria informada: Roger Quinelato e Raquel Pereira e conferência de coerência com a versão final |
| SEC-01 | OIDC/OAuth 2.0, papéis e privacidade | Bearer demonstrativo, RBAC e minimização; matriz em `docs/TDD_LOCALIZA.md` | `tests/test_crm.py`, `tests/test_security_hardening.py`, `tests/test_demo_credentials.py` e job `application` da CI da base | Parcial frente ao RNF: RBAC e controles demonstrativos implementados; OIDC/OAuth não implementados, credencial pública compartilhada sem identidade individual; sem publicação pública (ADR-007) |
| OBS-01 | Logs, métricas, traces e health checks | `src/archcorp/observability.py`, middleware, `/metrics`, `/health/*`, correlação e auditoria | `tests/test_security_hardening.py`, `tests/test_prontidao.py` e testes HTTP versionados | Parcial frente ao RNF: logs, métricas básicas, health checks e correlação implementados; tracing distribuído não implementado. Correlação não substitui spans, propagação de contexto de trace ou coletor; métricas em memória; horário de log convertido para UTC desde 29/10/2026 |
| RNF-01 | Interoperabilidade: contratos versionados, JSON UTF-8, UUID, ISO 8601 UTC, moeda explícita | OpenAPI, AsyncAPI, `errors.py`, `integration_legacy_ids` | `tools/export_openapi.py --check`, `tests/test_contracts_and_architecture.py`, `tests/test_api_v1_compatibility.py` | Parcial: valores monetários são `number` (float) na API v1, dívida para a v2 |
| RNF-02 | Confiabilidade: sem efeitos duplicados em reentrega | Outbox, inbox, `Idempotency-Key`, restrições únicas | `tests/test_dispatch_recovery.py`, `tests/test_reliability_regressions.py`, `tests/test_integridade_f2_f3.py` | Atendido no protótipo |
| RNF-03 | Segurança e privacidade | RBAC por token, validação, minimização, `PUBLIC_DEMO` | Ver SEC-01 | Parcial (ver SEC-01) |
| RNF-04 | Observabilidade | Correlação, logs JSON, `/metrics`, auditoria, health checks | Ver OBS-01 | Parcial (ver OBS-01) |
| RNF-05 | Manutenibilidade: fronteiras por interface pública | Fachadas `*.public`, ADR-005 | Teste arquitetural em `tests/test_contracts_and_architecture.py` | Atendido; serviços ainda usam SQLAlchemy diretamente (evolução) |
| RNF-06 | Disponibilidade controlada: chamado preservado sem Contracts | `PENDING_ENTITLEMENT` e reconciliação | `tests/test_t15_atendimento.py`, `tests/test_support.py` | Atendido com indisponibilidade simulada |
| RNF-07 | Desempenho: p95 < 500 ms nas consultas locais | `scripts/performance_smoke.py` | Medição registrada em `docs/EVIDENCIAS_VALIDACAO.md` | Atendido no ambiente local registrado; não dimensiona produção |
| RNF-08 | Escalabilidade | API sem estado e consumidores idempotentes | Estratégia em `docs/EVOLUCAO_MANUTENCAO.md` | Meta: escala horizontal não demonstrada |
| RNF-09 | Testabilidade | Suíte pytest, `web/tests`, `web/e2e` com axe, CI com 4 jobs | Ver `docs/EVIDENCIAS_VALIDACAO.md` e CI | Atendido |

## Evidências externas pendentes

Produtos, tecnologias, volumes, responsáveis e fluxos reais da organização não aparecem no enunciado. O projeto não inventa esses dados. A validação com professor ou representante de negócio complementa o AS-IS sem impedir a execução do protótipo acadêmico.

## Correspondência com as entregas do Guia

| Entrega exigida | Artefatos do projeto Localiza |
|---|---|
| Análise AS-IS | `docs/arquitetura/AS_IS.md` |
| Levantamento de requisitos | `docs/PRD_LOCALIZA.md` e `docs/REQUISITOS.md` |
| Arquitetura TO-BE e decisões | `docs/arquitetura/TO_BE.md`, `docs/TDD_LOCALIZA.md`, ADR-001, ADR-002 e ADR-003 |
| Padrões e estilos | ADR-001 e `docs/arquitetura/TO_BE.md` |
| APIs e pelo menos três integrações | `docs/INTEGRACOES.md`, `docs/arquitetura/FLUXOS_INTEGRACAO.md`, OpenAPI e AsyncAPI |
| Sistemas corporativos | AS-IS, TO-BE e `docs/DDD_LOCALIZA.md` |
| Interoperabilidade | `docs/EXEMPLOS_API.md`, OpenAPI, AsyncAPI e matriz |
| Qualidade arquitetural | `docs/ATRIBUTOS_QUALIDADE.md` |
| Escalabilidade, manutenção e evolução | `docs/EVOLUCAO_MANUTENCAO.md` |
| Eixo de empreendedorismo | `docs/VISAO_NEGOCIO.md` e PRD |
| Demonstração prática | `docs/ROTEIRO_DEMONSTRACAO.md` e `scripts/demo.ps1` |
| Relatório técnico e apresentação | `output/Relatorio_Tecnico_Cenario_4.docx` e `output/Apresentacao_Cenario_4.pptx` |

Os resultados locais históricos estão registrados em `docs/EVIDENCIAS_VALIDACAO.md`. Os números vigentes (testes, p95 e roteiros) ficam somente naquele documento, identificados pelo commit da execução; esta matriz não os repete. A CI da base está identificada no início desta matriz.

## Lacunas para fechamento

- **Entrega acadêmica:** nomes, contribuições, coerência entre código/relatório/slides, conferência renderizada do artigo com 15–20 páginas, ensaio dos três fluxos e aceite docente das premissas.
- **Operação prevista no plano:** comprovar HTTPS, health checks, escrita/leitura, migrações, proteção e persistência após reinício no provedor, ou registrar o alinhamento docente sobre a demonstração local permitida pelo Guia.
- **Pendências técnicas:** RF-04 parcial, OIDC/OAuth e tracing distribuído não implementados; sem escala horizontal demonstrada. ADR-006 continua proposto, apesar de o adaptador estar no código integrado.
- **Prazos:** o [cronograma vigente](CRONOGRAMA_EXECUCAO.md) prevê projeto/documentação em **09/11/2026** e apresentação avaliada em **23/11/2026**. O [panorama](PANORAMA_PRONTIDAO.md) acompanha o fechamento; integração #75 e CI aprovada não encerram tickets ou aceites automaticamente.

## Correções verificadas de fechamento

- F3: resolução e reconciliação sem processo existente falham de forma
  recuperável; a inbox não é confirmada. Após recuperar a abertura, repetir o
  despacho conclui a operação. Se a retentativa atingir o limite, reprocessar
  explicitamente os eventos em `FAILED` após resolver a dependência.
- Financeiro: cancelamento usa a data UTC e o estado efetivo da consulta.
  Fatura vencida recebe `409 INVALID_STATE`, mesmo antes da verificação
  explícita de inadimplência. No próprio dia do vencimento, ainda pode ser
  cancelada se estiver aberta e sem pagamento.
- Workflow: o fim do contrato cancela tarefas ainda abertas e calcula o
  agregado: todas `DONE` → `COMPLETED`; alguma `CANCELLED` e todas finais →
  `CANCELLED`. Reentrega preserva estados e responsáveis finais. O evento de
  encerramento também aguarda o processo de preparação, sem confirmação vazia.

As correções não alteram retroativamente registros já consumidos em versões
anteriores. A persistência de inconsistências antigas exige análise e reparação
específicas, sem apagar dados ou reescrever eventos automaticamente.
