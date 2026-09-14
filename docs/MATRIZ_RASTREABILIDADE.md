# Matriz de rastreabilidade do Cenário 4

| ID | Requisito | Implementação ou documento | Verificação | Estado |
|---|---|---|---|---|
| ASIS-01 | Sistemas, setores, usuários, processos, dados, dependências e problemas | `docs/arquitetura/AS_IS.md` | Revisão contra páginas 2 e 3 do enunciado | Atendido com premissas identificadas |
| RF-01 | Referência única de cliente | UUID em CRM e `integration_legacy_ids` | `test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia` | Atendido |
| RF-02 | Contrato a partir do CRM | `CustomerReader` e `POST /contracts/drafts` | Teste F1 | Atendido |
| RF-03 | Ativação cria cobrança e onboarding | Outbox, Finance e Workflow | Teste F2 com repetição | Atendido |
| RF-04 | Chamado usa contrato, serviço e SLA | `ContractEntitlementPort` e Support | Teste F3 | Atendido |
| RF-05 | Propagação cadastral | `CustomerUpdated.v1` e projeção Contracts | `test_atualizacao_cadastral_chega_a_contratos` | Atendido |
| RF-06 | Estado consolidado por correlação | auditoria, eventos e `GET /operations/{correlation_id}` | OpenAPI e roteiro | Atendido |
| RF-07 | Reprocessamento seguro | estados da outbox, falhas e rota de reprocessamento | contrato REST e análise de código | Atendido |
| ARQ-01 | Componentes, serviços, bancos, consumidores, comunicação e fronteiras | `docs/arquitetura/TO_BE.md` | Revisão arquitetural | Atendido |
| PAD-01 | Seleção e justificativa do estilo | ADR-001 | Opções, consequências e critérios de revisão | Atendido |
| INT-01 | Pelo menos três integrações detalhadas | `docs/INTEGRACOES.md` e `docs/arquitetura/FLUXOS_INTEGRACAO.md` | F1, F2, F3 e ramificações alternativas | Atendido |
| CORP-01 | Papel dos sistemas corporativos | AS-IS e TO-BE | Tabelas de responsabilidade | Atendido |
| INTEROP-01 | Padronização, contratos, IDs, sincronização e inconsistência | OpenAPI, AsyncAPI, `docs/EXEMPLOS_API.md` e plano | Testes de contrato, esquemas de resposta, UUID e exemplos F1-F3 | Atendido |
| QUA-01 | Pelo menos cinco atributos de qualidade | `docs/ATRIBUTOS_QUALIDADE.md` | Matriz com nove atributos | Atendido |
| EVO-01 | Escalabilidade, manutenção e evolução | `docs/EVOLUCAO_MANUTENCAO.md` | Revisão das perguntas do enunciado | Atendido |
| NEG-01 | Público, problema, valor, benefícios e viabilidade | `docs/VISAO_NEGOCIO.md` | Revisão do eixo de empreendedorismo | Atendido |
| DEMO-01 | Três fluxos funcionando | API e `scripts/demo.ps1` | Testes F1, F2 e F3 | Atendido |
| DOC-01 | Diagramas atual e proposto, componentes, integração e comunicação | arquivos em `docs/arquitetura` e relatório | Sete blocos Mermaid renderizados sem erro e figuras do relatório inspecionadas | Atendido |
| DOC-02 | APIs e exemplos de requisição e resposta | `docs/api/openapi.yaml`, `docs/events/asyncapi.yaml` e `docs/EXEMPLOS_API.md` | Parse dos contratos, igualdade com `app.openapi()` e testes automatizados | Atendido |
| DOC-03 | Relatório técnico de 15 a 20 páginas | `output/Relatorio_Tecnico_Cenario_4.docx` | 18 páginas renderizadas e inspecionadas integralmente | Atendido |
| DOC-04 | Apresentação técnica | `output/Apresentacao_Cenario_4.pptx` | Pacote validado e 15 slides renderizados e inspecionados | Atendido |
| SEC-01 | OIDC/OAuth 2.0, papéis e privacidade | adaptador bearer local, RBAC e minimização | teste 403 e revisão de payload/log | Atendido no escopo simulado |
| OBS-01 | Logs, métricas, traces e health checks | middleware, `/metrics`, `/health/*`, correlação e auditoria | testes HTTP e roteiro | Atendido; trace distribuído representado pela correlação no monólito |

## Evidências externas pendentes

Produtos, tecnologias, volumes, responsáveis e fluxos reais da organização não aparecem no enunciado. O projeto não inventa esses dados. A validação com professor ou representante de negócio complementa o AS-IS sem impedir a execução do protótipo acadêmico.

Os resultados da execução local estão registrados em `docs/EVIDENCIAS_VALIDACAO.md`: 13 testes aprovados, contratos sincronizados e p95 local de 6,36 ms em 200 consultas.
