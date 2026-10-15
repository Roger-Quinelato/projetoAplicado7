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
- Defeito encontrado e corrigido: reutilizar a mesma `Idempotency-Key` ao gerar o rascunho de **outra** reserva com as mesmas condições devolvia `200` e vinculava a segunda reserva ao contrato da primeira; cancelar a segunda cancelava o contrato da primeira. O teste `test_f1_mesma_chave_em_outra_reserva_nao_vincula_contrato_alheio` falhou antes da correção (`200` em vez de `409`). A correção (contexto Contracts) inclui o `reservationId` na impressão digital idempotente do rascunho a partir da reserva (ADR-001, regra 11), e a resposta passa a ser `409 IDEMPOTENCY_CONFLICT`, já documentada no OpenAPI para essa rota. Na revisão do CTO, o teste `test_f1_chave_do_rascunho_direto_reaproveitada_na_reserva_retorna_409` (mesmas ou outras condições) cobre a chave usada antes em `POST /api/v1/contracts/drafts`; ele já passava antes da mudança, mas só porque o `endsOn` da reserva diferia, e agora a proteção é explícita. A interface não era afetada, pois gera uma chave por reserva.
- `scripts/demo_f1.py` contra a API local (versão revisada, banco novo): **20/20 checagens aprovadas**, código de saída `0`. A checagem 0b lê o `/openapi.json` publicado e confirma que `ReservationInput` e `ContractDraftCreate` não têm campos cadastrais e que o rascunho a partir da reserva não tem corpo. Correlação do caminho principal `8ae4300e-2aec-4fe9-ae69-88835174e4f1`; trilha com `crm.create_customer`, `contracts.create_reservation`, `contracts.create_draft` e `contracts.draft_from_reservation`. Ramificações: `422 VALIDATION_ERROR` (valor zero e moeda minúscula), `422 BUSINESS_RULE_VIOLATION` (cliente inexistente e cliente inativado após a reserva), `409 IDEMPOTENCY_CONFLICT` (chave em outra reserva, com o contrato original mantido `DRAFT`), `401`, `403` e `400` para correlação inválida, todos em problem+json com o `correlationId` enviado ou gerado.
- Controles negativos do script (versão inicial, 19 checagens, também `19/19` repetida no mesmo banco): papel sem permissão de CRM (`--token demo-finance`) encerrou com código `1` e a checagem divergente impressa; URL sem API encerrou com código `2`. O script não tem dependência específica de SO, mas foi executado só em Linux.
- Logs da API desta execução: linhas `422` com o `correlationId` de cada ramificação; nenhuma ocorrência de token ou cabeçalho `Authorization`.
- `cd web && npm run build`: concluído sem erro (frontend não alterado).
- Pendência registrada em `CRONOGRAMA_EXECUCAO.md`: timeout e retentativa limitada do adaptador do CRM (critério de F1 ainda parcial em RF-02).
- Não verificado: F1 na URL HTTPS pública (Render/Supabase), PostgreSQL real e timeout de rede de um CRM externo. O adaptador `CustomerReader` roda no mesmo processo, sem timeout configurado nem retentativa automática; a indisponibilidade é coberta só pelo simulador do teste. Nenhuma integração real com a Localiza.
