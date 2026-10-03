# Achados — Agente 1 (requisitos, progresso e entregas)

Referência: `main` = `3a3d8bd`; consultas externas em 01/10/2026, 20:37–20:44 UTC. Achados ordenados por severidade.

### A1-01 — T01–T05 marcadas como concluídas nas ferramentas sem atender ao próprio critério de aceite
- Natureza / Severidade / Confiança: divergência documental com risco de processo / **alta** / alta (consulta direta às ferramentas)
- Esperado: `CRONOGRAMA_EXECUCAO.md:64` ("`Concluído` exige link para artefato e verificação"); critério T01 "revisão do professor pendente" e T05 "Aprovar TO-BE..."; `AGENT.md` NUNCA: "marque uma entrega como concluída sem atender aos critérios"; `MODELO_COMUM_ARCHCORP.md`: "Uma tarefa só é concluída com evidência vinculada".
- Observado: em 29/09, ao fechar as sprints Jira Q1 e Q2, ARCH7-1..5 passaram a "Concluído" (`resolution = null`). Minutos antes, os comentários diziam "Revisão do professor permanece pendente ...; não marcado como concluído" (ARCH7-1) e "issue preservada em andamento para revisão/aprovação" (ARCH7-5). As issues GitHub #4–#8 foram fechadas com `status:concluido` "conforme o estado atual do registro principal", e os cartões Trello foram movidos para "Concluído". O repositório continua dizendo "Em revisão/Em andamento" (`CRONOGRAMA:40-44`), e a subtask 1.5 "Validar premissas com professor" está aberta (`BACKLOG:11`). Não há evidência de validação docente.
- Localização: Jira ARCH7-1..5; GitHub #4–#8; Trello lista "Concluído"; `docs/CRONOGRAMA_EXECUCAO.md:40-44`; `docs/BACKLOG_TASKS_SUBTASKS.md:11`
- Reprodução: JQL `project = ARCH7 AND key in (ARCH7-1, ARCH7-5)` com `fields=[status, comment, resolution]`; `gh issue view 4 --comments`.
- Impacto: o progresso declarado nas ferramentas passa a ser 5/22 concluídas sem aceite verificável; o fechamento da sprint foi tratado como aceite.
- Evidências: E1-28, E1-29, E1-30, E1-31, E1-32, E1-14
- Correção proposta + critério de aceite: reabrir ARCH7-1..5 (ou criar o status "Em revisão" no fluxo Jira) até haver registro datado da revisão docente; espelhar em GitHub e Trello; registrar no CRONOGRAMA a data da conferência. Aceite: cada T01–T05 "Concluído" tem um link para evidência de revisão/aprovação (ata, e-mail resumido sem dados pessoais ou comentário docente) e `resolution` preenchida; repositório, Jira, GitHub e Trello mostram o mesmo status.

### A1-02 — Relatório técnico contém erros factuais e contradições internas
- Natureza / Severidade / Confiança: defeito demonstrado (entregável avaliado) / **alta** / alta
- Esperado: enunciado (`Guia.pdf`: a ArchCorp recebe a demanda; Cenário 4 genérico); `AGENT.md` NUNCA (OIDC sem evidência); coerência com o código.
- Observado: §1.1 "A Localiza recebeu a tarefa de modernizar ... o documento define cinco sistemas: CRM, reservas e contratos, ... assistência 24h [1]"; a referência [1] é o "Plano de Execução e Cronograma Detalhado" da ArchCorp, e o `Guia.pdf` não é citado; §6.2 "O protótipo simula tokens OIDC" (o código usa tokens fixos, E1-11); §8 "A operação preserva o contador acumulado" × §12.3 "reinicia o contador" × teste `attempts == 0`. Persistem desde a auditoria de 29/09 (C-01, C-02, C-04, C-08).
- Localização: `output/Relatorio_Tecnico_Cenario_4.docx` §1.1, §6.2, §8, §12.3, Referências; gerador `tools/build_report.py:182,296,367,373`
- Reprodução: `unzip -p output/Relatorio_Tecnico_Cenario_4.docx word/document.xml` e extrair `<w:t>`.
- Impacto: o entregável principal contradiz o enunciado e o protótipo.
- Evidências: E1-01, E1-11, E1-23, E1-27
- Correção + aceite: reescrever §1.1 (ArchCorp contratante; Cenário 4 "Empresa de serviços"; Localiza como contextualização da equipe); citar o `Guia.pdf`; trocar "simula tokens OIDC" por "tokens estáticos de demonstração com RBAC; OIDC é meta"; alinhar §8 ao comportamento testado. Aceite: busca por "Localiza recebeu", "simula tokens OIDC" e "preserva o contador" sem resultado no DOCX regenerado; o `Guia.pdf` aparece nas referências.

### A1-03 — Relatório não cumpre a estrutura exigida pelo guia (integrantes, fundamentação, figuras, densidade)
- Natureza / Severidade / Confiança: defeito demonstrado frente ao enunciado / **alta** / alta (renderizado)
- Esperado: `Guia.pdf`, "Relatório Técnico": artigo de 15–20 páginas; fundamentação com 17 conceitos e "citações diretas e indiretas"; Metodologia com "Descrição dos integrantes e suas respectivas contribuições"; Introdução com justificativa; Documentação com diagramas de arquitetura atual e proposta, componentes e integração.
- Observado: 18 páginas Carta (não A4) renderizadas, mas com ~2.726 palavras e 17 quebras forçadas, de modo que várias páginas ficam com menos da metade ocupada; 0 figuras; capa e §3.1 com "nomes e contribuições pendentes"; fundamentação sem sistemas corporativos, ERP, CRM, BPM, camadas, arquiteturas distribuídas, escalabilidade, manutenibilidade e evolução; nenhuma citação direta; ref. [8] não citada no texto; sem subseção de justificativa; sem seção de sistemas corporativos nem o exemplo de problema de interoperabilidade.
- Localização: `output/Relatorio_Tecnico_Cenario_4.docx`; `tools/build_report.py:134-135,170`
- Reprodução: `soffice --headless --convert-to pdf` (com writer instalado) e `pdfinfo` → 18 páginas, letter; ver `$SP/agente1/render/rel_montage.png`.
- Impacto: a faixa de páginas é atingida por paginação forçada, e não por conteúdo; itens obrigatórios ausentes.
- Evidências: E1-21, E1-22, E1-24
- Correção + aceite: inserir os diagramas Mermaid exportados (AS-IS, TO-BE, componentes/implantação, sequências F1–F3), completar a fundamentação e a metodologia, incluir integrantes e contribuições, adotar A4 se a instituição exigir e reduzir quebras forçadas. Aceite: PDF renderizado anexado às evidências com 15–20 páginas de conteúdo, ≥ 5 figuras numeradas e citadas no texto, os 17 conceitos presentes, ≥ 1 citação direta, todas as referências citadas e integrantes nomeados.

### A1-04 — Matriz de rastreabilidade marca como "Atendido" itens não implementados ou não verificáveis
- Natureza / Severidade / Confiança: divergência documental / **alta** / alta
- Esperado: `AGENT.md` NUNCA: "Apresente OIDC/OAuth, tracing distribuído ... como implementados sem evidência"; `ESTADO_IMPLEMENTACAO.md:13-14`; `termino1.md` D12: "Nenhum item marcado como atendido sem evidência existente".
- Observado: SEC-01 ("OIDC/OAuth 2.0 ...") "Atendido no escopo simulado"; OBS-01 ("... traces ...") "Atendido; trace distribuído representado pela correlação"; DOC-01 "figuras do relatório inspecionadas" (não há figuras); DOC-03/DOC-04 "Atendido" com "18 páginas/15 slides inspecionados" em 14/09, mas sem nomes e anteriores a T06–T09; RF-06 "Atendido" sem teste automatizado. A matriz não traz data nem commit da verificação de cada linha.
- Localização: `docs/MATRIZ_RASTREABILIDADE.md:16,31,33-36`
- Reprodução: comparar as linhas citadas com `ESTADO_IMPLEMENTACAO.md:13-14,20` e com a inspeção do DOCX (0 `<w:drawing>`).
- Impacto: a matriz, que é o artefato de conferência cruzada indicado pelo README, superestima a cobertura.
- Evidências: E1-07, E1-10, E1-11, E1-21
- Correção + aceite: separar SEC-01 em "RBAC por token local: atendido" e "OIDC: meta não implementada"; OBS-01 em "correlação, logs, métricas e health: atendido" e "tracing: meta"; DOC-01/03/04 como "Parcial" até a regeneração; acrescentar colunas de data e commit. Aceite: nenhuma linha "Atendido" contém OIDC, traces ou figuras inexistentes; cada linha tem data/commit da evidência.

### A1-05 — Relatório e slides anteriores à implementação atual (T19 não atendido para os entregáveis finais)
- Natureza / Severidade / Confiança: divergência documental / média / alta
- Esperado: critério T19 "Atualizar todos os documentos técnicos, relatório e slides conforme implementação"; `AGENT.md` SEMPRE (atualizar documentação na mesma mudança).
- Observado: `output/` foi alterado pela última vez em `6702804` (27/09 22:09 -03); `src/` em `3a3d8bd` (29/09 23:29 -03). O relatório e os slides não descrevem T06–T09 e usam números históricos (13 testes, p95 6,36 ms). `3a3d8bd` também não atualizou `TO_BE.md` (3 eventos × 6 no AsyncAPI; 1 tabela por contexto × 16), `DDD_LOCALIZA.md`, `CRONOGRAMA` nem `BACKLOG`.
- Localização: `output/*`; `docs/arquitetura/TO_BE.md:63-75`; `docs/DDD_LOCALIZA.md` "Eventos de Dominio"
- Reprodução: `git log -1 --format=%ci -- output/` × `-- src/`; `grep -n "name: .*\.v1" docs/events/asyncapi.yaml`.
- Impacto: os entregáveis avaliados descrevem uma versão anterior do protótipo.
- Evidências: E1-12, E1-20, E1-23, E1-24
- Correção + aceite: regenerar relatório e slides a partir do estado de `main`, atualizar TO-BE e DDD com os 6 eventos e as tabelas reais. Aceite: o commit que altera `output/` é posterior ou igual ao último commit de `src/`; TO-BE e DDD listam os mesmos eventos do AsyncAPI; o relatório cita a contagem de testes do mesmo commit.

### A1-06 — Contagens de testes divergentes entre documentos
- Natureza / Severidade / Confiança: divergência documental / média / alta
- Esperado: `termino1.md`, Gate 2: "Registrar resultados atuais, sem copiar contagens ou métricas antigas".
- Observado: a matriz diz 13 testes (`MATRIZ:59`), `termino1.md:3` diz 17, `EVIDENCIAS:7` diz 18 (27/09) e `EVIDENCIAS:60` diz 57 (29/09); relatório e slides citam 13 e "suíte ampliada". A contagem estática atual é 50 funções e 57 casos.
- Localização: `docs/MATRIZ_RASTREABILIDADE.md:59`; `termino1.md:3`; DOCX (Resumo, §10); slide 14
- Reprodução: `grep -hE "^(async )?def test_" tests/*.py | wc -l` + parametrizações.
- Impacto: o leitor não consegue saber qual é a evidência vigente.
- Evidências: E1-04, E1-05
- Correção + aceite: remover números fixos dos documentos derivados ou citar "N testes no commit X, run Y". Aceite: todas as menções à suíte usam o mesmo número, a mesma data e o mesmo commit (57 em `3a3d8bd`, a confirmar pelo Agente 3).

### A1-07 — Fonte de verdade nº 1 inexistente; enunciado "Localiza" não localizado
- Natureza / Severidade / Confiança: divergência documental / média / alta (repositório) e média (ferramentas)
- Esperado: `AGENT.md:37-44` (ordem das fontes de verdade).
- Observado: `AGENT.md:39` (e `CLAUDE.md` por referência) aponta "Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf". O arquivo não está no repositório nem foi encontrado no Drive ou no Notion. O único enunciado disponível é o `Guia.pdf` (título ArchCorp, sem Localiza). `README`, `REQUISITOS` e `termino1` já tratam o `Guia.pdf` como fonte primária.
- Localização: `AGENT.md:39`
- Reprodução: `ls "Projeto Aplicado – Localiza_"*` → inexistente; buscas Drive/Notion (E1-03).
- Impacto: agentes e revisores procuram uma fonte inexistente; a escolha da Localiza parece imposta pelo enunciado.
- Evidências: E1-01, E1-03
- Correção + aceite: corrigir `AGENT.md:39` para `Guia.pdf` ou versionar o PDF citado, se ele existir. Aceite: o arquivo citado como fonte nº 1 existe no repositório.

### A1-08 — Contextualização Localiza e hipóteses do AS-IS apresentadas como fatos em documentos ativos
- Natureza / Severidade / Confiança: divergência documental / média / alta
- Esperado: `AGENT.md` NUNCA "Converta uma hipótese ... em fato documentado"; SEMPRE "Identifique premissas ... como tais".
- Observado: `PLANO:52` diz que "O PDF informa quais sistemas existem". `AS_IS.md:25-29` classifica "Reservas e contratos de locacao", "Atendimento e assistencia 24h" e "Gestao de processos operacionais" como "Sistema confirmado pelo guia", mas o guia diz apenas "Sistema de contratos" e "Sistema de atendimento". `ADR-001:12` afirma que "A organização possui ... sistema de reservas e contratos ... assistência 24h". O relatório §1.1 atribui ao enunciado sistemas da Localiza. Por outro lado, `REQUISITOS.md:7-17` e `AS_IS.md:7-11` fazem a distinção corretamente.
- Localização: `docs/arquitetura/AS_IS.md:25-29`; `docs/adr/ADR-001-integracao-empresa-de-servicos.md:12`; DOCX §1.1
- Reprodução: comparar com o `Guia.pdf`, Cenário 4.
- Impacto: mistura fato do enunciado com escolha da equipe, em desacordo com a regra central do projeto.
- Evidências: E1-01, E1-13
- Correção + aceite: reescrever a coluna como "Sistema genérico confirmado pelo guia (contratos/atendimento); especialização Localiza = premissa"; ajustar o contexto do ADR (sem reescrever a decisão, conforme a regra de ADR) e o relatório. Aceite: nenhuma frase atribui ao enunciado reservas, assistência 24h ou Localiza.

### A1-09 — Status divergente entre repositório e ferramentas para T06–T09 e demais tarefas
- Natureza / Severidade / Confiança: divergência documental / média / alta
- Esperado: `CRONOGRAMA:10` (Jira principal; índices com links; atualização manual conferida).
- Observado: `ESTADO_IMPLEMENTACAO.md:3` registra a sprint Q3 (T06–T09) como implementada em 29/09, e a matriz marca CRM-01/CTR-01/DATA-01 como "Atendido". O CRONOGRAMA (status de 27/09) continua com "Em andamento". As issues #9–#12 estão abertas ("até a revisão do PR"), embora o PR #28 tenha sido mesclado em 30/09 02:29 UTC; o Jira está "Em andamento"; os cartões Trello dizem "Conferido em 27/09/2026". O backlog marca quase tudo como `[x]`. `ESTADO:22` e `EVIDENCIAS:12,15` ainda tratam o PR #2 como veículo da implementação. Os corpos das issues apontam para a branch `sobe-artefatos-cenario-4`.
- Localização: `docs/CRONOGRAMA_EXECUCAO.md:45-48`; `docs/ESTADO_IMPLEMENTACAO.md:3,22`; `docs/BACKLOG_TASKS_SUBTASKS.md`; GitHub #9–#12; Jira ARCH7-6..9
- Reprodução: E1-28, E1-30, E1-32.
- Impacto: não há fonte única de progresso; o estado real de T06–T09 (implementado e mesclado, mas sem aceite registrado) não aparece em nenhuma ferramenta.
- Evidências: E1-14, E1-19, E1-28, E1-30, E1-32
- Correção + aceite: atualizar o CRONOGRAMA com uma coluna "status em <data>" e o commit/PR de evidência; marcar o backlog como histórico; atualizar issues, Jira e Trello após o aceite. Aceite: para cada Txx, CRONOGRAMA, Jira, GitHub e Trello mostram o mesmo status e a mesma data de conferência.

### A1-10 — Apresentação incompleta frente aos 13 tópicos do guia e desatualizada
- Natureza / Severidade / Confiança: defeito demonstrado frente ao enunciado / média / alta
- Esperado: `Guia.pdf`, "Apresentação técnica" (13 tópicos, entre eles APIs, sistemas corporativos, manutenção e análise de qualidade).
- Observado: não há slide de APIs (endpoints, exemplo de requisição/resposta) nem de estratégia de manutenção; sistemas corporativos e qualidade aparecem de forma parcial (3 atributos no slide 12); título do slide 11 "Interoperabilidade e reservas e contratos" (substituição indevida de "contratos técnicos"); slide 14 com p95 histórico e "Suíte ampliada" sem número; capa sem integrantes, datada de 27/09 "em revisão"; o enquadramento ("Empresa de Serviços", sem Localiza) diverge dos documentos.
- Localização: `output/Apresentacao_Cenario_4.pptx`; `tools/build_presentation.mjs`
- Reprodução: render em `$SP/agente1/render/apr_montage.png`.
- Impacto: lacunas visíveis na avaliação oral.
- Evidências: E1-22, E1-25
- Correção + aceite: acrescentar slides de APIs e de manutenção, corrigir o título, atualizar os números e incluir a equipe. Aceite: checklist dos 13 tópicos × slides sem lacunas; números com data e commit.

### A1-11 — T14: critério "custos zero, limites e evolução comercial" não coberto
- Natureza / Severidade / Confiança: meta futura não atendida (tarefa planejada) / média / alta
- Esperado: critério T14 (`CRONOGRAMA:53`); eixo de empreendedorismo do guia (já coberto).
- Observado: `VISAO_NEGOCIO.md` atende ao eixo do guia (público, problema, valor, benefícios, 6 dimensões), mas não analisa o custo zero da hospedagem (Render/Supabase Free), seus limites (hibernação, pausa por inatividade, cotas) nem a evolução comercial. O status está "Planejado" e o prazo é 29/10, de modo que não há atraso.
- Localização: `docs/VISAO_NEGOCIO.md:53-73`
- Reprodução: `grep -i "render|supabase|free|gratuit" docs/VISAO_NEGOCIO.md` → vazio.
- Impacto: o critério interno não está atendido; o requisito acadêmico está atendido de forma qualitativa.
- Evidências: E1-16
- Correção + aceite: acrescentar uma seção de custos da demonstração (planos gratuitos, limites documentados com fonte e data), riscos de suspensão e evolução comercial, sem números inventados. Aceite: seção com fontes oficiais datadas, explicitamente marcada como premissa onde couber.

### A1-12 — T21: Notion, Drive e GitHub Project não comprovados; evidências de sincronização fora do Git
- Natureza / Severidade / Confiança: divergência documental / média / média (limitação dos conectores)
- Esperado: critério T21 (criar Jira, Trello, Notion, Drive e GitHub Project, com links cruzados); `EVIDENCIAS:11` ("Trello e Notion criados").
- Observado: Jira (22) e Trello (22) existem, com links para o Jira; GitHub tem 22 issues e marcos Q1–Q7. Nenhuma página Notion ou arquivo Drive do projeto foi localizado; GitHub Project pendente (declarado). `JIRA_SYNC.json`, `TRELLO_SYNC.json` e `NOTION_SYNC.json` estão no `.gitignore`. Os marcos Q1 e Q2 seguem "open" com 0 issues abertas.
- Localização: `docs/EVIDENCIAS_VALIDACAO.md:11`; `.gitignore:229`
- Reprodução: E1-03, E1-15, E1-34.
- Impacto: dois dos cinco destinos não são verificáveis; não há evidência versionada da sincronização.
- Evidências: E1-15, E1-28, E1-30, E1-32, E1-33, E1-34
- Correção + aceite: registrar no repositório (sem segredos) as URLs públicas ou compartilháveis do Notion, do Drive e do Project, com data da conferência; fechar os marcos Q1/Q2 somente após o aceite. Aceite: cada destino tem uma URL acessível ao revisor e uma data.

### A1-13 — Lacunas de teste na rastreabilidade de RF-06, RF-07 e RNF-07
- Natureza / Severidade / Confiança: dívida técnica / baixa / média
- Esperado: critérios de `REQUISITOS.md:46-47,59`; `AGENT.md` (testes proporcionais ao risco, reprocessamento sem duplicar efeito).
- Observado: nenhum teste exercita `GET /operations/{correlationId}`; o teste de reprocessamento não verifica que reprocessar um evento já aplicado não duplica cobrança/processo; o p95 mede só `/health/ready`.
- Localização: `tests/test_flows.py:111-136`; `tests/test_contracts_and_architecture.py:32`; `scripts/performance_smoke.py:19`
- Reprodução: `grep -rn "operations/" tests/`.
- Impacto: "Atendido" sustentado por roteiro/manual ou por medida indireta.
- Evidências: E1-07, E1-08, E1-09
- Correção + aceite: teste HTTP de RF-06 (trilha com eventos e auditoria); teste de reprocessamento de evento já consumido com contagem de `Invoice`/`ProcessInstance` inalterada; medição p95 de rotas de negócio. Aceite: testes novos falham se a inbox for removida; o relatório de desempenho cita rotas de negócio.

### A1-14 — Gerador da apresentação depende de caminhos locais e expõe nome de usuário
- Natureza / Severidade / Confiança: dívida técnica / baixa / alta
- Esperado: `Guia.pdf` ("permitir que outra equipe ... consiga dar continuidade"); `AGENT.md` (execução reproduzível).
- Observado: `tools/build_presentation.mjs:6-11` usa `C:/ProjetoAplicado7`, `C:/Users/<usuário>/.codex/...` e um runtime Python local; depende de `@oai/artifact-tool`.
- Localização: `tools/build_presentation.mjs:4-11`
- Reprodução: `node tools/build_presentation.mjs` fora do Windows falha (inferência por leitura; não executado).
- Impacto: T19 não pode ser refeito por outra equipe.
- Evidências: E1-26
- Correção + aceite: parametrizar por variáveis de ambiente ou substituir por gerador portável (ex.: python-pptx). Aceite: o PPTX regenera em CI Linux.

### A1-15 — Jira: "Concluído" sem resolução e responsáveis atribuídos contra a regra do cronograma
- Natureza / Severidade / Confiança: divergência documental / baixa / alta
- Esperado: `CRONOGRAMA:11` ("Sem nome dos integrantes, atribuições permanecem sem responsável").
- Observado: 18 de 22 itens ARCH7 têm responsável (a conta do titular); ARCH7-1..5 em "Concluído" com `resolution = null`. Persiste desde a auditoria de 29/09 (C-14).
- Localização: Jira ARCH7
- Reprodução: E1-30.
- Impacto: a autoria e a contribuição individual (T22) ficam ambíguas.
- Evidências: E1-30, E1-27
- Correção + aceite: alinhar a regra (permitir o titular como responsável provisório) ou remover as atribuições; preencher a resolução. Aceite: a regra do CRONOGRAMA e o Jira coincidem.

### A1-16 — Auditoria anterior (29/09) não mesclada; a maioria dos achados documentais persiste
- Natureza / Severidade / Confiança: risco de processo / baixa / alta
- Esperado: rastrear e corrigir achados registrados.
- Observado: `origin/ccr-1c5dff06-gdznnu` (`be3f694`) não tem PR. Dos achados documentais, C-04 e C-05 foram resolvidos parcialmente; C-01, C-02, C-03, C-06, C-07, C-08, C-09, C-10, C-11, C-12, C-13, C-14, C-15 e C-17 persistem. Os técnicos T-01, T-03 e T-11 parecem resolvidos em `3a3d8bd`. O PR #29 (refactor + docstrings) está aberto em rascunho, com CI verde.
- Localização: refs `origin/ccr-1c5dff06-gdznnu`, `origin/claude/sprint-3-4-status-3mbie4`
- Reprodução: E1-19, E1-27.
- Impacto: os mesmos problemas reaparecem a cada rodada.
- Evidências: E1-19, E1-27
- Correção + aceite: transformar os achados abertos em subtarefas de T19 com link para esta auditoria. Aceite: cada achado tem um ticket com status.

### A1-17 — Diretório criado dentro de `output/` durante a auditoria — **NÃO PROCEDE**
- Status: retirado em 01/10/2026. O coordenador confirmou que criou `output/auditoria/2026-10-01T2035Z` intencionalmente. Mantido apenas como registro.
- Natureza / Severidade / Confiança: (não procede) / — / —
- Esperado: briefing (repositório somente leitura).
- Observado: `output/auditoria/2026-10-01T2035Z/evidencias/` (vazio) existe desde 20:35 UTC; não foi criado por este agente.
- Localização: `/home/user/projetoAplicado7/output/auditoria/`
- Reprodução: `find output/auditoria`.
- Impacto: nenhum no Git (diretório vazio), mas viola o isolamento da auditoria.
- Evidências: E1-36
- Correção + aceite: o coordenador deve confirmar a origem e mover os artefatos para `$SP`. Aceite: `find output -type d -newer Guia.pdf` vazio.
