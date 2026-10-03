# Plano de ação priorizado

Referência auditada: `main` = `3a3d8bd`. As ações estão ordenadas por impacto e urgência; prazos internos vêm do `docs/CRONOGRAMA_EXECUCAO.md`. Nenhuma ação foi executada nesta auditoria: código, contratos, tickets e publicação permaneceram inalterados.

**Frentes responsáveis:**

- **F-REQ:** requisitos, progresso e entregas.
- **F-ARQ:** arquitetura e comportamento.
- **F-QSO:** qualidade, segurança e operação.

Cada ação cita os achados de `REGISTRO_ACHADOS.md` e as tarefas afetadas.

## Onda 0: imediata, antes de novas tarefas

| # | Ação | Achados | Frente | Dependências | Critério de aceite |
|---|---|---|---|---|---|
| P-01 | Publicar no remoto (branch + PR) os commits locais de `execucao-tarefas-pendentes` (`3fdb533`) ou registrar por que não foram publicados; repetir esta auditoria sobre o novo HEAD | AUD-50 | F-REQ | — | `git ls-remote` mostra o commit; PR aberto com CI; delta auditado contra este pacote |
| P-02 | Reabrir ou devolver para "Em revisão" ARCH7-1..5 no Jira, GitHub #4–#8 e Trello, até existir registro datado de revisão ou aprovação (T01 exige revisão docente; T05, aprovação) | AUD-07 | F-REQ | Validação docente (externa) | As quatro fontes mostram o mesmo status; cada "Concluído" tem link de evidência e `resolution` preenchida |
| P-03 | Corrigir a matriz de rastreabilidade: dividir SEC-01 (RBAC local atendido; OIDC como meta) e OBS-01 (correlação/logs/métricas atendidos; tracing como meta); DOC-01/03/04 e as linhas afetadas por AUD-01/04/20/21 passam a "Parcial"; incluir colunas de data e commit | AUD-08, AUD-14 | F-REQ | — | Nenhuma linha "Atendido" cita OIDC, traces ou figuras inexistentes; toda contagem de testes cita commit e run |

## Onda 1: confiabilidade do núcleo (antes de T13/T17, prazos 29/10 e 12/11)

| # | Ação | Achados | Frente | Dependências | Critério de aceite |
|---|---|---|---|---|---|
| P-04 | Despachante transacional: savepoint (`begin_nested`) por consumidor; `rollback()` no `except`; `attempts`/`last_error` gravados em transação própria; motivo com `type(exc).__name__` quando a mensagem vier vazia; `eventId`/`eventType` no log | AUD-01, AUD-12, AUD-31 | F-ARQ | — | Teste (SQLite **e** PG) injeta `IntegrityError` no consumidor: `attempts` cresce, evento chega a `FAILED` após `RETRY_LIMIT`, aparece em `/integration/failures` e os eventos seguintes são despachados no mesmo ciclo; nenhum efeito do consumidor que falhou fica persistido |
| P-05 | Exclusão mútua no despacho: `SELECT … FOR UPDATE SKIP LOCKED` em PG ou reivindicação por `UPDATE … SET status='DISPATCHING'`; lote limitado | AUD-11 | F-ARQ | P-04 | Teste concorrente em PG com N despachos paralelos: todos retornam 200; cada handler executa uma vez |
| P-06 | Ativação atômica: `UPDATE … WHERE status='DRAFT'` com checagem de `rowcount` ou `with_for_update()`; no frontend, desabilitar a ação durante o envio e reutilizar a chave por intenção | AUD-10, AUD-26 | F-ARQ | — | Duas ativações paralelas com chaves diferentes geram exatamente 1 `ContractActivated.v1`; duplo clique (Playwright) gera 1 requisição efetiva |
| P-07 | Separar a publicação no broker do consumo interno: estado próprio de publicação (ou segunda outbox); timeouts curtos do `pika` (`socket_timeout`, `blocked_connection_timeout`, `connection_attempts`); conexão reutilizada por despacho; documentar ou declarar a fila de auditoria | AUD-05 | F-ARQ | P-04 | Com broker indisponível, o evento fica consumido internamente, a falha de publicação tem motivo não vazio e o despacho de N eventos termina em tempo limitado e documentado |
| P-08 | Projeções com versão: carregar a versão ou `occurredAt` do agregado no `CustomerUpdated.v1`; aplicar só se for mais novo; registrar o descarte na auditoria | AUD-04 | F-ARQ | — | Teste "v1 falha → v2 aplicado → reprocessa v1" mantém v2 e registra o descarte |
| P-09 | Valores monetários na fronteira: `Field(gt=0, max_digits=14, decimal_places=2)` em todo `amount`; `currency` com `^[A-Z]{3}$`; quantizar antes de comparar; handler `DataError` → 422 | AUD-09, AUD-35 | F-ARQ | — | `0.001` e `1e15` → 422 em SQLite e PG; pagamento parcial 100.09 + 0.01 quita a fatura de 100.10 nos dois bancos |
| P-10 | Tipo monetário único nos contratos: string decimal com 2 casas (ou número documentado) em todas as rotas e eventos; corrigir `Money` do AsyncAPI e os exemplos nulos; teste que valida **cada** exemplo OpenAPI e envelope contra o schema, com `FormatChecker` | AUD-20, AUD-21, AUD-41 | F-ARQ | P-09 | Script de validação com 0 exemplos inválidos; envelopes com 0,07, 19,99 e 1234567,89 validam; `dueAt` com `Z` em SQLite e PG |

## Onda 2: endurecimento da demonstração pública (antes de T17/T20, prazos 12/11 e 26/11)

| # | Ação | Achados | Frente | Dependências | Critério de aceite |
|---|---|---|---|---|---|
| P-11 | REVOKE completo para `anon`/`authenticated`: todas as tabelas (inclusive `alembic_version`) e sequências, mais `ALTER DEFAULT PRIVILEGES`, ou schema não exposto pela Data API | AUD-23 | F-QSO | — | Em PG com papéis Supabase simulados e depois no Supabase real, `has_table_privilege('anon', t, …)` = false para todas as relações |
| P-12 | `/metrics` protegido no modo público e rotulado pelo template da rota | AUD-24 | F-QSO | — | N requisições com IDs distintos mantêm constante o número de séries; `/metrics` retorna 401 no modo público |
| P-13 | Atualizar FastAPI/Starlette para versões sem os advisories; lock com hashes (`pip-compile --generate-hashes` ou `uv lock`); `pip-audit` e `npm audit` no CI | AUD-25, AUD-49 | F-QSO | — | `pip-audit` sem achados aplicáveis; suíte verde; CI falha diante de vulnerabilidade nova |
| P-14 | Logs: incluir `exception.type/message` no JSON; remover a query string do log de acesso; cabeçalhos de segurança (CSP, `nosniff`, `frame-ancestors`, `Referrer-Policy`); 405 em `problem+json` | AUD-32, AUD-46, AUD-47 | F-QSO | — | Teste com `caplog` encontra o tipo da exceção; grep de e-mail nos logs = 0; teste de cabeçalhos passa |
| P-15 | Papéis no modo público: credenciais por papel ou somente leitura para visitantes; limitação de tentativas; registrar o risco aceito em ADR | AUD-34 | F-QSO | ADR novo | Papel não admin recebe 403 no modo público; ADR com o risco aceito |
| P-16 | Publicar no Render Free + Supabase Free somente após P-11..P-14; registrar URL HTTPS, `/health/ready`, escrita e leitura após reinício e revisão de segredos | AUD-42 | F-QSO | P-11..P-14, contas externas | Critério de T20 integralmente evidenciado, com data |

## Onda 3: qualidade verificável (T18, prazo 12/11)

| # | Ação | Achados | Frente | Dependências | Critério de aceite |
|---|---|---|---|---|---|
| P-17 | `DATABASE_URL` de teste configurável; job de CI com `postgres:16` (papéis anon/authenticated); testes de concorrência (P-05/P-06) e do evento venenoso (P-04); teste de RLS com conexão real | AUD-36 | F-QSO | P-04..P-06, P-11 | CI verde na matriz SQLite + PG; o teste de RLS falha se o REVOKE for removido |
| P-18 | Testes de navegador (Playwright) e acessibilidade (axe) no CI; corrigir contraste (≥ 4,5:1), `<main>` na tela de acesso e `role="alert"`; formulário preservado em erro; erros 422 traduzidos por campo; painel tolerante a 403 por coleção | AUD-26, AUD-27 | F-QSO | — | axe sem violações *serious*/*critical*; jornada F1–F3 por papel passa no CI |
| P-19 | Medir p95 das rotas de negócio F1–F3, além de `/health/ready`; teste HTTP de RF-06 (`/operations/{correlationId}`); reprocessar evento já consumido sem duplicar efeitos | AUD-36 | F-QSO | — | O relatório de desempenho cita rotas de negócio; os novos testes falham se a inbox for removida |
| P-20 | Corrigir o caso de borda de migração (esquema intermediário sem `alembic_version`) ou documentar o carimbo manual | AUD-33 | F-QSO | — | Teste por revisão intermediária passa em PG |

## Onda 4: completude funcional e fronteiras (T12, T15, T16; prazos 29/10 e 05/11)

| # | Ação | Achados | Frente | Dependências | Critério de aceite |
|---|---|---|---|---|---|
| P-21 | Máquina de estados de tarefa no domínio de Workflow; evento ou bloqueio para conclusão de `TICKET_RESOLUTION`; auditoria de transições; chave de idempotência em `POST /workflow/tasks` | AUD-30 | F-ARQ | — | Transições inválidas → 409 `INVALID_STATE`; conclusão reflete no Support |
| P-22 | Regra de encerramento decidida em ADR/TDD (fatura final, chamados abertos, preparação não executada como `CANCELLED`); Finance consome `ContractClosed.v1` | AUD-28 | F-ARQ | ADR | Testes de encerramento cobrem fatura e chamado aberto |
| P-23 | Inadimplência persistida e auditada (rotina explícita, data UTC); pagamentos com `audit()` e correlação | AUD-29 | F-ARQ | P-09 | `/operations/{correlationId}` mostra o pagamento; `OVERDUE` persistido e auditado |
| P-24 | API pública de `integration` para idempotência, outbox e falhas; retirar de `main.py` o acesso direto a `OutboxEvent`/`AuditLog`; ampliar o teste de fronteiras (todas as formas de import, incluir `integration`) ou adotar `import-linter` | AUD-22 | F-ARQ | — | O teste ampliado falha com os 7 casos sintéticos de E2-19 e passa no código corrigido |
| P-25 | Hexagonal incremental: casos de uso sem `HTTPException`; portas sem `Session`; adaptador `BrokerPublisher`; rotas de `main.py` movidas para os routers dos contextos | AUD-06 | F-ARQ | P-24 | Teste estático: nenhum `service.py`/`domain.py` importa `fastapi`; portas públicas não importam `sqlalchemy` |
| P-26 | Idempotência uniforme (`IdempotencyStore` com impressão digital completa) em todos os comandos; replay em vez de 409 sob corrida com a mesma chave; validações e códigos de erro alinhados a INTEGRACOES | AUD-39, AUD-40, AUD-48 | F-ARQ | — | Mesma chave com payload diferente → 409 em todos os comandos; mesma chave em paralelo → 2xx + `Idempotency-Replayed`; tabela de erros coberta por teste |

## Onda 5: documentação e entregáveis acadêmicos (T14, T19, T21, T22; prazos 29/10–10/12)

| # | Ação | Achados | Frente | Dependências | Critério de aceite |
|---|---|---|---|---|---|
| P-27 | Reescrever o relatório: ArchCorp como contratante e Localiza como contextualização da equipe; citar o `Guia.pdf`; trocar "simula tokens OIDC" por "tokens estáticos com RBAC"; alinhar §8 ao reprocessamento real (zera `attempts`); completar fundamentação (17 conceitos, citações diretas e indiretas), metodologia com integrantes e contribuições, ≥ 5 figuras (AS-IS, TO-BE, componentes/implantação, sequências F1–F3); reduzir quebras forçadas; definir o formato de página exigido | AUD-02, AUD-03 | F-REQ | P-04..P-10 (descrever o estado corrigido) | PDF renderizado com 15–20 páginas de conteúdo, figuras numeradas e citadas, nenhuma das frases incorretas, `Guia.pdf` nas referências, integrantes nomeados |
| P-28 | Regenerar os slides a partir de `main`: incluir APIs (endpoints e exemplo) e manutenção; corrigir o título do slide 11; números com data e commit; equipe; gerador portável (sem caminhos `C:/Users/...`) | AUD-17, AUD-38 | F-REQ | P-27 | Checklist dos 13 tópicos do guia sem lacunas; PPTX regenerado em CI Linux |
| P-29 | Atualizar TO-BE e DDD (6 eventos, tabelas reais); `ATRIBUTOS_QUALIDADE` (sem "OIDC simulado"; retentativa manual sem backoff); ADR-001:73 (fila no broker como meta, via novo ADR se mudar a decisão); ROTEIRO:313; `causationId` preenchido quando um fato decorrer de outro | AUD-13, AUD-37 | F-REQ / F-ARQ | — | TO-BE e DDD listam os eventos do AsyncAPI; busca por "OIDC simulado" sem resultado |
| P-30 | Fonte de verdade: corrigir `AGENT.md:39` para `Guia.pdf` (ou versionar o enunciado "Localiza", se existir); reescrever AS_IS:25-29, PLANO:52 e o contexto do ADR-001:12 separando o "confirmado pelo guia" (genérico) da especialização Localiza (premissa) | AUD-16 | F-REQ | — | O arquivo citado como fonte nº 1 existe; nenhuma frase atribui ao enunciado reservas, assistência 24h ou Localiza |
| P-31 | Alinhar status: coluna "status em <data>" no CRONOGRAMA com commit/PR; backlog como histórico; issues #9–#12 e Jira ARCH7-6..9 atualizados após o aceite de T06–T09; regra de responsáveis coerente com o Jira | AUD-15, AUD-43 | F-REQ | P-02 | Para cada Txx, as quatro fontes mostram o mesmo status e a mesma data |
| P-32 | T21: registrar URLs compartilháveis de Notion, Drive e GitHub Project, com data, sem segredos; fechar os marcos Q1/Q2 somente após o aceite | AUD-18 | F-REQ | Acesso às contas | Cada destino tem URL acessível ao revisor e data de conferência |
| P-33 | T14: seção de custos da demonstração (planos gratuitos, limites com fonte oficial datada, riscos de hibernação/pausa) e evolução comercial, com premissas marcadas | AUD-19 | F-REQ | — | Seção com fontes datadas; nenhum número sem fonte |
| P-34 | Transformar em subtarefas de T19 os achados abertos desta auditoria e da auditoria de 29/09 (`origin/ccr-1c5dff06-gdznnu`); decidir o destino do PR #29 | AUD-44 | F-REQ | — | Cada achado tem ticket com status |
| P-35 | T22: integrantes, contribuições individuais, revisão docente, ensaio e submissão | AUD-03 | F-REQ | P-27, P-28 | Pacote final com nomes, contribuições e registro da revisão docente |

## Itens de menor prioridade

- AUD-45: documentar como decisão explícita o chamado pendente sem adaptador de contrato.
- AUD-49 (parte de imagem): contêiner sem root e imagens fixadas por digest.

## Dependências críticas

Ordem crítica: **P-04 → P-05/P-07 → P-17 → P-16 (publicação) → P-27/P-28 (entregáveis descrevem o estado corrigido) → P-35**. P-01 e P-02 não dependem de código e devem ser feitos primeiro.
