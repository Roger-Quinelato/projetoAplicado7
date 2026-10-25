# Evidências — Agente 1 (requisitos, progresso e entregas)

Referência auditada: `main` = `3a3d8bd` (árvore limpa). Clone em `/home/user/projetoAplicado7`, somente leitura. Consultas externas em 01/10/2026 entre 20:37 e 20:44 UTC. Nenhuma escrita em repositório ou ferramenta externa. Nenhum segredo, token ou e-mail copiado.

## A. Enunciado acadêmico

### E1-01 — `Guia.pdf` é o único enunciado no repositório e não menciona Localiza
- Tipo: comando + inspeção documental
- Fonte/local: `Guia.pdf` (13 p., A4); texto extraído em `$SP/agente1/guia.txt`
- Comando: `pdfinfo Guia.pdf; pdftotext -layout Guia.pdf guia.txt` (poppler, contêiner Linux)
- Resultado observado: título dos metadados "Projeto Aplicado – ArchCorp: Arquitetura de Sistemas Corporativos". O Cenário 4 é "Empresa de serviços" com "CRM; Sistema de contratos; Sistema financeiro; Sistema de atendimento; Sistema de gestão de processos". A palavra "Localiza" não aparece. A demanda é atribuída à ArchCorp ("A ArchCorp contratou vocês como uma equipe júnior").
- Limitações: nenhuma.

### E1-02 — Critérios acadêmicos extraídos do `Guia.pdf`
- Tipo: inspeção documental
- Fonte/local: `$SP/agente1/guia.txt`
- Resultado observado (resumo literal dos critérios):
  - Itens 1–9: AS-IS (sistemas, setores, usuários, processos, dados, problemas, dependências, necessidades, limitações e representação); RF e RNF, com explicação dos RNF prioritários; TO-BE (componentes, sistemas, serviços, APIs, bancos, consumidores, comunicação, fluxo, fronteiras) e justificativa; padrões/estilos, com vantagens, limitações e a ressalva de não usar microsserviços "apenas por serem uma tecnologia atual"; "pelo menos três integrações", cada uma com 9 campos (origem, destino, informação, objetivo, tipo, API, dados enviados, dados recebidos, tratamento de erros); sistemas corporativos (função, processos, dados, integrações, papel); interoperabilidade com "pelo menos um exemplo de problema de interoperabilidade"; "pelo menos cinco atributos de qualidade" com necessidade, risco, estratégia e resultado; 7 perguntas de evolução.
  - Eixo de empreendedorismo: público-alvo, problema, proposta de valor, benefícios e viabilidade em 6 dimensões (custos, complexidade, infraestrutura, equipe, prazo, necessidades futuras).
  - Entrega final: apresentação com 13 tópicos; demonstração prática de "pelo menos três fluxos integrados"; documentação com 16 itens; "Relatório Técnico em formato de artigo, de 15 a 20 páginas", com Resumo, Introdução (contextualização, justificativa, objetivos geral e específicos, apresentação), Fundamentação teórica (17 conceitos, referências, "citações diretas e indiretas"), Metodologia ("Descrição dos integrantes e suas respectivas contribuições", recursos, métodos, procedimentos), Resultados (15 itens e 6 perguntas), Considerações finais (9 perguntas) e Referências.
  - O enunciado não fixa datas, deploy público, OIDC, tracing, RabbitMQ nem número de testes.
- Limitações: não há enunciado específico "Localiza" para comparar (E1-03).

### E1-03 — Enunciado "Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf" não localizado
- Tipo: inspeção documental + consulta externa
- Fonte/local: `AGENT.md:39` cita esse arquivo como fonte nº 1; árvore de `3a3d8bd` não o contém. Google Drive (`search_files`, 20:37–20:39 UTC): consultas `title contains 'Localiza'` → vazio; `title contains 'ArchCorp' or 'Cenario' or 'Relatorio_Tecnico' or 'Guia' or 'Sistemas Corporativos'` → apenas arquivos sem relação; `fullText contains 'ARCH7' or 'ArchCorp' or 'Cenário 4'` → sem arquivo do projeto. `list_recent_files` → "Operation is not implemented". Notion (`notion-search`, 20:38–20:44 UTC): "Localiza Arquitetura de Sistemas Corporativos", "ArchCorp", "Projeto Aplicado", "ARCH7", "Localiza", "Cenário 4", "monólito modular outbox" → nenhuma página do projeto.
- Resultado observado: o arquivo não existe no repositório nem foi encontrado no Drive ou no Notion acessíveis por estes conectores.
- Limitações: `docs/governanca/AGENTE_ORGANIZADOR_ARCHCORP.md` diz que Drive universitário e Notion pessoal são contas distintas; o conector do Drive pode não alcançar a pasta universitária e o do Notion pode estar ligado a outro workspace. Registrado como **limitação de verificação**, não como inexistência.

## B. Requisitos, rastreabilidade e testes

### E1-04 — Contagem de funções de teste por grep (sem executar)
- Tipo: comando
- Fonte/local: `tests/*.py` em `3a3d8bd`
- Comando: `grep -hE "^(async )?def test_" tests/*.py | wc -l` e inspeção de `@pytest.mark.parametrize` (`tests/test_crm.py:121,132`, `tests/test_contracts.py:131`)
- Resultado observado: 50 funções `test_` (contracts 9, contracts_and_architecture 9, crm 9, extended_modules 3, flows 9, foundation 10, public_database_security 1). Três funções parametrizadas geram 3 + 4 + 3 casos, portanto 50 − 3 + 10 = **57 casos coletáveis**, o que coincide com "57 testes aprovados" em `docs/EVIDENCIAS_VALIDACAO.md:60`.
- Limitações: contagem estática; a execução cabe ao Agente 3.

### E1-05 — Contagens de testes divergentes na documentação
- Tipo: inspeção documental
- Fonte/local: `docs/MATRIZ_RASTREABILIDADE.md:59` ("13 testes aprovados, contratos sincronizados e p95 local de 6,36 ms"); `termino1.md:3` ("a suíte atual tem 17 testes"); `docs/EVIDENCIAS_VALIDACAO.md:7` ("18 testes aprovados", 27/09) e `:60` ("57 testes aprovados", 29/09); relatório DOCX, Resumo ("A avaliação histórica de setembro executou 13 testes automatizados"); slide 14 ("Suíte ampliada", "p95 6,36 ms").
- Resultado observado: quatro números diferentes (13, 17, 18, 57) para a mesma suíte. O real estático é 57 (E1-04).
- Limitações: nenhuma.

### E1-06 — Todos os testes citados na matriz existem
- Tipo: comando
- Fonte/local: `docs/MATRIZ_RASTREABILIDADE.md:11-35`; `tests/`
- Comando: `grep -ln "def <nome>" tests/*.py` para 14 nomes citados
- Resultado observado: os 14 existem (`test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia`, `test_identificador_legado_resolve_uuid_global`, `test_atualizacao_cadastral_chega_a_contratos`, `test_falha_permanente_pode_ser_listada_e_reprocessada`, `test_openapi_valido_com_exemplos_e_erros_problem_json`, `test_exemplos_asyncapi_validam_contra_os_schemas`, `test_envelopes_publicados_validam_contra_asyncapi`, `test_contrato_de_erro_problem_json_para_status_comuns`, `test_conflitos_de_unicidade_retornam_409_e_nao_500`, `test_carga_sintetica_e_idempotente`, `test_migracoes_criam_esquema_sem_divergencia_dos_modelos`, `test_migracoes_sao_aditivas`, `test_composicao_da_aplicacao_nao_le_modelos_dos_contextos`, `test_matriz_de_autorizacao_do_crm`).
- Limitações: existência não significa aprovação; execução pelo Agente 3.

### E1-07 — RF-06 sem teste automatizado de comportamento
- Tipo: comando + inspeção de código
- Fonte/local: `grep -rn "operations/" tests/` → única ocorrência `tests/test_contracts_and_architecture.py:32` (presença da rota no OpenAPI)
- Resultado observado: nenhum teste chama `GET /api/v1/operations/{correlationId}`. A matriz (`MATRIZ:16`) cita "OpenAPI e roteiro" e marca "Atendido". Há smoke manual com curl registrado em `EVIDENCIAS_VALIDACAO.md:64`.
- Limitações: o smoke manual não é reproduzível a partir do repositório.

### E1-08 — RF-07: teste de reprocessamento não verifica ausência de efeito duplicado
- Tipo: inspeção de código
- Fonte/local: `tests/test_flows.py:111-136`
- Resultado observado: o teste usa um evento `Broken.v1` sem consumidor real, verifica `FAILED`, listagem e retorno a `PENDING` com `attempts == 0`. Não reprocessa um evento cujo efeito já foi confirmado nem verifica "sem duplicar cobranças, processos ou chamados" (critério de `REQUISITOS.md:47`).
- Limitações: o comportamento pode estar correto pela inbox; falta teste (Agente 2/3 podem confirmar).

### E1-09 — RNF-07 medido só em `/health/ready`
- Tipo: inspeção de código
- Fonte/local: `scripts/performance_smoke.py:19` (`client.get("/health/ready")`); `docs/REQUISITOS.md:59` ("Consultas locais do prototipo apresentam p95 inferior a 500 ms")
- Resultado observado: a medição não cobre consultas de negócio.
- Limitações: nenhuma.

### E1-10 — Matriz marca "Atendido" itens que ESTADO/README/AGENT dizem não implementados
- Tipo: inspeção documental
- Fonte/local: `MATRIZ:35` (SEC-01 "OIDC/OAuth 2.0, papéis e privacidade" → "Atendido no escopo simulado; sem OIDC"); `MATRIZ:36` (OBS-01 "Logs, métricas, traces e health checks" → "Atendido; trace distribuído representado pela correlação no monólito"); `MATRIZ:31` (DOC-01 "figuras do relatório inspecionadas" → "Atendido"); `MATRIZ:33-34` (DOC-03/DOC-04 "Atendido; regenerar após revisão Localiza"). Contra: `ESTADO_IMPLEMENTACAO.md:13-14` ("Sem OIDC/OAuth", "Sem tracing distribuído"), `AGENT.md:3` ("OIDC, tracing distribuído ... são metas"), `README.md` Limites conhecidos.
- Resultado observado: o relatório não tem nenhuma figura (E1-21); OIDC e tracing não existem; DOC-03/04 dependem de nomes e regeneração pendentes (`ESTADO:20`).
- Limitações: nenhuma.

### E1-11 — Mecanismo de autenticação real
- Tipo: inspeção de código
- Fonte/local: `src/archcorp/security.py:11-35`
- Resultado observado: dicionário fixo `TOKEN_ROLES` com tokens `demo-*`; no modo público, um único segredo comparado por `compare_digest` concede `TOKEN_ROLES["demo-admin"]` (todos os papéis). Não há JWT, emissor, claims nem OIDC. `docs/arquitetura/TO_BE.md:141` e `tools/build_report.py:296` dizem "simula tokens OIDC"; `docs/ATRIBUTOS_QUALIDADE.md:17` diz "Bearer OIDC simulado".
- Limitações: análise de segurança aprofundada cabe ao Agente 2.

### E1-12 — TO-BE e DDD não foram atualizados após T06–T09
- Tipo: inspeção documental + comando
- Fonte/local: `docs/arquitetura/TO_BE.md:72-75` ("o AsyncAPI documenta `CustomerUpdated.v1`, `ContractActivated.v1` e `TicketOpened.v1`"); `docs/DDD_LOCALIZA.md` "Eventos de Dominio" (3 eventos); `docs/events/asyncapi.yaml:139,175,213,248,277,312` (6 mensagens). Tabela "Persistência" de `TO_BE.md:63-70` cita 1 tabela por contexto; o código tem 16 tabelas (`grep __tablename__`). `git show --stat 3a3d8bd` não altera `TO_BE.md`, `DDD_LOCALIZA.md`, `AS_IS.md`, `REQUISITOS.md`, `CRONOGRAMA_EXECUCAO.md`, `BACKLOG_TASKS_SUBTASKS.md` nem `output/`.
- Resultado observado: arquitetura documentada descreve 3 eventos; contrato e código têm 6.
- Limitações: nenhuma.

### E1-13 — Hipóteses e escolhas do projeto apresentadas como fato do enunciado
- Tipo: inspeção documental
- Fonte/local: `PLANO_IMPLEMENTACAO_CENARIO_4.md:52` ("O PDF informa quais sistemas existem"); `docs/arquitetura/AS_IS.md:25-29` (coluna "Classificacao": "Sistema confirmado pelo guia" para "Reservas e contratos de locacao", "Atendimento e assistencia 24h" e "Gestao de processos operacionais"); `docs/adr/ADR-001...md:12` ("A organização possui CRM, sistema de reservas e contratos, ... assistência 24h"); relatório §1.1 ("A Localiza recebeu a tarefa de modernizar ... o documento define cinco sistemas: CRM, reservas e contratos, ... assistência 24h").
- Resultado observado: o guia confirma "Sistema de contratos" e "Sistema de atendimento" genéricos; "reservas", "assistência 24h" e Localiza são contextualização da equipe. `REQUISITOS.md:7-17` e `AS_IS.md:7-11` marcam corretamente a contextualização como premissa, mas o ADR, o relatório e a coluna "Classificacao" a apresentam como fato.
- Limitações: nenhuma.

### E1-14 — Backlog marcado como concluído além do cronograma
- Tipo: inspeção documental
- Fonte/local: `docs/BACKLOG_TASKS_SUBTASKS.md:29-80` (todas as subtasks `[x]`, exceto 1.5 e 8.5), incluindo "9.3 Regenerar e inspecionar o relatório técnico" e "9.5 Revisar a entrega contra o guia e atualizar a rastreabilidade"; `CRONOGRAMA_EXECUCAO.md:45-61` (T06–T13, T15–T17, T19, T21 "Em andamento"; T14, T18, T20 "Planejado"; T22 "Aguardando").
- Resultado observado: duas fontes de status incompatíveis no repositório.
- Limitações: nenhuma.

### E1-15 — Arquivos de sincronização e evidências visuais citados não estão no Git
- Tipo: comando
- Fonte/local: `EVIDENCIAS_VALIDACAO.md:10-11,54` citam `JIRA_SYNC.json`, `TRELLO_SYNC.json`, `NOTION_SYNC.json`, `.codex-finalizer/`, `tmp/report-render-final/`; `.gitignore:221-222,229` ignora `tmp/`, `.codex-finalizer/` e `docs/*_SYNC.json`; `ls` → inexistentes no clone.
- Resultado observado: as evidências de sincronização e de inspeção visual não são reproduzíveis a partir do repositório.
- Limitações: podem existir na máquina do titular.

### E1-16 — Viabilidade (T14) não trata custos zero, limites gratuitos nem evolução comercial
- Tipo: comando + inspeção documental
- Fonte/local: `docs/VISAO_NEGOCIO.md:53-73`; `grep -i "render|supabase|free|gratuit"` em `VISAO_NEGOCIO.md`, `EVOLUCAO_MANUTENCAO.md`, `PRD_LOCALIZA.md` → nenhuma ocorrência; último commit em `VISAO_NEGOCIO.md` = `6702804` (27/09).
- Resultado observado: o documento cobre público, problema, valor, benefícios/indicadores e as 6 dimensões de viabilidade do guia de forma qualitativa, sem números. Não há análise de custo zero (Render/Supabase Free), limites (hibernação, pausa de projeto) nem evolução comercial, que formam o critério de T14. Esses limites aparecem apenas no `README.md`.
- Limitações: nenhuma.

## C. Histórico Git

### E1-17 — Grafo de todas as refs e origem das tarefas
- Tipo: comando
- Comando: `git log --all --oneline --graph --decorate --date-order`; `git show --stat <commit>`
- Resultado observado (datas do autor):
  - `4ef1884` 13/09 21:47 -03 Initial commit (.gitignore).
  - `e12ef49` 13/09 21:59 (PR #1, merge `c1d067a`) e `54115fb` 13/09 22:07 (mesmo conteúdo: 64 arquivos, 6551 inserções): primeira versão de docs, código, testes, relatório e slides → origem de T01–T05 (escopo, AS-IS, requisitos, ADR-001, TO-BE) e do relatório/slides.
  - `99a5b2d` 14/09 00:31: completa documentação, OpenAPI, regenera DOCX/PPTX.
  - `6702804` 27/09 22:09: módulos Finance/Support/Workflow, `web/` (React), PRD, DDD, TDD, CRONOGRAMA (T01–T22), governança, `render.yaml`, `publish_jira_backlog.py`; última alteração de `output/`.
  - `9f1026b`, `63c8066` 27/09: issues no GitHub (T21 parcial).
  - `369b9fe` 27/09: RLS no PostgreSQL (T17 parcial). `6eaaebe`/`5ff1ff2`/`010a0aa` 27/09: CI e registro de build.
  - `dcc1529` 29/09 08:32: merge do PR #2 em `main`.
  - `ba9051b` → `563deee` 29/09: AGENT.md SEMPRE/NUNCA e CLAUDE.md (PR #26).
  - `93d109e`, `e3ba685` → `d7f8c4d` 29/09: skills Claude (PR #27), sem efeito no produto.
  - `5f1ac4f`, `4c7f9e8`, `11fa99b`, `1155bb6`, `076d5bb` 29/09 17:22–17:48 UTC (branch `claude/install-skills-cloud-8vla1f`, PR #28) → squash `3a3d8bd` 29/09 23:29 -03: T06–T09.
- Limitações: um único autor humano em todo o histórico (identidade não reproduzida aqui); commits com coautoria de agente. A branch `execucao-tarefas-pendentes`/`3fdb533` não existe (L-01 do briefing).

### E1-18 — Commits que só registram estado/aceite e não comportamento
- Tipo: comando
- Fonte/local: `git show --stat 010a0aa` (só `ESTADO_IMPLEMENTACAO.md` e `EVIDENCIAS_VALIDACAO.md`: "docs: registra build remoto aprovado"); `9f1026b`, `63c8066` (docs + script de publicação de issues).
- Resultado observado: não há commit que registre o fechamento de T01–T05 (esse fechamento ocorreu só em Jira/GitHub/Trello em 29/09, E1-30 a E1-33); nenhum commit de `main` atualiza o CRONOGRAMA depois de 27/09.
- Limitações: nenhuma.

### E1-19 — Refs não mescladas
- Tipo: comando + consulta externa
- Fonte/local: `git log main..origin/claude/sprint-3-4-status-3mbie4` → `9443adc` (refactor) e `b58c933` (docstrings, regenera OpenAPI), PR #29 **aberto em rascunho** (GitHub `list_pull_requests`, 20:43 UTC), CI run #19 sucesso. `git log main..origin/ccr-1c5dff06-gdznnu` → `be3f694` (auditoria de 29/09), **sem PR**. `origin/sobe-artefatos-cenario-4` tem `f482d1d` (merge do PR #3 `add-claude-md` nessa branch, não em `main`).
- Resultado observado: estado publicado em `main` = `3a3d8bd`; trabalho de PR #29 e a auditoria anterior estão publicados no remoto mas não mesclados.
- Limitações: nenhuma.

### E1-20 — Datas de geração do relatório/slides anteriores ao código atual
- Tipo: comando
- Comando: `git log -1 --format='%h %ci' -- output/` → `6702804 2026-09-27 22:09:03 -0300`; `-- src/` → `3a3d8bd 2026-09-29 23:29:58 -0300`. `unzip -l` do DOCX/PPTX → entradas de 27/09 17:25–17:26; PPTX `dcterms:created` 2026-09-27T20:26Z; DOCX `core.xml` com datas padrão do python-docx (2013).
- Resultado observado: relatório e slides foram gerados antes de T06–T09 e não refletem `3a3d8bd`.
- Limitações: nenhuma.

## D. Relatório e slides

### E1-21 — Estrutura do DOCX
- Tipo: comando
- Fonte/local: `output/Relatorio_Tecnico_Cenario_4.docx` (SHA-256 `740de917…1966`, inalterado após a auditoria); texto em `$SP/agente1/relatorio.txt`
- Comando: `unzip -p ... word/document.xml` + regex Python; contagem de `<w:drawing`, `pageBreakBefore`, `<w:pgSz>`
- Resultado observado: 318 parágrafos, **~2.726 palavras**, **0 figuras/desenhos**, 10 tabelas, 17 `pageBreakBefore`, página Carta (12240×15840 twips = 8,5×11 pol.), não A4. Capa: "Equipe do Projeto Aplicado — nomes e contribuições pendentes / 27 de setembro de 2026 / Relatório técnico em revisão".
- Limitações: nenhuma.

### E1-22 — Renderização do relatório e dos slides
- Tipo: comando
- Ambiente: LibreOffice 24.2 (writer/impress instalados no contêiner para esta auditoria), cópias em `$SP/agente1/render/`; originais com SHA-256 conferido antes e depois.
- Comando: `soffice --headless --convert-to pdf`; `pdfinfo`; `pdftoppm`; `montage`
- Resultado observado: relatório **18 páginas** (letter); apresentação **15 slides** (16:9). Inspeção visual (`rel_montage.png`): várias páginas ocupam menos da metade da área útil, com quebras forçadas no início de cada seção ("2 Fundamentação teórica continuação", "4 Cenário atual AS IS continuação", "6 ... continuação"); nenhuma figura. Slides (`apr_montage.png`): visual limpo e consistente, com diagramas de caixas simples; sem cortes visíveis.
- Limitações: a paginação no Word pode diferir da do LibreOffice; a conversão inicial falhou com o pacote mínimo ("source file could not be loaded") e funcionou após instalar `libreoffice-writer`/`libreoffice-impress`.

### E1-23 — Afirmações do relatório contrárias ao enunciado ou ao código
- Tipo: inspeção documental
- Fonte/local: `$SP/agente1/relatorio.txt`; gerador `tools/build_report.py`
- Resultado observado:
  - §1.1: "A Localiza recebeu a tarefa de modernizar..." (o guia atribui a demanda à ArchCorp; E1-01).
  - Referência [1]: "ARCHCORP. Plano de Execução e Cronograma Detalhado" (o `Guia.pdf` não é referenciado).
  - §6.2: "O protótipo simula tokens OIDC" (E1-11).
  - §8: "A operação preserva o contador acumulado; uma nova falha retorna imediatamente a FAILED" × §12.3: "o reprocessamento reinicia o contador de tentativas" × `tests/test_flows.py:136` (`assert event.attempts == 0`).
  - Resumo/§10/slide 14: "13 testes", "p95 de 6,36 ms" históricos (E1-05).
  - §6.1: "RabbitMQ recebe cópias duráveis dos eventos para observação e integração externa" — coerente com o ESTADO (sem consumidores via broker).
  - §12.1: "A publicação HTTPS no Render/Supabase permanece dependente..." — não afirma deploy.
  - Referência [8] (Nygard) aparece só na lista; nenhuma citação direta (0 aspas).
- Limitações: nenhuma.

### E1-24 — Cobertura do relatório frente às seções do guia e ao estado atual
- Tipo: inspeção documental
- Fonte/local: `$SP/agente1/relatorio.txt`; contagem de termos: "BPM" 0, "Justificativa" 0, "camadas" 0, "Postman"/"Swagger" 0, "ERP" 1
- Resultado observado: a fundamentação (§2.1–2.8) omite sistemas corporativos, ERP, CRM e BPM como conceitos, arquitetura em camadas, arquiteturas distribuídas, escalabilidade, manutenibilidade e evolução de sistemas. A introdução não tem justificativa. A metodologia não lista integrantes. Não há seção de sistemas corporativos nem o exemplo de problema de interoperabilidade (e-mail × código × CPF do plano). O texto não descreve T06–T09 (contatos/oportunidades, reservas com cancelamento, encerramento com `ContractClosed.v1`, Alembic, `problem+json`, consulta de IDs legados); menciona apenas brevemente interface web (T10), pagamento simulado (T12) e credencial pública (T17); não trata inadimplência (T12), tarefas e responsáveis do workflow (T16) nem os resultados de qualidade (T18).
- Limitações: nenhuma.

### E1-25 — Cobertura da apresentação frente aos 13 tópicos do guia
- Tipo: comando + inspeção visual
- Fonte/local: `$SP/agente1/apresentacao.txt`, `apr_montage.png`
- Resultado observado: 15 slides: capa; cenário e problema; AS-IS; requisitos; decisão arquitetural; TO-BE; propriedade dos dados; F1; F2; F3; "Interoperabilidade e reservas e contratos" (título com a substituição indevida de "contratos técnicos"); confiabilidade/segurança/observabilidade; evolução e viabilidade; demonstração e resultados ("Suíte ampliada", "p95 6,36 ms"); conclusões. Não há slide de APIs (endpoints, exemplos) nem de estratégia de manutenção; "sistemas corporativos envolvidos" só aparece de forma indireta; a análise de qualidade cobre 3 atributos no slide 12, mais a lista do slide 4. Sem nomes da equipe ("Equipe do Projeto Aplicado · 27 de setembro de 2026 · em revisão"). Nenhum slide menciona Localiza; o título é "Arquitetura de Integração para Empresa de Serviços". Sem mídia raster (0 arquivos `media/`).
- Limitações: nenhuma.

### E1-26 — Gerador da apresentação não é reproduzível fora da máquina original
- Tipo: inspeção de código
- Fonte/local: `tools/build_presentation.mjs:4-11` (import de `@oai/artifact-tool`; caminhos `C:/ProjetoAplicado7` e `C:/Users/<usuário>/.codex/...`)
- Resultado observado: a apresentação não pode ser regenerada a partir do repositório em outro ambiente. O nome de usuário local está versionado; não foi reproduzido aqui.
- Limitações: nenhuma.

## E. Auditoria anterior (29/09)

### E1-27 — Auditoria de 29/09 lida e confrontada com `3a3d8bd`
- Tipo: comando + inspeção
- Comando: `git show origin/ccr-1c5dff06-gdznnu:docs/auditorias/auditoria-completa-2026-09-29.md` (272 linhas, commit `be3f694`, base `563deee`)
- Resultado observado (achado anterior → situação em `3a3d8bd`):
  - **Resolvidos ou aparentemente resolvidos:** T-01 (500 com outra `Idempotency-Key`; agora existe `test_conflitos_de_unicidade_retornam_409_e_nao_500` e a mensagem de commit cita 409); T-03 (reserva lia CRM direto; agora `contracts/service.py:9` importa `crm.public` e `main.py` não importa modelos de contexto; `test_composicao_da_aplicacao_nao_le_modelos_dos_contextos`); T-11 (migração só criava schemas → Alembic, ADR-002); C-04 em `INTEGRACOES.md:83-84` e `EXEMPLOS_API.md:369-371` (agora dizem que o contador zera); C-05 em `FLUXOS_INTEGRACAO.md:231-233` (agora cita `TicketEntitlementReconciled.v1`).
  - **Persistem:** C-01/C-02 (relatório: Localiza recebeu a tarefa; ref. [1]); C-03 (`AGENT.md:39` aponta PDF inexistente); C-04 no relatório (§8 × §12.3); C-05 em `ROTEIRO_DEMONSTRACAO.md:313` ("O protótipo não recalcula o prazo do processo de Workflow") e `INTEGRACOES.md:115`; C-06 (`INTEGRACOES.md:117-119` diz que a descrição não entra na resposta da API, mas `support/routes.py:50` a devolve no detalhe); C-07 (SEC-01/OBS-01 "Atendido"); C-08 ("simula tokens OIDC"); C-09 (relatório sem figuras); C-10 (backlog × cronograma); C-11 (contagens 13/17/18, agora com 57); C-12 (ADR-001:73 "fila de mensagens não processadas"); C-13 (`ESTADO:22` e `EVIDENCIAS:12,15` tratam o PR #2 como veículo ativo); C-14 (18 de 22 tarefas Jira com responsável × `CRONOGRAMA:11`); C-15 (slides "Empresa de Serviços" × docs Localiza); C-17 (p95 só de prontidão); B-3 (participantes); B-4 (fundamentação); B-6 (paginação: agora renderizada, 18 páginas Carta, E1-22); I-9 (slides sem APIs e manutenção); M-6 (gerador não portável).
- Limitações: T-01, T-02, T-03 e T-04 são técnicos e cabem ao Agente 2/3 confirmar por execução.

## F. Ferramentas externas (somente leitura)

### E1-28 — GitHub Issues: 22 tarefas
- Tipo: consulta externa
- Fonte/local: MCP `github.list_issues` (Roger-Quinelato/projetoAplicado7), 2026-10-01 ~20:42 UTC
- Resultado observado: 22 issues (#4–#25). **#4–#8 (T01–T05) FECHADAS** em 29/09 16:54 UTC, etiqueta `status:concluido`. #9–#12 (T06–T09) abertas com `status:em-andamento`, comentário de 29/09 18:01 UTC: "A issue continua aberta até a revisão do PR" (PR #28 mesclado em 30/09 02:29 UTC, sem atualização posterior). #13–#16, #18–#20, #22, #24 `em-andamento`; #17 (T14), #21 (T18), #23 (T20) `planejado`; #25 (T22) `aguardando`. Corpos das issues ainda apontam para a branch `sobe-artefatos-cenario-4` e o PR #2 (já mesclado).
- Limitações: nenhuma.

### E1-29 — Comentários de fechamento de T01 e T05 no GitHub
- Tipo: consulta externa
- Fonte/local: `issue_read get_comments` #4 e #8, ~20:43 UTC
- Resultado observado: #4, 16:50 UTC: "segue Em andamento no Jira porque a revisão docente continua pendente ... Mantive esta issue GitHub aberta e o status Em revisão; fechar a sprint não conclui a revisão pendente". #4, 16:53 UTC: "após o fechamento de Q1, o Jira agora mostra ARCH7-1 como Concluído ... Sincronizei esta issue para Concluído e fechei-a". #8, 16:53 UTC: "Sincronização após fechar a sprint Q2 ... ARCH7-5 está Concluído no Jira ... Espelho o status Concluído".
- Limitações: nenhuma.

### E1-30 — Jira ARCH7
- Tipo: consulta externa
- Fonte/local: Atlassian Rovo `searchJiraIssuesUsingJql` (site `projetooaplicado6.atlassian.net`, cloudId `3cc78234-…`), `project = ARCH7`, ~20:43 UTC
- Resultado observado: 22 itens ARCH7-1..22 com vínculos `Blocks` coerentes com as dependências do CRONOGRAMA e prazos por semana (ex.: ARCH7-5 due 2026-10-01; ARCH7-22 due 2026-12-10). Sprints: "Q1 · Escopo" e "Q2 · Requisitos e TO-BE" **fechadas**; "Q3 · APIs e fundação" ativa; Q4–Q7 futuras. **ARCH7-1..5 "Concluído"** com `resolution = null`; ARCH7-6..13, 15..17, 19, 21 "Em andamento"; ARCH7-14, 18, 20, 22 "Tarefas pendentes" e sem responsável; os outros 18 têm responsável (a conta do titular).
- Limitações: o histórico de transições (changelog) não foi consultado; o horário da transição foi inferido do campo `updated`.

### E1-31 — Comentários Jira contradizem o status "Concluído" de T01 e T05
- Tipo: consulta externa
- Fonte/local: ARCH7-1 e ARCH7-5 (campo `comment`), ~20:43 UTC
- Resultado observado: ARCH7-1, descrição: "Critério: cinco contextos e exclusões documentados; revisão docente pendente". Comentário de 29/09 13:29 -03: "Revisão do professor permanece pendente, conforme o critério da issue; não marcado como concluído". `updated` 13:39 -03 com status Concluído. ARCH7-5, comentário de 13:43 -03: "issue preservada em andamento para revisão/aprovação do conjunto"; `updated` 13:44:57 -03 com status Concluído. As duas têm `resolution = null`.
- Limitações: nenhuma.

### E1-32 — Trello
- Tipo: consulta externa
- Fonte/local: board "ArchCorp · Projeto Aplicado 7 · S1–S14" (https://trello.com/b/dL5CIIpM/archcorp-projeto-aplicado-7-s1-s14), `list_by_board`, ~20:44 UTC
- Resultado observado: 22 cartões, cada um com link para o ARCH7-n. T01–T05 na lista **"Concluído"** (`complete: true`, movidos em 29/09 16:53–16:54 UTC), mas as descrições continuam dizendo "Status: em revisão" / "Status local: Em revisão/Em andamento". T06–T13, T15–T17, T19, T21 em "Em andamento"; T14, T18, T20 em "Planejado"; T22 em "Aguardando". Descrições "Conferido em 27/09/2026". Nenhum cartão tem membros.
- Limitações: nenhuma.

### E1-33 — GitHub PRs, Actions, marcos, deployments
- Tipo: consulta externa
- Fonte/local: `list_pull_requests` (state all), `actions_list list_workflow_runs`, `gh api .../milestones`, `gh api .../deployments`, ~20:42–20:44 UTC
- Resultado observado: PRs #1, #2, #26, #27 e #28 com `merged_at` preenchido (o campo `merged` vem `false` no MCP; tratado como artefato da ferramenta); #3 mesclado na branch `sobe-artefatos-cenario-4`; **#29 aberto em rascunho**. Actions `Verify`: 19 runs; #1–#2 (28/09, `6eaaebe`) falharam; os demais tiveram sucesso; **run #18 (push em `main`, `3a3d8bd`, 30/09 02:30 UTC) = success**; run #19 (PR #29, `b58c933`) = success. O workflow executa pytest (Python 3.12), `npm ci`, `npm run build` e `docker build`; não executa `export_openapi --check` nem o teste de desempenho. Marcos Q1–Q7 todos "open" (Q1: 0 abertas/2 fechadas; Q2: 0/3). Deployments: 0. Repositório público, sem homepage.
- Limitações: GraphQL indisponível na sessão; GitHub Project não verificado.

### E1-34 — Notion e Google Drive sem artefatos do projeto
- Tipo: consulta externa
- Fonte/local: ver E1-03 (20:37–20:44 UTC)
- Resultado observado: nenhuma página Notion ou arquivo Drive do ArchCorp/ARCH7 localizado. O repositório afirma "Trello e Notion criados como índices/documentação" (`EVIDENCIAS_VALIDACAO.md:11`) e que o Drive guarda arquivos oficiais (`CRONOGRAMA:10`).
- Limitações: as contas dos conectores podem não ser as citadas na governança; limitação de verificação.

### E1-35 — Nenhuma URL pública de hospedagem
- Tipo: comando + consulta externa
- Fonte/local: `git log --all -p | grep onrender` → vazio; `git grep` sem URL Render/Supabase de projeto; GitHub `search_issues` "onrender URL pública Render deploy" → 0; Jira `text ~ "onrender"` → 0; deployments GitHub = 0; `render.yaml` define o serviço `archcorp-projeto-aplicado-7` (free) sem URL.
- Resultado observado: nenhuma URL foi encontrada; não foi feito GET (não se testou URL inferida).
- Limitações: a URL pode existir no painel Render do titular.

### E1-36 — Diretório criado em `output/` durante a auditoria (origem esclarecida: coordenador; A1-17 não procede)
- Tipo: comando
- Fonte/local: `output/auditoria/2026-10-01T2035Z/evidencias/` (vazio, criado em 01/10 20:35, não rastreado pelo Git)
- Resultado observado: um processo da auditoria (não este agente) criou diretórios vazios dentro do repositório, que deveria ser somente leitura. `git status` continua limpo porque o Git ignora diretórios vazios.
- Limitações: autoria do diretório não determinada.
