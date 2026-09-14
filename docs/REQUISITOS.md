# Requisitos da arquitetura do Cenário 4

## Objetivo e fontes

Este documento reúne os requisitos da arquitetura proposta para integrar CRM,
contratos, financeiro, atendimento e gestão de processos. Ele detalha o item 2
do `Guia.pdf` e usa como referências o
`PLANO_IMPLEMENTACAO_CENARIO_4.md`, o ADR-001, os contratos OpenAPI e
AsyncAPI e o comportamento demonstrado pelo protótipo.

O guia confirma os sistemas do Cenário 4 e os problemas organizacionais gerais.
Produtos, tecnologias, volumes, responsáveis e interfaces atuais não foram
informados. Esses dados permanecem classificados como **Premissa a validar** e
não alteram os requisitos da demonstração acadêmica.

## Prioridades

- **P0 — obrigatório nesta entrega:** requisito necessário para compreender a
  arquitetura, executar os três fluxos mínimos ou demonstrar segurança,
  recuperação e continuidade.
- **P1 — evolução orientada por métricas:** requisito que deve ser preservado no
  desenho, mas cuja implantação completa depende de dados de produção ausentes
  no guia.

## Requisitos funcionais

| ID | Prioridade | Requisito | Critério de aceite | Rastreabilidade |
|---|---|---|---|---|
| RF-01 | P0 | Manter uma referência única de cliente entre os sistemas. | Todo registro integrado usa um `customerId` global em UUID e pode manter identificadores legados associados ao sistema de origem. | F1, tabelas de mapeamento de IDs e teste de idempotência do contrato. |
| RF-02 | P0 | Criar um contrato a partir de um cliente existente no CRM. | Um cliente elegível origina um contrato em estado `DRAFT` sem novo cadastro manual; repetir a requisição com a mesma `Idempotency-Key` devolve o mesmo `contractId`. | F1, `POST /api/v1/contracts/drafts` e `test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia`. |
| RF-03 | P0 | Ativar o contrato e iniciar faturamento e onboarding. | A ativação registra `ContractActivated.v1`; Finance cria uma cobrança e Workflow inicia um onboarding, sem duplicar efeitos após reentrega. | F2, outbox/inbox e `test_f2_ativacao_cria_uma_cobranca_e_um_onboarding`. |
| RF-04 | P0 | Abrir chamado com o contrato, o serviço e o SLA aplicáveis. | Support consulta a elegibilidade, registra o SLA e publica `TicketOpened.v1`; se Contracts estiver indisponível, preserva o chamado em `PENDING_ENTITLEMENT` para reconciliação. | F3 e testes de abertura, indisponibilidade e reconciliação. |
| RF-05 | P0 | Propagar alterações cadastrais relevantes. | O CRM publica `CustomerUpdated.v1`; o consumidor atualiza sua projeção após registrar o `eventId`, sem substituir a fonte oficial. | Evento `CustomerUpdated.v1` e `test_atualizacao_cadastral_chega_a_contratos`. |
| RF-06 | P0 | Consultar o estado consolidado de uma operação. | Uma consulta por `correlationId` reúne auditoria e eventos associados à operação. | `GET /api/v1/operations/{correlation_id}` e roteiro de demonstração. |
| RF-07 | P0 | Consultar e reprocessar integrações com falha permanente. | Um operador autorizado consulta motivo, tentativas e correlação e agenda reprocessamento sem duplicar efeitos já confirmados. | Rotas de falha e `test_falha_permanente_pode_ser_listada_e_reprocessada`. |

## Requisitos não funcionais

| ID | Prioridade | Requisito | Critério de aceite | Rastreabilidade |
|---|---|---|---|---|
| RNF-01 | P0 | Interoperabilidade | APIs e eventos usam contratos versionados, JSON em UTF-8, UUID global, datas e horas ISO 8601 UTC e valores monetários decimais com moeda explícita. Inconsistências preservam a fonte oficial e ficam registradas. | OpenAPI, AsyncAPI, F1 e documentação de integração. |
| RNF-02 | P0 | Confiabilidade e tolerância a falhas | Fatos persistidos usam outbox; consumidores registram inbox; reentrega da mesma chave ou evento não duplica cobrança, processo ou chamado. Falhas permanentes preservam contexto para reprocessamento. | Testes de F1, F2, falha permanente e reprocessamento. |
| RNF-03 | P0 | Segurança e privacidade | Rotas protegidas exigem autenticação e papéis compatíveis; entradas são validadas; logs e eventos não expõem tokens, senhas, dados bancários, documentos completos ou descrição sensível do chamado. TLS é obrigatório fora do ambiente local. | Testes 403 e 422, revisão dos payloads e adaptador local de autenticação. |
| RNF-04 | P0 | Observabilidade | HTTP, logs, eventos, auditoria e erros propagam `correlationId`; health checks distinguem processo vivo de dependências prontas; métricas registram latência e falhas relevantes. | Middleware, `/health/live`, `/health/ready`, `/metrics` e consulta de operação. |
| RNF-05 | P0 | Manutenibilidade | Contextos de negócio comunicam-se por interfaces públicas e não importam modelos internos nem acessam tabelas de outro contexto. Mudança estrutural exige novo ADR. | Teste estático de fronteiras, ADR-001 e documentação TO-BE. |
| RNF-06 | P0 | Disponibilidade controlada | Uma indisponibilidade de Contracts não perde a solicitação de atendimento; o estado pendente permite reconciliação quando a dependência retorna. | Teste de indisponibilidade e reconciliação de F3. |
| RNF-07 | P0 | Desempenho da demonstração | Consultas locais do protótipo apresentam p95 inferior a 500 ms, excluindo atrasos deliberados dos simuladores. A medição registra amostra e ambiente. | `scripts/performance_smoke.py` e evidência de execução. |
| RNF-08 | P1 | Escalabilidade | APIs permanecem sem estado e consumidores idempotentes podem receber réplicas por fila quando métricas de latência, vazão ou idade da fila justificarem. | Estratégia de evolução e métricas operacionais; capacidade de produção ainda não validada. |
| RNF-09 | P0 | Testabilidade | A suíte cobre os três fluxos, autorização, validação, reentrega, indisponibilidade, falha permanente, contratos e fronteiras entre módulos. | `tests/test_flows.py` e `tests/test_contracts_and_architecture.py`. |

## Regras transversais

- CRM é a fonte oficial de cliente, contatos, consentimentos e oportunidade.
- Contracts é a fonte oficial de contrato, itens, vigência, plano e SLA.
- Finance é a fonte oficial de cobrança, vencimento, pagamento e inadimplência.
- Support é a fonte oficial de chamado, prioridade, histórico e resolução.
- Workflow é a fonte oficial de instância, tarefa, responsável, prazo e estado.
- Integration é a fonte oficial de IDs legados, correlação, outbox, inbox e
  falhas.
- REST atende comandos e consultas que exigem resposta imediata. Eventos
  representam fatos confirmados e efeitos desacoplados.
- Mudanças compatíveis são aditivas. Mudanças incompatíveis criam nova versão
  da API ou do evento.

## Escopo e dependências externas

A primeira entrega não substitui integralmente os cinco sistemas, não migra todo
o histórico e não demonstra alta disponibilidade real. Integrações com produtos
legados, TLS, OIDC corporativo e metas de capacidade dependem dos ambientes e
dados da organização.

As seguintes informações continuam como **Premissa a validar**: produtos e
tecnologias existentes, responsáveis por sistema, interfaces atuais, volumes,
SLAs operacionais e mecanismos reais de troca entre áreas. A validação pode
refinar adaptadores e metas, mas não deve transformar hipóteses em fatos nem
alterar uma decisão estrutural sem novo ADR.
