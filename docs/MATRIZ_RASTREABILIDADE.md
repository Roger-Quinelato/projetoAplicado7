# Matriz de rastreabilidade do Cenário 4

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

| ID | Requisito | Implementação ou documento | Verificação | Estado |
|---|---|---|---|---|
| PRD-01 | Contexto, problema, publico-alvo, valor e escopo do produto Localiza | `docs/PRD_LOCALIZA.md` e `docs/VISAO_NEGOCIO.md` | Revisão contra eixo de Empreendedorismo do guia | Atendido |
| DDD-01 | Linguagem ubiqua, contextos e regras de dominio | `docs/DDD_LOCALIZA.md` | Revisão de aderencia aos sistemas do Cenario 4 | Atendido |
| TDD-01 | Desenho tecnico, componentes, contratos e fluxos | `docs/TDD_LOCALIZA.md`, OpenAPI, AsyncAPI e ADR-001 | Revisão contra itens 3, 4, 5 e 7 do guia | Atendido |
| ASIS-01 | Sistemas, setores, usuários, processos, dados, dependências e problemas | `docs/arquitetura/AS_IS.md` | Revisão contra páginas 2 e 3 do enunciado | Atendido com premissas identificadas |
| RF-01 | Referência única de cliente | UUID em CRM, `integration_legacy_ids` e `GET /integration/legacy-ids/{sourceSystem}/{legacyId}` | `test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia` e `test_identificador_legado_resolve_uuid_global` | Atendido |
| RF-02 | Reserva/contrato de locação a partir do CRM | `CustomerReader`, `POST /contracts/reservations`, `POST /contracts/drafts` e rascunho a partir da reserva | Teste F1 e `tests/test_contracts.py` | Atendido |
| RF-03 | Ativação da locação cria cobrança e preparação de retirada | Outbox, Finance e Workflow | Teste F2 com repetição | Atendido |
| RF-04 | Chamado usa contrato, grupo de veículo e SLA | `ContractEntitlementPort` e Support | Teste F3 | Atendido |
| RF-05 | Propagação cadastral | `CustomerUpdated.v1` e projeção Contracts | `test_atualizacao_cadastral_chega_a_contratos` | Atendido |
| RF-06 | Estado consolidado por correlação | auditoria, eventos e `GET /operations/{correlation_id}` | OpenAPI e roteiro | Atendido |
| RF-07 | Reprocessamento seguro | estados da outbox, falhas e rota de reprocessamento | `test_falha_permanente_pode_ser_listada_e_reprocessada` | Atendido |
| ARQ-01 | Componentes, serviços, bancos, consumidores, comunicação e fronteiras | `docs/arquitetura/TO_BE.md` | Revisão arquitetural | Atendido |
| PAD-01 | Seleção e justificativa do estilo | ADR-001 | Opções, consequências e critérios de revisão | Atendido |
| INT-01 | Pelo menos três integrações detalhadas | `docs/INTEGRACOES.md` e `docs/arquitetura/FLUXOS_INTEGRACAO.md` | F1, F2, F3 e ramificações alternativas | Atendido |
| CORP-01 | Papel dos sistemas corporativos | AS-IS e TO-BE | Tabelas de responsabilidade | Atendido |
| INTEROP-01 | Padronização, contratos técnicos, IDs, sincronização e inconsistência | OpenAPI, AsyncAPI, `docs/EXEMPLOS_API.md` e plano | `test_openapi_valido_com_exemplos_e_erros_problem_json`, `test_exemplos_asyncapi_validam_contra_os_schemas` e `test_envelopes_publicados_validam_contra_asyncapi` | Atendido |
| ERR-01 | Contrato único de erro | `src/archcorp/errors.py`, `ProblemDetails` no OpenAPI e seção "Contrato de erro" em `docs/INTEGRACOES.md` | `test_contrato_de_erro_problem_json_para_status_comuns` e `test_conflitos_de_unicidade_retornam_409_e_nao_500` | Atendido |
| DATA-01 | Dados sintéticos e migração aditiva | `docs/DADOS_SINTETICOS.md`, `scripts/seed_sintetico.py`, ADR-002 e migrações Alembic | `test_carga_sintetica_e_idempotente`, `test_migracoes_criam_esquema_sem_divergencia_dos_modelos` e `test_migracoes_sao_aditivas` | Atendido em SQLite; PostgreSQL publicado pendente |
| CRM-01 | CRM completo: clientes, contatos e oportunidades com validação e autorização | `src/archcorp/crm/` | `tests/test_crm.py` | Atendido |
| CTR-01 | Reservas e contratos: reserva, rascunho, ativação idempotente e encerramento | `src/archcorp/contracts/` e `ContractClosed.v1` | `tests/test_contracts.py`, `test_composicao_da_aplicacao_nao_le_modelos_dos_contextos` | Atendido; Finance não consome o encerramento |
| QUA-01 | Pelo menos cinco atributos de qualidade | `docs/ATRIBUTOS_QUALIDADE.md` | Matriz com nove atributos | Atendido |
| EVO-01 | Escalabilidade, manutenção e evolução | `docs/EVOLUCAO_MANUTENCAO.md` | Revisão das perguntas do enunciado | Atendido |
| NEG-01 | Público, problema, valor, benefícios e viabilidade | `docs/VISAO_NEGOCIO.md` | Revisão do eixo de empreendedorismo | Atendido |
| DEMO-01 | Três fluxos funcionando | API e `scripts/demo.ps1` | Testes F1, F2 e F3 | Atendido |
| DOC-01 | Diagramas atual e proposto, componentes, integração e comunicação | arquivos em `docs/arquitetura` e relatório | Sete blocos Mermaid renderizados sem erro e figuras do relatório inspecionadas | Atendido |
| DOC-02 | APIs e exemplos de requisição e resposta | `docs/api/openapi.yaml` (gerado por `tools/export_openapi.py`), `docs/events/asyncapi.yaml` e `docs/EXEMPLOS_API.md` | Igualdade com `app.openapi()`, validação OpenAPI 3.1, exemplo em toda resposta 2xx JSON, erros em problem+json e exemplos AsyncAPI validados contra os schemas | Atendido |
| DOC-03 | Relatório técnico de 15 a 20 páginas | `output/Relatorio_Tecnico_Cenario_4.docx` | 18 páginas renderizadas e inspecionadas integralmente | Atendido; regenerar após revisão Localiza |
| DOC-04 | Apresentação técnica | `output/Apresentacao_Cenario_4.pptx` | Pacote validado e 15 slides renderizados e inspecionados | Atendido; regenerar após revisão Localiza |
| SEC-01 | OIDC/OAuth 2.0, papéis e privacidade | adaptador bearer local, RBAC e minimização; matriz em `docs/TDD_LOCALIZA.md` | `test_matriz_de_autorizacao_do_crm` (401/403 por papel) e revisão de payload/log | Atendido no escopo simulado; sem OIDC |
| OBS-01 | Logs, métricas, traces e health checks | middleware, `/metrics`, `/health/*`, correlação e auditoria | testes HTTP e roteiro | Atendido; trace distribuído representado pela correlação no monólito |

## Evidências externas pendentes

Produtos, tecnologias, volumes, responsáveis e fluxos reais da organização não aparecem no enunciado. O projeto não inventa esses dados. A validação com professor ou representante de negócio complementa o AS-IS sem impedir a execução do protótipo acadêmico.

## Cronograma de Entregas do Guia

| Entrega exigida | Artefatos do projeto Localiza |
|---|---|
| Análise AS-IS | `docs/arquitetura/AS_IS.md` |
| Levantamento de requisitos | `docs/PRD_LOCALIZA.md` e `docs/REQUISITOS.md` |
| Arquitetura TO-BE e decisões | `docs/arquitetura/TO_BE.md`, `docs/TDD_LOCALIZA.md`, ADR-001 e ADR-002 |
| Padrões e estilos | ADR-001 e `docs/arquitetura/TO_BE.md` |
| APIs e pelo menos três integrações | `docs/INTEGRACOES.md`, `docs/arquitetura/FLUXOS_INTEGRACAO.md`, OpenAPI e AsyncAPI |
| Sistemas corporativos | AS-IS, TO-BE e `docs/DDD_LOCALIZA.md` |
| Interoperabilidade | `docs/EXEMPLOS_API.md`, OpenAPI, AsyncAPI e matriz |
| Qualidade arquitetural | `docs/ATRIBUTOS_QUALIDADE.md` |
| Escalabilidade, manutenção e evolução | `docs/EVOLUCAO_MANUTENCAO.md` |
| Eixo de empreendedorismo | `docs/VISAO_NEGOCIO.md` e PRD |
| Demonstração prática | `docs/ROTEIRO_DEMONSTRACAO.md` e `scripts/demo.ps1` |
| Relatório técnico e apresentação | `output/Relatorio_Tecnico_Cenario_4.docx` e `output/Apresentacao_Cenario_4.pptx` |

Os resultados da execução local estão registrados em `docs/EVIDENCIAS_VALIDACAO.md`: 13 testes aprovados, contratos sincronizados e p95 local de 6,36 ms em 200 consultas.
