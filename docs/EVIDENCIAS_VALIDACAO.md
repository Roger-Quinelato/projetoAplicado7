# Evidências de validação

> O estado atual de execução está no [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e no [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Sincronização da documentação com a `main` (parte do #65, 2026-10-22)

Base: `origin/main` em `2b59136` (inclui os PRs #67, #71 e #72). Ambiente: Windows 11 (10.0.26300), Python 3.12.10, SQLite. Só a documentação mudou.

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte Python, SQLite puro | `PYTHONPATH=src python -m pytest -q -p no:cacheprovider` | **233 aprovados, 14 ignorados** (exigem PostgreSQL ou RabbitMQ reais) em 5 min 34 s; o teste a mais em relação ao #62 veio do PR #67 (`tests/test_flows.py`) |
| Contrato REST | `python tools/export_openapi.py --check` | atualizado (saída 0) |
| Contrato de eventos | comparação dos `eventType` emitidos em `src/` com `docs/events/asyncapi.yaml` | os seis eventos coincidem; nenhum payload mudou desde 15/10/2026 |

- Documentos ajustados ao código: `CRONOGRAMA_EXECUCAO.md` (status T12–T22 com as issues dos pacotes, tabela A–J, pendência das duas cabeças do Alembic resolvida pela `0005`), `ESTADO_IMPLEMENTACAO.md` (revisão do #67, limite de 200 registros dos indicadores, axe bloqueante), `TESTES_E2E.md` (axe com asserção), `MATRIZ_RASTREABILIDADE.md` (linha WF-01, convergência das migrações, contagens de 20/10), README (variáveis `RABBITMQ_*`, Compose isolado, `broker` em `/health/ready`) e o cabeçalho do `AGENTS.md`.
- Não executado nesta rodada: suítes com PostgreSQL e RabbitMQ reais, `npm test`, roteiros Playwright, Compose com Docker, geradores do DOCX e do PPTX, publicação (T20, #64).

## Viabilidade e documentos (#63 e parte do #65, 2026-10-20)

Base: branch `aceite-integrado` (B–F integrados). Ambiente: contêiner Linux, Python 3.13, LibreOffice para a conversão em PDF.

| Verificação | Resultado |
|---|---|
| Suíte Python com PostgreSQL 16 e RabbitMQ 3.12 locais | 246 aprovados, 0 ignorados (só documentação mudou) |
| Suíte Python com SQLite puro | 232 aprovados, 14 ignorados |
| `tools/build_report.py` | DOCX regenerado com as contagens e o p95 de 20/10/2026. Renderizado pelo LibreOffice: **21 páginas, 20 sem a capa**. A paginação no Word pode variar; o limite de 15–20 p. depende de a capa contar e precisa ser conferido na exportação final |
| `tools/build_presentation.mjs` | Fonte atualizada (246 testes, p95 até 45,1 ms, "serviços gratuitos (não custo zero)"). **PPTX não regenerado**: o gerador depende de `@oai/artifact-tool`, ausente neste ambiente. O `output/Apresentacao_Cenario_4.pptx` versionado ainda mostra "211 testes" e "p95 4,22 ms" e deve ser regenerado localmente |
| Placeholders | Só "nomes a preencher" na capa do relatório e dos slides (`EQUIPE`, pacote J) |
| Regressões documentais (grep) | Nenhum texto equipara correlação a tracing distribuído, descreve o RabbitMQ como executor dos consumidores ou dá o ADR-006 como aprovado (status: proposto) |
| Afirmações de custo | "Custos zero" só aparece no título da T14 em `CRONOGRAMA_EXECUCAO.md` (igual ao da issue #17), sem afirmar economia. Relatório e slides passam a dizer "plano gratuito" e "não custo zero" |

- `VISAO_NEGOCIO.md` separa três custos (serviços, implementação e operação), liga cada benefício ao que o protótipo mede hoje e lista as quatro premissas para validação docente, com o código e o teste de cada uma.
- O aviso de "estado de execução em 27/09/2026", repetido em 17 documentos, perdeu a data vencida e passa a só apontar para o estado e o cronograma.
- Não verificado: contagem de páginas no Word, PPTX regenerado e publicação (T20, #64).

## Aceite integrado e operacional local (#62, 2026-10-20)

Versão: branch `aceite-integrado`, commit `eb7ca1b` (pacote F) sobre a integração de #57, #68, #69 e #70 (merge `9d08a0a`). Ambiente: Linux (contêiner), Python 3.13, Node 22, Chromium 1194, **PostgreSQL 16.15** e **RabbitMQ 3.12.1** locais, descartáveis, com dados sintéticos. Docker indisponível no contêiner: o Compose foi validado só com `docker compose config`.

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte Python, PostgreSQL + RabbitMQ reais | `TEST_DATABASE_URL=… TEST_RABBITMQ_URL=… PYTHONPATH=src python -m pytest -q -rs` | **246 aprovados, 0 ignorados** |
| Suíte Python, SQLite + RabbitMQ real | idem, sem `TEST_DATABASE_URL` | 236 aprovados, 10 ignorados (exigem PostgreSQL) |
| Suíte Python, SQLite puro (como no job `application`) | `PYTHONPATH=src python -m pytest -q` | 232 aprovados, 14 ignorados (PostgreSQL/RabbitMQ) |
| Contrato REST | `python tools/export_openapi.py --check` | atualizado |
| Frontend | `npm test`; `npm run build` | 12 aprovados; build aprovado |
| Navegador, API com SQLite novo (como no job `e2e`) | `npm run test:e2e`; `npm run test:a11y` | 21 bloqueantes + axe bloqueante: **22 aprovados** |
| Navegador, API com **PostgreSQL + RabbitMQ** (`E2E_BASE_URL`, `broker: UP`) | mesmos roteiros | **22 aprovados**, incluindo F1, F2 e F3 pela interface |
| Desempenho RNF-07 (60 clientes, 100 amostras por consulta) | `python scripts/performance_smoke.py` | todas as 10 consultas com p95 < 500 ms; maior p95: faturas, 23,9 ms (SQLite) e 45,1 ms (PostgreSQL) |

- **Prontidão AMQP reproduzida:** com o RabbitMQ iniciando, `rabbitmq-diagnostics ping` respondeu no 2º segundo, a porta 5672 só aceitou conexão no 3º e `check_port_connectivity` passou no 4º. Compose e CI passam a usar `check_port_connectivity`.
- **Broker parado e religado de verdade** (API com PostgreSQL, `rabbitmqctl stop`): prontidão `broker: DOWN` com `status: UP`; despacho `failed: 1` e nenhuma fatura do contrato; listener AMQP de volta em ~4 s; despacho `processed: 1`, novo despacho `processed: 0`; uma fatura e um processo para o contrato.
- **Automatizado:** `test_broker_indisponivel_nao_deixa_efeito_e_reprocessamento_recupera` leva o evento a `FAILED` no limite (3), sem fatura nem processo para o contrato; após a volta do broker, o reprocessamento gera um único conjunto de efeitos e uma mensagem na fila `archcorp.events`.
- Os 10 ignorados do SQLite são os testes que exigem PostgreSQL (locks, concorrência de pagamento e convergência de migrações em PostgreSQL); todos rodaram na linha PostgreSQL acima.
- Observação de desempenho: a listagem de faturas é a mais lenta (calcula o saldo por fatura); continua duas ordens de grandeza abaixo da meta.
- Não verificado: Compose com Docker real, URL pública (T20), PostgreSQL gerenciado, leitor de tela.

## Lacunas da interface e feedback por papel (#61, 2026-10-20)

Ambiente: Linux (contêiner), Node 22, Chromium 1194, API local com SQLite novo. Base: branch do PR #57 (`3b49988`).

- `web/e2e/papeis-e-feedback.spec.ts`: **10 roteiros aprovados**; a suíte Playwright completa teve **19 bloqueantes aprovados** e a varredura axe informativa sem violações.
- Achado durante a validação: o fundo em gradiente de `.shell` fazia o axe classificar como “incompleto” todo texto fora dos cartões (título, introdução, rodapé), então o contraste dessa área não era medido. Com fundo sólido em `main` (sem mudança visual), o axe passou a medir e encontrou o rodapé abaixo de 4,5:1 (`#66768a` sobre `#f4f7fb`), corrigido para `#526175`. Uma injeção de cor de baixo contraste confirmou que o teste reprova quando há violação.
- `npm test` (12 aprovados) e `npm run build` aprovados. Backend inalterado.
- Não verificado: leitor de tela, navegação completa só por teclado e a regra de contraste em estados de foco e hover.

## Criação ambígua e seleção de clientes na interface (#34, 2026-10-20)

Ambiente: Linux (contêiner), Python 3.13, Node 22, SQLite, Chromium 1194. Base: `main` em `cf155ee`.

- `npm test` (web): **12 testes aprovados**, incluindo 8 novos em `web/tests/intents.test.ts` (classificação de falha ambígua, resposta perdida seguida de repetição com a mesma chave e um único registro, recusa de corpo diferente sem chamar a API, descarte explícito, liberação da chave após `4xx` e `503 SERVICE_UNAVAILABLE`).
- `npm run build` (inclui `tsc -b` estrito): aprovado.
- Playwright contra a API local com SQLite novo: **9 roteiros bloqueantes aprovados** (2 novos em `web/e2e/selecao-e-ambiguidade.spec.ts`, com 205 clientes de lote) e varredura axe sem violações A/AA nos seis contextos (informativa).
- `PYTHONPATH=src python -m pytest -q`: **213 aprovados e 10 ignorados** (PostgreSQL e RabbitMQ reais ausentes). O backend não foi alterado.
- Mudança de comportamento em relação à verificação de 14/10/2026 (seção T10): reenviar com campo corrigido depois de falha ambígua não usa mais chave nova automaticamente; o envio é recusado até o usuário repetir o pedido original ou descartá-lo.
- Não verificado: URL pública, PostgreSQL, uso por leitor de tela e execução no GitHub Actions.

## Estados finais, auditoria e prazos do Workflow (#59, 2026-10-20)

Ambiente: Linux (contêiner), Python 3.13, SQLite. Base: `main` em `cf155ee`, branch `workflow-estados-prazos`.

- `tests/test_workflow.py`: **13 aprovados**. Com as rotas e o serviço da `main` anterior, **5 falham**: reabertura de tarefa final com outra tarefa ativa, troca de responsável em tarefa final, cancelamento do processo quando todas as tarefas são finais com algum cancelamento, auditoria de criação/transição e prazo de preparação contado do `occurredAt` (despacho atrasado).
- `PYTHONPATH=src python -m pytest -q`: **226 aprovados e 10 ignorados** (PostgreSQL e RabbitMQ reais ausentes).
- `tools/export_openapi.py`: OpenAPI regenerado; só mudam descrições das rotas de tarefa (nenhum campo, status ou código removido).
- Não verificado localmente: PostgreSQL (o job `postgresql` do CI cobre a suíte), interface além das ações já existentes.

## Integridade de F2/F3 e migrações (#60, 2026-10-20)

Ambiente: Linux (contêiner), Python 3.13, SQLite e **PostgreSQL 16 local** (instância descartável, dados sintéticos, `TEST_DATABASE_URL`). Base: `main` em `cf155ee`, branch `f2-f3-integridade-migracoes`. RabbitMQ real não disponível.

- Linha de base da `main` no PostgreSQL local, antes das mudanças: 221 aprovados e 2 ignorados (RabbitMQ).
- Com as mudanças, PostgreSQL: **227 aprovados e 2 ignorados**; SQLite: **217 aprovados e 12 ignorados** (PostgreSQL/RabbitMQ).
- Novo `tests/test_integridade_f2_f3.py`:
  - data padrão de encerramento em UTC (31/12 23h30 em Brasília = 01/01 UTC); **falha com o serviço anterior**, que usava `date.today()` local;
  - novo evento com outro `eventId` para o mesmo fato (`ContractActivated.v1`, `TicketOpened.v1`) não cria segunda fatura, preparação ou processo de resolução;
  - pagamentos concorrentes de 1.500 numa fatura de 2.500: um é aceito e o outro recusado com `409`, saldo final 1.000 (somente PostgreSQL).
- `tests/test_migration_convergence.py`: banco vazio → head única sem divergência dos modelos, em SQLite e PostgreSQL; as convergências a partir de `0003` e de cada `0004` e o bloqueio do downgrade com fatura `FINAL` passaram nos dois bancos.
- Já cobertos por testes existentes e reexecutados aqui: frações de centavo (`422`), pagamento acima do saldo (`409`), transições que impedem reabrir fatura paga, fatura cancelada não recobrada no acerto final, valor final zero sem fatura, reentrega do mesmo `eventId`, replay e histórico do Support.
- Não verificado: RabbitMQ real e PostgreSQL gerenciado do provedor.

## Verificação em 17/10/2026 (entrega de 19/10)

Ambiente: Windows 11 (10.0.26300), Python 3.12.10, SQLite, dependências de `requirements.txt` e `requirements-dev.txt` em ambiente limpo.

- `PYTHONPATH=src python -m pytest -q -p no:cacheprovider`: **211 testes aprovados e 10 ignorados** em 7 min 50 s. Os ignorados exigem PostgreSQL ou RabbitMQ reais. Inclui os 8 testes novos de `tests/test_crm_reader_resiliente.py` e os 4 de indisponibilidade do CRM em `tests/test_f1_cliente_reserva_contrato.py` (ADR-006).
- `tools/export_openapi.py`: OpenAPI regenerado com as respostas `503` aditivas das quatro rotas que leem o CRM.
- Roteiros contra `uvicorn` local com banco novo: `scripts/demo_f1.py` **20/20**, `scripts/demo_f2.py` **14/14**, `scripts/demo_f3.py` **15/15**, todos com código de saída `0`. O F3 mostrou o prazo do processo cerca de 2 s depois do prazo do chamado, o defeito corrigido pelo PR #42 (ainda não integrado).
- `scripts/performance_smoke.py`: 200 consultas de prontidão com **p95 de 4,22 ms** (meta: 500 ms). O valor não representa hospedagem pública.
- `tools/render_diagrams.py`: seis diagramas Mermaid renderizados em `docs/arquitetura/img/` e inspecionados visualmente. Foram corrigidos o alias inválido de ator no F2, que duplicava participantes, e a acentuação do AS-IS.
- `tools/build_report.py`: o DOCX foi convertido pelo LibreOffice e tem **20 páginas**, todas inspecionadas em folha de contato. A estrutura segue o Guia (seções 1 a 5 e referências), com seis figuras e citações autor-data.
- `tools/build_presentation.mjs`: **18 slides**. O finalizador aprovou integridade e layout, e a conversão pelo LibreOffice confirmou os diagramas embutidos.
- Não verificado: URL HTTPS pública, PostgreSQL gerenciado e corte de chamada de rede de um CRM externo. Nomes e contribuições dos integrantes continuam pendentes no relatório e na apresentação.

## Verificação em 27/09/2026

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

## Endurecimento de segurança sobre a main (2026-10-15)

Origem: auditoria de código, configuração e logs do CI. Dados sintéticos; nenhum
ataque de carga ou teste no deploy público.

- Dependências: FastAPI 0.143.2 e Starlette 1.8.0 (antes 0.116.1/0.47.3, com
  CVE-2025-62727 e avisos posteriores corrigidos até a 1.3.1); `pip-audit -r
  requirements.txt` sem vulnerabilidades conhecidas. Vite 7.3.7
  (GHSA-rq7h-c2jc-7f22) e `source-map-js` 1.2.2 (GHSA-68fv-2mgg-jv7q, o aviso
  "high" do `npm ci`); `npm audit` sem vulnerabilidades. Lockfile gerado com npm 11.
  O OpenAPI exportado não mudou com a atualização do FastAPI.
- Métricas: rótulo pelo template da rota, método fora da lista conhecida vira
  `OTHER`, escape de rótulos e `/metrics` com `operations`/`admin`.
  `tests/test_security_hardening.py`: 2.000 URLs sintéticas criam no máximo as
  séries dos templates; saída válida com aspas e método desconhecido; 401/403/200.
- Compose: API e console do RabbitMQ publicados em `127.0.0.1`. Servidor Vite de
  desenvolvimento sem `--host 0.0.0.0`.
- Erros 422 sem `input`/`ctx` e com `msg` genérica, igual ao #35, e `describeIssue`
  ajustado na interface (`web/tests/api.test.ts`), para a main não esperar a pilha.
- CI: passos `pip-audit` e `npm audit --audit-level=moderate` reprovam a execução.
- Local (Python 3.13, Node 22): **79 passed** em SQLite; `npm test` 4 passed;
  `npm run build` sem erro.
- Limites mantidos: credencial pública compartilhada com todos os papéis, contêiner
  como root e ausência de limitação de taxa. Não verificado: deploy público e
  configurações reais do provedor.

## Roteiros Playwright versionados (2026-10-17)

Ambiente: Windows 11, `node -v` = v24.21.0, `npx playwright --version` = 1.63.0, Chrome for Testing 153.0.8010.12 (saída de `npx playwright install chromium`), Python do `.venv` local, SQLite temporário novo a cada execução, API em `127.0.0.1:8765` servindo `web/dist`, sem RabbitMQ.

- `npm run test:e2e` em `web/`: **7 testes aprovados** em duas execuções seguidas, cada uma com banco novo (F1 cliente → reserva → rascunho para o mesmo cliente; `demo-support` recebe a negativa ao cadastrar cliente; credencial inválida; "Sair"; seis contextos por menu e por URL; hash desconhecido).
- Verificação de que o teste não é vazio: com a asserção do F1 trocada de propósito por um texto inexistente, o teste falhou; o arquivo foi restaurado.
- `npm run test:a11y`: na execução local de 17/10/2026 o axe (WCAG 2 A/AA) listou 0 violações nos seis contextos, apenas no estado inicial (banco vazio, sem diálogos ou erros). O teste não tem asserção e o resumo não foi versionado. Não substitui auditoria formal nem teste com leitor de tela.
- Correção durante a validação: as primeiras execuções reaproveitaram a API do `docker compose` na porta 8000 (banco PostgreSQL persistente) e **não** valem como evidência; a porta padrão passou a 8765 e o reaproveitamento silencioso de servidor foi removido.
- CI: o job `e2e` passou no GitHub Actions no PR #54 (run 39067995117, 53 s), junto de `application`, `postgresql` e `rabbitmq`.
- Não verificado: o início do `npx` do MCP no Windows (depende do PR), a interface na URL HTTPS pública, F2/F3 pela interface e o perfil Playwright MCP em uma sessão do Claude Code/Codex.
