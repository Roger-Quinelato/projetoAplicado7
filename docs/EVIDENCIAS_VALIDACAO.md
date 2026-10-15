# Evidências de validação

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Verificação atual em 27/09/2026

- `PYTHONPATH=src .venv/Scripts/python -m pytest -q tests -p no:cacheprovider`: **18 testes aprovados**, um aviso de depreciação de Starlette/AnyIO. Inclui reserva → contrato → fatura → pagamento simulado; chamado → resolução → workflow; segredo do modo público; idempotência, reconciliação e proteção RLS no modo PostgreSQL.
- `cd web && npm run build`: TypeScript e Vite concluídos sem erro, com `web/dist` gerado. Falta testar a interface no serviço HTTPS público.
- Inspeção local em navegador na mesma origem `http://127.0.0.1:8000/`: tela de acesso, painel e formulário CRM renderizaram; cadastro de cliente sintético apareceu na lista após escrita na API. A API respondeu `UP` em `/health/ready`. O teste HTTPS público continua pendente.
- `tools/build_report.py`: DOCX regenerado em 27/09/2026. `tools/build_presentation.mjs`: PPTX regenerado; recibo `.codex-finalizer/Apresentacao_Cenario_4.validation.json` mostra integridade, layout e reimportação aprovados. Revisão editorial final e preenchimento da equipe pendentes.
- Jira `ARCH7`: 22 tarefas T01–T22 criadas, com prioridade, data por semana e vínculos de bloqueio. Trello e Notion criados como índices/documentação; não há sincronização automática. Os respectivos IDs estão em `JIRA_SYNC.json`, `TRELLO_SYNC.json` e `NOTION_SYNC.json`.
- GitHub: [PR #2](https://github.com/Roger-Quinelato/projetoAplicado7/pull/2) atualizado com o commit de implementação; [22 issues T01–T22](https://github.com/Roger-Quinelato/projetoAplicado7/issues) criadas como índice, cada uma com link para o Jira. Sete marcos Q1–Q7 e etiquetas de semana, tipo, prioridade e status foram verificados nas issues T01 e T22. O GitHub Project ainda requer autorização do escopo `project`.
- Render e Supabase exigem autenticação do titular nas respectivas contas. Nenhuma URL pública, banco em nuvem ou persistência após reinício foi verificada até esta data.
- O modo público inclui RLS e revogação de acesso Data API `anon`/`authenticated` às tabelas em PostgreSQL. Essa proteção é definida no código e continua pendente de verificação em um projeto Supabase real.
- O [GitHub Actions Verify do PR #2](https://github.com/Roger-Quinelato/projetoAplicado7/actions/runs/36366105937) concluiu com sucesso em checkout limpo: suíte Python, instalação e build do frontend, e build da imagem Docker. Isso valida a construção, sem substituir o teste do serviço publicado.

As evidências de 13/09 e 14/09 abaixo são históricas e descrevem a versão anterior do protótipo.

## Execução em 13 de setembro de 2026

- Suíte automatizada: 13 testes aprovados em 4,11 segundos.
- Fluxo F1: rascunho criado a partir do UUID do CRM e repetição devolveu o mesmo contrato.
- Fluxo F2: repetição da ativação e novo despacho mantiveram uma cobrança e uma preparação de retirada.
- Fluxo F3: chamado recebeu SLA e iniciou uma instância de resolução.
- Degradação: atendimento e assistência 24h registrou `PENDING_ENTITLEMENT` e reconciliou após retorno de Contracts.
- Segurança: papel de atendimento e assistência 24h recebeu 403 ao tentar criar cliente.
- Falha permanente: evento chegou a `FAILED` após três tentativas, apareceu na consulta e voltou a `PENDING` por reprocessamento auditado.
- Reservas e contratos: o OpenAPI salvo corresponde ao `app.openapi()`, contém esquemas de resposta, exemplos dos três fluxos e UUID nos identificadores globais; o AsyncAPI contém três eventos com o envelope obrigatório, incluindo `causationId`.
- Arquitetura: teste estático não encontrou importação de modelos internos entre contextos de negócio.
- Desempenho local: 200 consultas de prontidão tiveram p95 de 6,36 ms, abaixo da meta de 500 ms no ambiente de teste local.

## Ambiente da execução

- Sistema operacional: Microsoft Windows NT 10.0.26200.0.
- Python: 3.12.14.
- Processador informado pelo ambiente: Intel64 Family 6 Model 142 Stepping 10.
- Banco dos testes e da medição: SQLite local.
- Comando da suíte: `python -m pytest -q tests -p no:cacheprovider` com `PYTHONPATH=src`.
- Comando da medição: `python scripts/performance_smoke.py` com `PYTHONPATH=src`.

O aviso de depreciação emitido pelo cliente de teste pertence à compatibilidade interna entre versões de Starlette e AnyIO. Ele não altera o resultado dos testes. A atualização dessas dependências deve ocorrer em uma tarefa de manutenção com nova execução da suíte.

## Limites da evidência

Os testes usam SQLite e adaptadores internos para rapidez. Docker Compose fornece PostgreSQL e RabbitMQ para a demonstração. A validação em infraestrutura externa, TLS, provedor OIDC real e produtos legados depende dos ambientes da organização e fica fora das informações fornecidas pelo enunciado.

## Inspeção dos artefatos em 14 de setembro de 2026

- A verificação final da suíte aprovou novamente os 13 testes; a execução completa levou 22,60 segundos e emitiu apenas o aviso de depreciação já registrado.
- Os sete blocos Mermaid de AS-IS, TO-BE, fluxos e planejamento foram renderizados em SVG sem erro pelo Mermaid CLI 11.17.0.
- O relatório técnico foi regenerado, renderizado em 18 páginas e inspecionado integralmente; não foram encontrados cortes, sobreposições, páginas vazias ou tabelas quebradas.
- A apresentação foi regenerada com 15 slides. Os validadores de integridade, geometria, fontes e reimportação aprovaram o pacote, e todos os slides foram inspecionados em PNG.

As imagens e recibos técnicos de verificação permanecem em `tmp/report-render-final/`, `tmp/presentation-build/`, `tmp/mermaid-render/` e `.codex-finalizer/`.

## Execução da sprint Q3 em 29 de setembro de 2026 (T06–T09)

Ambiente: contêiner Linux, Python 3.11.15, SQLite local e Node para o build da interface. Estes resultados acrescentam evidências às execuções anteriores, sem substituí-las.

- Suíte automatizada: 57 testes aprovados com `PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider`.
- Contratos: `python tools/export_openapi.py --check` confirmou o OpenAPI sincronizado com `app.openapi()`. O OpenAPI 3.1 passou no `openapi-spec-validator`, todas as respostas 2xx JSON têm exemplo e todos os erros usam `application/problem+json`.
- Eventos: o AsyncAPI descreve seis eventos (`CustomerUpdated.v1`, `ContractActivated.v1`, `ContractClosed.v1`, `TicketOpened.v1`, `TicketEntitlementReconciled.v1` e `TicketResolved.v1`). Os exemplos e os envelopes gravados na outbox durante os fluxos foram validados contra os schemas com `jsonschema`.
- Migrações: `upgrade head` em banco vazio não mostrou divergência entre migrações e modelos. O SQL gerado para PostgreSQL foi inspecionado no modo offline do Alembic, sem banco PostgreSQL real.
- Smoke HTTP com `uvicorn` e `curl`: cliente, reserva, rascunho a partir da reserva, ativação, despacho, encerramento e novo despacho; `GET /api/v1/operations/{correlationId}` mostrou `ContractActivated.v1` e `ContractClosed.v1` publicados e a auditoria de cada etapa; e-mail duplicado retornou `409` em `application/problem+json` com o mesmo `correlationId`.
- Desempenho local: `scripts/performance_smoke.py` mediu p95 de 5,74 ms em 200 consultas de prontidão.
- Interface: `npm run build` concluído.
- Não executado neste ambiente: `docker build` (sem daemon Docker no contêiner; o GitHub Actions executa o build) e qualquer verificação no Render/Supabase.

## Interface navegável em 14 de outubro de 2026 (T10)

Ambiente: contêiner Linux, Python 3.13, Node 22, SQLite local novo, API servida por `uvicorn archcorp.main:app --port 8000` com `web/dist` na mesma origem e Chromium (Playwright) sem interface gráfica.

- `cd web && npm run build`: `tsc -b` estrito e Vite concluídos sem erro.
- Suíte Python: 57 testes aprovados com `PYTHONPATH=src python3 -m pytest -q tests -p no:cacheprovider` (backend não alterado).
- Roteiro Playwright contra a API real, com tokens locais `demo-admin` e `demo-support`: navegação pelos cinco contextos com estados vazios; F1 cliente → reserva → rascunho com o mesmo `customerId`; F2 ativação → despacho → fatura → pagamento simulado; F3 elegibilidade → chamado de prioridade alta → despacho → atribuição → resolução; criação, início e conclusão de tarefa em Workflow; consulta de trilha por correlação.
- Erros exibidos de forma legível, com código HTTP, `code` e `correlationId`: `401` na tela de acesso (credencial inexistente), `403` ao criar cliente com `demo-support`, `422` de telefone fora do E.164 (campo traduzido) e de reserva com fim anterior ao início (regra do servidor), e falha de rede simulada pelo navegador. Os formulários preservam os dados após erro.
- Idempotência na interface (revisão do CTO): com falha ambígua simulada (a API grava, o navegador perde a resposta), o reenvio com campo corrigido usou chave nova e foi aceito sem `409`; o reenvio com corpo idêntico reaproveitou a chave e recebeu `Idempotency-Replayed: true`, sem duplicar a reserva; após um `409 IDEMPOTENCY_CONFLICT` simulado, a nova tentativa usou chave nova. Trocar o cliente no formulário de chamado preserva descrição e categoria e limpa apenas o contrato.
- Acessibilidade básica: rótulos associados aos campos, avisos em regiões `aria-live`, foco visível, link "Pular para o conteúdo", navegação por teclado entre contextos com foco movido ao título. Viewport de 390 px sem rolagem horizontal da página. Nenhum erro de JavaScript no console (apenas os registros de recurso do navegador para as respostas 4xx provocadas).
- Não verificado: interface na URL HTTPS pública, auditoria formal de acessibilidade (WCAG/leitor de tela) e teste automatizado de frontend versionado no repositório; o roteiro Playwright desta execução ficou fora do Git.

## Demonstração F1 em 14 de outubro de 2026 (T11)

Ambiente: contêiner Linux, Python 3.13.16, Node 22, SQLite local novo e API servida por `PYTHONPATH=src uvicorn archcorp.main:app --port 8000` com tokens locais. Dados sintéticos; nenhum sistema da Localiza foi acessado.

- Suíte Python: **74 testes aprovados** com `PYTHONPATH=src python3 -m pytest -q tests -p no:cacheprovider` (57 anteriores + 17 casos novos em `tests/test_f1_cliente_reserva_contrato.py`, após a revisão do CTO), um aviso de depreciação Starlette/AnyIO já conhecido. `python3 tools/export_openapi.py --check` confirmou o OpenAPI sem alteração.
- Casos novos de F1: caminho cliente → reserva → rascunho sem corpo, com `customerId` do CRM e nome/e-mail do contrato projetados do CRM; esquemas `ContractDraftCreate` e `ReservationInput` sem campos cadastrais; idempotência do rascunho a partir da reserva; cliente inexistente ou sem consentimento rejeitado com problem+json, sem contrato, vínculo nem chave consumida; oito violações estruturais com `422` e `loc` do campo; `Idempotency-Key` ausente, reserva inexistente, `401` e `403` nas duas rotas de rascunho; indisponibilidade simulada do `CustomerReader` (`TimeoutError`) com `500 INTERNAL_ERROR` (comportamento atual, não contrato-alvo), log `ERROR` com a correlação, nenhum efeito parcial e repetição segura com a mesma chave; `correlationId` do HTTP na auditoria e em `GET /api/v1/operations/{correlationId}`, inclusive quando a API gera o UUID.
- Defeito encontrado e corrigido: reutilizar a mesma `Idempotency-Key` ao gerar o rascunho de **outra** reserva com as mesmas condições devolvia `200` e vinculava a segunda reserva ao contrato da primeira; cancelar a segunda cancelava o contrato da primeira. O teste `test_f1_mesma_chave_em_outra_reserva_nao_vincula_contrato_alheio` falhou antes da correção (`200` em vez de `409`). A correção (contexto Contracts) inclui o `reservationId` na impressão digital idempotente do rascunho a partir da reserva, mantendo a operação `create_contract_draft`, e a resposta passa a ser `409 IDEMPOTENCY_CONFLICT`, já documentada no OpenAPI para essa rota. Na revisão do CTO, o teste `test_f1_chave_do_rascunho_direto_reaproveitada_na_reserva_retorna_409` (mesmas ou outras condições) cobre a chave usada antes em `POST /api/v1/contracts/drafts`; ele já passava antes da mudança, porque o `endsOn` da reserva já diferencia os pedidos; quem isola a inclusão do `reservationId` é `test_f1_mesma_chave_em_outra_reserva_nao_vincula_contrato_alheio`. A interface não era afetada, pois gera uma chave por reserva.
- `scripts/demo_f1.py` contra a API local (versão revisada, banco novo): **20/20 checagens aprovadas**, código de saída `0`. A checagem 0b lê o `/openapi.json` publicado e confirma que `ReservationInput` e `ContractDraftCreate` não têm campos cadastrais e que o rascunho a partir da reserva não tem corpo. Correlação do caminho principal `8ae4300e-2aec-4fe9-ae69-88835174e4f1`; trilha com `crm.create_customer`, `contracts.create_reservation`, `contracts.create_draft` e `contracts.draft_from_reservation`. Ramificações: `422 VALIDATION_ERROR` (valor zero e moeda minúscula), `422 BUSINESS_RULE_VIOLATION` (cliente inexistente e cliente inativado após a reserva), `409 IDEMPOTENCY_CONFLICT` (chave em outra reserva, com o contrato original mantido `DRAFT`), `401`, `403` e `400` para correlação inválida, todos em problem+json com o `correlationId` enviado ou gerado.
- Controles negativos do script (versão inicial, 19 checagens, também `19/19` repetida no mesmo banco): papel sem permissão de CRM (`--token demo-finance`) encerrou com código `1` e a checagem divergente impressa; URL sem API encerrou com código `2`. O script não tem dependência específica de SO, mas foi executado só em Linux.
- Logs da API desta execução: linhas `422` com o `correlationId` de cada ramificação; nenhuma ocorrência de token ou cabeçalho `Authorization`.
- `cd web && npm run build`: concluído sem erro (frontend não alterado).
- Pendência registrada em `CRONOGRAMA_EXECUCAO.md`: timeout e retentativa limitada do adaptador do CRM (critério de F1 ainda parcial em RF-02).
- Não verificado: F1 na URL HTTPS pública (Render/Supabase), PostgreSQL real e timeout de rede de um CRM externo. O adaptador `CustomerReader` roda no mesmo processo, sem timeout configurado nem retentativa automática; a indisponibilidade é coberta só pelo simulador do teste. Nenhuma integração real com a Localiza.

## Estabilização v1 — regressões de integração e privacidade (2026-10-15)

Base: `5e344e2`. Os 74 testes existentes e duas caracterizações do atendimento
passaram; os dois novos casos de outbox/privacidade falharam antes da correção.
`tests/test_reliability_regressions.py` reproduz flush SQL inválido após efeito
parcial, verifica rollback, continuidade, esgotamento, reprocessamento e reentrega,
e impede eco de dados sintéticos nos erros de validação e logs.
Os códigos v1 caracterizados são `CONFLICT` na resolução repetida sem chave e
`INVALID_STATE` na reconciliação repetida sem chave. Nenhum deploy foi executado.

Após a correção: `PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider`: **78 passed** em SQLite. PostgreSQL ainda não executado nesta etapa.

### Correções da revisão na camada #35 (2026-10-15)

- Despachante da outbox: consumidores e broker em SAVEPOINT; a tentativa é
  registrada na transação que mantém o bloqueio do evento. Ajuste do pysqlite
  (`BEGIN` explícito) em `infrastructure/db.py`.
- `tests/test_reliability_regressions.py`: dois casos novos (SAVEPOINT após só
  leitura não confirma a transação externa; nenhuma fronteira de transação entre
  a falha do consumidor e o registro da tentativa). Ambos falharam antes da correção.
- Interface: `describeIssue` deixa de exibir `?`, `0` ou texto vazio sem `ctx` e
  identifica e-mail pelo campo. `web/tests/api.test.ts` (4 casos, `node:test`):
  3 falharam antes da correção. Passo `npm test` adicionado ao job `application`.
- Local (Python 3.13, Node 22): `PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider`:
  **80 passed** em SQLite; `cd web && npm test`: 4 passed; `npm run build`: sem erro.
- RabbitMQ: publisher confirms, `mandatory=True` e fila durável `archcorp.events.all`
  (`#`). Dois testes com `pika` simulado: a configuração do canal (falhou antes da
  correção) e a mensagem sem rota mantendo o evento `PENDING` sem efeitos
  (caracterização: qualquer exceção do broker já contava como falha).
  Após a mudança: **82 passed** em SQLite.
- Revisão operacional do broker: limites de conexão bloqueada, socket, heartbeat e
  tentativa única; fila com `x-max-length` e `reject-publish`; métrica de
  profundidade; falha ao gravar a tentativa desfaz a transação, registra
  `attempt_not_recorded` e interrompe o lote. Testes com `pika` simulado: ordem
  `connect → declare → bind → confirm_delivery → basic_publish → close` e falha em
  cada etapa (6 casos); teste da interrupção do lote. O teste de ordem/limites e o
  de interrupção falharam antes da mudança. Job `rabbitmq` na CI com RabbitMQ 3.13
  real (`tests/test_rabbitmq_real.py`). Local: **88 passed, 2 skipped** em SQLite.
- Não verificado nesta etapa: PostgreSQL (o job e os testes de concorrência entram
  na camada #37) e disputa real entre dois despachantes. RabbitMQ real só na CI.

## Financeiro em 14 de outubro de 2026 (T12)

Ambiente: contêiner Linux, Python 3.13.16, Node 22.22.0, SQLite local e API servida por `PYTHONPATH=src uvicorn archcorp.main:app --port 8011` com banco SQLite novo e `FINANCE_ALLOW_FUTURE_AS_OF=true` (simulação local da data de referência). Tokens locais, dados sintéticos; nenhum sistema da Localiza, PSP ou banco real foi acessado. Resultados do commit final da branch `feat/t12-financeiro`, com as correções das duas revisões do CTO.

- Suíte Python: **122 testes aprovados** com `PYTHONPATH=src python3 -m pytest -q tests -p no:cacheprovider` (74 anteriores + 47 em `tests/test_finance.py` + 1 em `tests/test_foundation.py`), um aviso de depreciação Starlette/AnyIO já conhecido. `test_f2_ativacao_cria_uma_cobranca_e_uma_preparacao_de_retirada` continua aprovado sem alteração.
- Casos de `tests/test_finance.py`: transições permitidas e proibidas da fatura; estado e saldo após pagamento parcial, total, em fatura inadimplente, sobrepagamento, fatura quitada (`CONFLICT`) e cancelada (`INVALID_STATE`); vencimento pela data UTC com relógio injetado (23:30 em UTC−3 já conta como o dia seguinte; no próprio `dueDate` não vence); ciclos iniciados por ciclo de cobrança, inclusive fim de mês; primeira fatura e fatura final idempotentes por `eventId`; encerramento sem valor restante idempotente fora da inbox (marcador; uma única auditoria); primeira fatura cancelada não é recobrada no encerramento; encerramento sem primeira fatura falha sem efeito; verificação de vencimento determinística, idempotente e auditada; fluxo completo pela API; validações `422`/`409`/`404` com os códigos da v1; cancelamento; data futura bloqueada sem a simulação e, com `PUBLIC_DEMO`, recusada pelo serviço e na inicialização; matriz de papéis; reentrega de `ContractClosed.v1` pelo despachante e com o registro da inbox apagado; migração `0004` sobre faturas antigas; downgrade da `0004` sem fatura `FINAL` (volta à 0003) e com `FINAL` (bloqueado antes de alterar dados, revisão mantida em 0004); SQL PostgreSQL offline.
- Guarda de migração (`tests/test_foundation.py`): analisa a AST do `upgrade`; além das operações anteriores, recusa `drop_constraint`, `drop_index` e qualquer `.execute(...)` (inclusive pela conexão) com SQL `UPDATE`, `DELETE`, `DROP`, `ALTER`, `RENAME` ou `TRUNCATE`, e recusa `.execute` com argumento não literal (f-string, `sa.text`, variável). As exceções em `MIGRATION_EXCEPTIONS` são por operação e contagem exata, com data e ADR; a única é a `0004` (1 `drop_constraint`, 1 `UPDATE`; ADR-003). Um teste dedicado cobre cada forma de contorno.
- Infraestrutura de teste: `tests/conftest.py` passou a apagar `alembic_version` junto com as tabelas. Sem isso, um banco de teste local antigo (carimbado em `0003`) fazia a inicialização reaplicar a `0004` sobre o esquema já criado por `create_all`; em checkout limpo o problema não aparece.
- Contratos: `PYTHONPATH=src python3 tools/export_openapi.py --check` aprovado após regenerar `docs/api/openapi.yaml`. Códigos `code` da v1 preservados: moeda diferente da fatura continua `422 VALIDATION_ERROR` e pagamento em fatura quitada continua `409 CONFLICT`; `INVALID_STATE` e `BUSINESS_RULE_VIOLATION` só nos caminhos novos (fatura cancelada, cancelamento inválido, data de referência futura). Mudanças aditivas: campos `kind`, `balance`, `delinquent`, `overdueSince` e `sourceEventId`; status `PARTIALLY_PAID` e `CANCELLED` no enum; filtro `contractId`; cabeçalho opcional `Idempotency-Key` e resposta `Idempotency-Replayed` no pagamento; rotas `POST /api/v1/finance/invoices/overdue-check` e `POST /api/v1/finance/invoices/{id}/cancel`. Mudanças não aditivas aceitas no ADR-003 (protótipo acadêmico, sem cliente externo da v1, integridade monetária): valor com mais de duas casas passa a `422 VALIDATION_ERROR` (antes era aceito e arredondado silenciosamente na gravação); fatura em aberto com pagamento parcial passa de `OPEN` a `PARTIALLY_PAID` (também nos dados, pela 0004); o `detail` do pagamento em fatura quitada passa de "Pagamento excede saldo da fatura" a "Fatura já quitada" (status e `code` preservados). Valores monetários seguem `number` (float) na v1: desvio da regra de decimal registrado como dívida para a v2. AsyncAPI: nenhum evento novo; descrições dos consumidores atualizadas e premissas marcadas.
- Demonstração contra `uvicorn` (script fora do Git, saída arquivada fora do repositório): **20/20 checagens aprovadas**, correlação `9b3b08f6-360d-482c-bb26-8c9e62bf2ecb`. Sequência: cliente → rascunho → ativação → despacho → fatura `INITIAL` `OPEN` de R$ 2.500 com vencimento 25/10/2026 (data UTC do evento 15/10 + 10) → pagamento parcial de R$ 1.000 (`PARTIALLY_PAID`, saldo 1.500) → replay com a mesma chave (`Idempotency-Replayed: true`, mesmo `paymentId`) → mesma chave com outro valor (`409 IDEMPOTENCY_CONFLICT`) → sobrepagamento (`409 CONFLICT`) → moeda USD (`422 VALIDATION_ERROR`) → verificação com `asOf` 25/10 (nada marcado) → `asOf` 26/10 (fatura marcada) → repetição (nada novo, `alreadyOverdue: 1`) → fatura `OVERDUE`, `delinquent: true` → pagamento de R$ 1.500 (`PAID`, saldo 0, `overdueSince` mantido) → novo pagamento (`409 CONFLICT`) → encerramento com fim em 08/01/2027 → despacho → fatura `FINAL` de R$ 7.500 com `sourceEventId` do encerramento → trilha com `create_first_invoice`, `record_simulated_payment`, `evaluate_overdue`, `mark_invoice_overdue` e `create_final_invoice`.
- Inicialização com `PUBLIC_DEMO=true` e `FINANCE_ALLOW_FUTURE_AS_OF=true`: `uvicorn` encerrou com código `3` e `RuntimeError: FINANCE_ALLOW_FUTURE_AS_OF é simulação local e não pode ser usada com PUBLIC_DEMO`.
- Logs da API da demonstração: 58 linhas, nenhuma ocorrência de token, cabeçalho `Authorization` ou referência de pagamento.
- `cd web && npm run build`: concluído sem erro com a tela Financeiro ajustada (tipo da fatura, saldo da API, coluna Inadimplência, verificação de vencimento, `Idempotency-Key` no pagamento e premissas indicadas no texto). A tela não foi exercitada em navegador nesta execução.
- Diagramas novos de `FLUXOS_INTEGRACAO.md` (ciclo de vida da fatura e verificação de vencimento) validados pelo renderizador Mermaid.
- Observações fora do escopo: o `JsonFormatter` de `observability.py` grava o horário local com sufixo `Z` (na execução, horário local `21:40Z` para 00:40 UTC); o encerramento de contrato usa `date.today()` local como data padrão (`contracts/service.py`, limitação pré-existente). Os dados de negócio da T12 (`overdueSince`, `evaluatedAt`, vencimento, auditoria) estão em UTC.
- Não verificado: roteiro PowerShell do `ROTEIRO_DEMONSTRACAO.md` (sem PowerShell no contêiner; a mesma sequência foi executada pelo script Python), Docker Compose, PostgreSQL real (só SQL offline), concorrência real de pagamentos (o bloqueio `FOR UPDATE` é ignorado pelo SQLite), URL HTTPS pública, PSP, nota fiscal e qualquer sistema da Localiza.

## Integração financeira com estabilização v1 (2026-10-15)

T12 original `9c655cf`, integrada sobre a correção da outbox `ff0094a`.
A suíte integrada passou com **127 testes** em SQLite antes do reforço da guarda;
a guarda agora inspeciona helpers locais alcançáveis, aliases simples de operações
Alembic e `exec_driver_sql`, além de `execute`, sem alterar as exceções por contagem
do ADR-003. O teste adicional cobre helper destrutivo fora de `upgrade`.
Preservados o bloqueio de downgrade com FINAL antes de alterações, os códigos
financeiros existentes, a proibição de data futura no modo público e o marcador
idempotente da fatura final sem saldo. Prazo de dez dias e cálculo por ciclo iniciado
continuam premissas; valores float na saída são dívida para futura API v2.
## Atendimento completo em 14 de outubro de 2026 (T15)

Ambiente: contêiner Linux, Python 3.13.16, Node 22.22.0, SQLite local e API servida por `PYTHONPATH=src uvicorn archcorp.main:app --port 8001` com banco próprio (`DATABASE_URL=sqlite:///./tmp/demo-t15.db`) e tokens locais. Dados sintéticos; nenhum sistema da Localiza, central de atendimento ou ITSM foi acessado.

- Suíte Python: **122 testes aprovados** com `PYTHONPATH=src python3 -m pytest -q tests -p no:cacheprovider` (74 anteriores, sem alteração de asserções, + 48 casos em `tests/test_t15_atendimento.py`), um aviso de depreciação Starlette/AnyIO já conhecido.
- Contratos: `PYTHONPATH=src python3 tools/export_openapi.py --check` aprovado após regenerar o OpenAPI. Mudanças aditivas na v1: campos opcionais `openedAt`, `resolvedAt` e `slaStatus` nas respostas de chamado; `RESOLVED` no enum de `TicketResponse`; rotas novas `GET /api/v1/support/tickets/{ticketId}/history` e `POST /api/v1/support/tickets/reconcile-pending`; `503` documentado na reconciliação; cabeçalho `Idempotency-Replayed` na resolução e na reconciliação. O AsyncAPI ganhou os mesmos três campos opcionais nos payloads de chamado e um exemplo de `TicketOpened.v1` pendente; exemplos e envelopes gravados validaram contra os schemas.
- Endurecimentos de entrada (não aditivos, por privacidade e consistência com Contracts): `serviceCode` com 2 a 80 caracteres; descrição e responsável rejeitam documento, cartão, telefone (11 dígitos ou mais), placa e e-mail com `422`; resolução e atribuição fora da máquina de estados passam a responder `409 INVALID_STATE` (antes `409 CONFLICT`); resolução repetida passa de `409` para `200` idempotente.
- Migração aditiva `0004_support_sla_history`: cria `support_ticket_history` e as colunas anuláveis `opened_at`, `reconciled_at` e `resolved_at`. Sem divergência entre modelos e migrações; teste dedicado aplica `0003` → `head` com um chamado existente e confirma que ele permanece legível (`openedAt` nulo). O fixture de testes passou a remover `alembic_version` junto com as tabelas, porque um banco de teste local carimbado em `0003` falhava ao receber a migração nova.
- Casos novos: máquina de estados completa (todas as combinações), prioridade, prazo e `slaStatus` com relógio injetado (`WITHIN` no instante do prazo, `BREACHED` um segundo depois, `MET`/`BREACHED` fixados na resolução); serviço com porta falsa de Contracts (elegível, `ContractsUnavailableError`, `TimeoutError`, `ConnectionError`); idempotência da abertura (mesmo corpo, outro relato com `409`, registro anterior à T15 sem impressão digital, chave não consumida em `422`); seis violações de fronteira com `422` sem chamado; log `WARNING` com correlação e sem descrição; atribuição, repetição sem efeito e reatribuição com histórico, auditoria e papel (nunca o token); resolução idempotente com um único `TicketResolved.v1`; reconciliação com `503` sem efeito, prazo contado da abertura após 3 h de indisponibilidade, repetição sem novo evento, rejeição com cancelamento do processo em Workflow; lote com `503`, confirmação/rejeição, repetição vazia e interrupção no meio do lote preservando o que foi confirmado; reentrega de `TicketOpened.v1` e `TicketResolved.v1` sem duplicar processo nem inbox; envelopes dos três eventos de chamado contra o AsyncAPI; matriz 401/403 nas oito rotas de atendimento.
- Demonstração real (roteiro Python com `httpx`, mantido fora do Git) em três fases com reinício do servidor: **32/32 checagens aprovadas** (fase A 15/15 com Contracts disponível; fase B 4/4 com `CONTRACT_ADAPTER_AVAILABLE=false`; fase C 13/13 com Contracts de volta). Cobriu abertura `OPEN`/`HIGH`/8 h com `dueAt` = `openedAt` + 8 h, repetição idempotente, `409 IDEMPOTENCY_CONFLICT`, `422` para descrição com CPF, `403` (finance, operations) e `401`; atribuição, repetição e reatribuição; resolução `MET` e repetição idempotente com um único evento despachado; processo de resolução `COMPLETED`; histórico `OPENED, ASSIGNED, REASSIGNED, RESOLVED`; trilha por `correlationId` com Support e o consumidor de Workflow; três chamados pendentes, `503` individual e em lote; após reinício, chamado ainda pendente, reconciliação individual com prazo contado da abertura, repetição com `Idempotency-Replayed: true`, lote com 1 confirmado e 1 rejeitado, lote repetido vazio, prazo ajustado em Workflow e processo cancelado para o rejeitado, `409 INVALID_STATE` ao resolver o rejeitado.
- Logs da API nas três fases: nenhuma ocorrência de token, cabeçalho `Authorization`, descrição de chamado ou do CPF enviado; a indisponibilidade aparece como `WARNING` com `operation: support_entitlement`, `result: unavailable` e o `correlationId`.
- Interface: `cd web && npm ci && npm run build` concluídos (`tsc -b` estrito e Vite). Atendimento ganhou coluna SLA, histórico por chamado, rótulo de reatribuição e botão **Reconciliar pendentes**. Não houve roteiro de navegador nesta execução.
- Diagramas: os seis blocos Mermaid de `docs/arquitetura/FLUXOS_INTEGRACAO.md`, inclusive o novo ciclo de vida do chamado, renderizaram sem erro com Mermaid CLI.
- Observado e fora do escopo: o processo `TICKET_RESOLUTION` de Workflow recebe prazo pela hora do despacho e expõe `dueAt` sem sufixo `Z`; `GET /api/v1/operations/{correlationId}` devolve `occurredAt` da auditoria sem fuso; o carimbo dos logs JSON usa hora local com sufixo `Z`. Registrado para T16/T17.
- Não verificado: interface no navegador, PostgreSQL real, URL HTTPS pública, timeout de rede de um Contracts externo (adaptador no mesmo processo) e qualquer integração com central de atendimento ou sistemas da Localiza.

## Estabilização integrada do atendimento (2026-10-15)

T15 original `6683b83`, integrada sobre T12 validada. Corrigidas as expectativas
da T15 que contrariavam o contrato v1 aprovado: sem chave há conflito; rejeições
por regex da descrição/responsável foram retiradas (ADR-004). Casos novos verificam
replay persistido após mudança de estado, chave cruzada entre recursos/comandos,
e papel autorizado. A migração de convergência preserva dados a partir da 0003 e
de cada 0004 publicada, mantém uma head e bloqueia downgrade com FINAL.

Execução local: **178 passed, 6 skipped** (SQLite; skips são exclusivamente
PostgreSQL). `npm ci --prefix web` e `npm run build --prefix web` aprovados. CI
PostgreSQL 16 configurada, mas execução ainda não confirmada nesta evidência.
Sem Docker, deploy ou acesso a sistemas reais.

### Conferência posterior do baseline v1 (2026-10-15)

A CI do SHA `15c9a4e` passou, incluindo PostgreSQL 16 (migrações e concorrência),
frontend e Docker: https://github.com/Roger-Quinelato/projetoAplicado7/actions/runs/38670396112.
Comparação com main `5e344e2` identificou limites novos de serviceCode e regex
nova na moeda: foram retirados para preservar a fronteira v1. TicketResponse
mantém enum de abertura/reconciliação; TicketDetailResponse continua incluindo
RESOLVED. Após ajustes: **177 passed, 6 skipped** em SQLite; CI será repetida no
SHA final. A retirada de dois casos de rejeição de serviceCode foi compensada
pela manutenção do teste de tamanho da descrição; elegibilidade não mudou.

Na auto-revisão final, a métrica de falhas passou a incrementar somente após o
commit da tentativa. Testes adicionais verificam falha de commit sem contagem
antecipada e preservação do evento anterior já confirmado. Exemplos 422 e de
replay foram alinhados ao comportamento. Suíte local após o ajuste: **179 passed,
6 skipped**; PostgreSQL novamente coberto pela CI do SHA final.

### Concorrência real da outbox em PostgreSQL (camada #37, 2026-10-15)

- `tests/test_postgresql_concurrency.py`, dois casos novos com dois despachantes em
  conexões separadas:
  - enquanto o consumidor de A falha segurando o `FOR UPDATE`, o despachante B
    pula o evento (`processed 0, failed 0`); ao final `attempts == 1`, o consumidor
    rodou uma vez e nenhum efeito ou inbox ficou gravado;
  - com consumidor que sempre falha, dois despachantes em laço levam o evento a
    `FAILED` com `attempts == retry_limit`, igual ao número de execuções, e nunca
    há execução simultânea do mesmo evento.
- Limite: os dois casos também passam com o despachante anterior (`ff0094a`); eles
  provam exclusão mútua e contagem em PostgreSQL real, não a janela entre rollback e
  novo bloqueio. A demonstração determinística dessa janela continua sendo o teste de
  sequência em SQLite da camada #35.
- Local (PostgreSQL 16, Python 3.13), após integrar as correções do #35:
  `TEST_DATABASE_URL=... PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider`:
  **191 passed** em PostgreSQL; em SQLite, 183 passed e 8 skipped (exigem PostgreSQL).

## Refatoração estrutural posterior à estabilização (2026-10-15)

Rotas de Contracts, Support e Integration saíram de main.py; schemas pertencem
a seus módulos e imports antigos continuam disponíveis por fachada. Negócios
usam integration.public, sem importar seus modelos/serviço internos. ADR-005
registra a decisão e a avaliação limitada do PR29, que não foi integrado.
O OpenAPI produzido após a extração foi comparado integralmente com o conjunto
de suporte corrigido e é idêntico. Não há mudança de API/evento nesta extração.

A proteção de compatibilidade usa fixture separado da main 5e344e2 e duas
exceções exatas do ADR-003; seu teste negativo detecta restrição nova na descrição,
rota removida e cabeçalho obrigatório. Fronteiras, domínio puro e identidade dos
imports legados têm testes específicos. A CI PostgreSQL executa a mesma suíte.

Suíte estrutural final local: **184 passed, 6 skipped** (PostgreSQL ausente local),
OpenAPI conferido, `ruff --select F,E9` e `git diff --check` aprovados. A guarda de
migração mantém também o objeto exato da restrição removida e o UPDATE exato da
exceção ADR-003, além da contagem. CI do suporte final `2cadab6` passou em
https://github.com/Roger-Quinelato/projetoAplicado7/actions/runs/38713887061.
A execução da CI da extração será conferida no SHA publicado; deploy público
permanece pendente.
