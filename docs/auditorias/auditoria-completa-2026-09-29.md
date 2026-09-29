# Auditoria completa — Projeto Aplicado 7, Cenário 4 (Localiza)

Data da auditoria: 29/09/2026. Escopo: documentação, requisitos, arquitetura, contratos, código, testes, demonstração e entregáveis acadêmicos. Esta auditoria não altera nenhum arquivo além deste relatório.

Convenções usadas nas tabelas:

- **Fato observado**: verificado neste commit por leitura de arquivo, execução de comando ou consulta somente leitura.
- **Inferência**: conclusão derivada de fatos observados, identificada como tal.
- **Não verificado**: afirmação que esta auditoria não conseguiu confirmar nem refutar.
- Referências `arquivo:linha` usam o commit auditado. `Guia p. N` indica a página do `Guia.pdf`.

## 1. Resumo executivo

**Veredito: parcialmente pronta.**

O repositório cobre, com artefatos próprios, quase todos os itens exigidos pelo enunciado (`Guia.pdf` p. 3–13). O protótipo executa os três fluxos mínimos. A suíte automatizada passou neste commit (18 testes) e o CI `Verify` está verde em `main`. OpenAPI e aplicação estão sincronizados, e a separação entre fato, meta e premissa foi feita de forma consistente em `AGENT.md`, `README.md` e `docs/ESTADO_IMPLEMENTACAO.md`.

A entrega ainda não está pronta para submissão por quatro grupos de problemas:

1. **Entregáveis acadêmicos incompletos ou incorretos.** O relatório DOCX não contém nenhuma figura ou diagrama, deixa participantes e contribuições pendentes e atribui à Localiza a demanda que o enunciado atribui à ArchCorp. Ele também cita como fonte `[1]` um material que não é o enunciado e se contradiz sobre o reprocessamento (seções 8 e 12.3).
2. **Contradições entre documentação e código.** Três comportamentos implementados e testados contradizem documentos ativos:
   - o reprocessamento zera o contador de tentativas;
   - a reconciliação publica `TicketEntitlementReconciled.v1` e atualiza o prazo no Workflow;
   - a descrição do chamado aparece na resposta de `GET /support/tickets`.
3. **Defeitos técnicos confirmados.** Um rascunho com a mesma chave de negócio e outra `Idempotency-Key` retorna `500`. Um consumidor que gera erro de integridade derruba o despachante sem registrar a falha. A rota de reservas lê a tabela do CRM diretamente, e o teste de fronteiras não detecta isso.
4. **Status de rastreabilidade inflado.** A matriz e o backlog marcam como "Atendido" ou `[x]` itens que o cronograma, o Jira e o próprio `ESTADO_IMPLEMENTACAO.md` registram como em andamento, pendentes ou não implementados (OIDC, traces, figuras do relatório).

Não há evidência de acesso a sistemas reais da Localiza. Não foram encontrados segredos reais versionados. A publicação pública (Render/Supabase) segue não verificada, conforme o próprio repositório declara.

## 2. Escopo auditado

| Item | Valor |
|---|---|
| Repositório | `Roger-Quinelato/projetoAplicado7` |
| Branch local | `ccr-1c5dff06-gdznnu` (mesmo commit de `origin/main`) |
| Commit | `563deee48815ad8d96dd60d95e29245eb4bc0dd2` — merge do PR #26 (29/09/2026 08:37 -03:00) |
| Estado inicial | Árvore limpa (`git status` sem alterações). Subprodutos de teste (`tmp/`, `__pycache__/`), ignorados pelo Git, foram removidos ao final |
| Data da auditoria | 29/09/2026 |
| Ambiente | Contêiner Linux; Python 3.11.15 em venv isolado; Node 22.22.2. O CI usa Python 3.12 e Node 24 |
| Exclusões | Anexos ArchCorp e skills em `C:\...` (inexistentes neste ambiente e ignorados pelo Git em `.codex-remote-attachments/`); arquivos `docs/*_SYNC.json` (ignorados pelo Git); Trello, Notion e Drive (não consultados); Render/Supabase (sem URL); Docker Compose (não executado); renderização visual do DOCX/PPTX (o LibreOffice do ambiente não carregou os arquivos) |

**Limite metodológico:** as skills citadas no prompt (`codenavi`, `docs-writer`, `writing-for-agents`, `organizador-de-frentes`, `atlassian-twg-cli`) estão em caminhos Windows indisponíveis. A navegação seguiu `CLAUDE.md` → `AGENT.md` → `README.md` → fontes de verdade, e o estilo foi avaliado pelas regras locais de `AGENT.md` ("Idioma e documentação").

## 3. Inventário de artefatos

| Grupo | Artefato | Estado | Observação |
|---|---|---|---|
| Fonte primária | `Guia.pdf` (13 p., título "Projeto Aplicado – ArchCorp: Arquitetura de Sistemas Corporativos") | Fonte | Único enunciado presente. Não menciona Localiza |
| Instruções | `CLAUDE.md`, `AGENT.md`, `README.md` | Ativo | `AGENT.md:39` aponta um PDF inexistente como fonte nº 1 |
| Planejamento | `PLANO_IMPLEMENTACAO_CENARIO_4.md` | Ativo (referência com metas) | Aviso na linha 3 separa metas de estado |
| Planejamento | `docs/CRONOGRAMA_EXECUCAO.md`, `docs/BACKLOG_TASKS_SUBTASKS.md` | Ativo | Status contraditórios entre si |
| Planejamento | `docs/governanca/*.md` (3) | Ativo (método) | Adaptações de material ArchCorp externo |
| Histórico | `termino1.md` | Histórico | Aviso na linha 3; contagem de testes desatualizada (17) |
| Estado | `docs/ESTADO_IMPLEMENTACAO.md`, `docs/EVIDENCIAS_VALIDACAO.md` | Ativo | Evidência datada de 27/09; seção 13–14/09 marcada como histórica |
| Requisitos/produto | `docs/REQUISITOS.md`, `docs/PRD_LOCALIZA.md`, `docs/VISAO_NEGOCIO.md` | Ativo | — |
| Arquitetura | `docs/arquitetura/AS_IS.md`, `TO_BE.md`, `FLUXOS_INTEGRACAO.md`, `docs/adr/ADR-001-*.md`, `docs/DDD_LOCALIZA.md`, `docs/TDD_LOCALIZA.md` | Ativo | ADR único |
| Integração | `docs/INTEGRACOES.md`, `docs/EXEMPLOS_API.md`, `docs/api/openapi.yaml` (35 paths), `docs/events/asyncapi.yaml` (5 canais) | Ativo; OpenAPI gerado | — |
| Qualidade/evolução | `docs/ATRIBUTOS_QUALIDADE.md`, `docs/EVOLUCAO_MANUTENCAO.md` | Ativo | — |
| Demonstração | `docs/ROTEIRO_DEMONSTRACAO.md`, `scripts/demo.ps1`, `scripts/performance_smoke.py` | Ativo | Scripts PowerShell (Windows) |
| Rastreabilidade | `docs/MATRIZ_RASTREABILIDADE.md` | Ativo | Status inflados (seção 5) |
| Código | `src/archcorp/**` (6 contextos + infraestrutura), `web/` (React/Vite), `migrations/001_initial.sql` | Ativo | A migração só cria schemas; as tabelas vêm de `create_all` |
| Testes | `tests/*.py` (18 testes) | Ativo | — |
| Operação | `Dockerfile`, `docker-compose.yml`, `render.yaml`, `.github/workflows/verify.yml` | Ativo | — |
| Gerados | `output/Relatorio_Tecnico_Cenario_4.docx`, `output/Apresentacao_Cenario_4.pptx` (últimos commits em 27/09) | Gerado | Gerados por `tools/build_report.py` e `tools/build_presentation.mjs` |
| Ferramentas | `tools/publish_github_issues.py`, `tools/publish_jira_backlog.py` | Ativo | Escrevem em serviços externos |
| Não revisado | `web/package-lock.json` (conteúdo), `.codex-finalizer/`, `tmp/report-render-final/` (citados em `EVIDENCIAS_VALIDACAO.md:10,54`, mas ausentes do Git) | Não revisado | As evidências visuais citadas não são reproduzíveis a partir do repositório |

## 4. Matriz de conformidade ao enunciado

A aplicabilidade de cada critério foi confirmada no `Guia.pdf`.

| # | Critério (fonte) | Evidência no repositório | Situação | Lacuna |
|---|---|---|---|---|
| 1 | Cenário com ≥ 3 áreas a integrar (p. 1–2) | Cenário 4, "Empresa de serviços": CRM, contratos, financeiro, atendimento, gestão de processos (p. 2); `AS_IS.md:7-11` | Atendido | O enunciado não cita Localiza. A contextualização Localiza é escolha da equipe e está marcada como premissa em `REQUISITOS.md:7-17` |
| 2 | AS-IS: sistemas, setores, usuários, processos, dados, problemas, dependências, necessidades, limitações e representação (p. 3) | `docs/arquitetura/AS_IS.md` (tabela 23-29, Mermaid 42-52, problemas 54-63) | Atendido com premissas | "Limitações da arquitetura atual" aparece misturada aos problemas. O diagrama AS-IS não está no relatório |
| 3 | RF e RNF, com RNF prioritários explicados (p. 3–4) | `docs/REQUISITOS.md:37-61`; P0/P1 em 29-35 | Atendido | RNF-03 exige OIDC só no plano (`PLANO:87`); em `REQUISITOS` o critério é "autenticação e papel", o que é coerente |
| 4 | TO-BE com componentes, sistemas, serviços, APIs, bancos, consumidores, comunicação, fluxo e fronteiras; justificativa (p. 4) | `docs/arquitetura/TO_BE.md` (visão lógica 34-51, tabela 63-70, implantação 107-114, justificativa 126-137); ADR-001 | Atendido | O diagrama da visão lógica (`TO_BE.md:40-41`) mostra `CustomerReader`, mas a rota de reservas ignora essa porta (seção 7, T-03) |
| 5 | Padrões/estilos: por que, vantagens, limitações; não usar microsserviços sem justificativa (p. 4–5) | ADR-001, opções 34-58 e consequências 86-101 | Atendido | — |
| 6 | ≥ 3 integrações com origem, destino, informação, objetivo, tipo, API, dados enviados/recebidos e erros (p. 5) | `docs/INTEGRACOES.md:22-119` (tabelas completas para F1–F3) | Atendido | Pontos contraditórios com o código em F2/F3 (seção 5, C-04 a C-06) |
| 7 | Sistemas corporativos: função, processos, dados, integrações e papel (p. 5–6) | `AS_IS.md:23-29`, `TO_BE.md:63-70`, `DDD_LOCALIZA.md:19-28` | Parcial | Não há classificação explícita dos sistemas nas categorias do enunciado (ERP, CRM, BPM, atendimento). "BPM" aparece no plano, não em uma seção dedicada |
| 8 | Interoperabilidade, com ≥ 1 exemplo de problema e solução (p. 6) | `PLANO:139-154` (exemplo e-mail × código × CPF); `INTEGRACOES.md:131-148` | Parcial | O exemplo de problema/solução só existe no plano de referência, não em documento ativo nem no relatório. O mapeamento legado só é gravado na criação de cliente (`crm/service.py:15-16`); não há conciliação de IDs ambíguos |
| 9 | ≥ 5 atributos de qualidade com necessidade, risco, estratégia e resultado (p. 6–7) | `docs/ATRIBUTOS_QUALIDADE.md:13-23` (9 atributos) | Atendido | A linha "Disponibilidade" cita "timeout na porta externa", que não existe no código (T-09) |
| 10 | Escalabilidade, manutenção e evolução: 7 perguntas e estratégia (p. 7) | `docs/EVOLUCAO_MANUTENCAO.md` §1–7 | Atendido | — |
| 11 | Empreendedorismo: público, problema, valor, benefícios e viabilidade em 6 dimensões (p. 7–8) | `docs/VISAO_NEGOCIO.md` | Atendido | Sem estimativa de custo; a ausência é justificada (linhas 40-42) |
| 12 | Apresentação técnica com 13 tópicos (p. 9) | `output/Apresentacao_Cenario_4.pptx` (15 slides) | Parcial | Sem slide dedicado a APIs (endpoints/exemplos) nem a manutenção. Slide 14 usa p95 histórico. Nenhum slide menciona Localiza, ao contrário dos documentos |
| 13 | Demonstração prática de ≥ 3 fluxos integrados (p. 9) | API, `web/`, `scripts/demo.ps1`, `ROTEIRO_DEMONSTRACAO.md`; testes F1–F3 aprovados | Atendido localmente | Docker Compose não executado nesta auditoria; demo pública inexistente (não exigida pelo guia) |
| 14 | Documentação: requisitos, diagramas atual, proposto, de componentes e de integração, fluxos, API, exemplos, justificativa, qualidade, estratégias, protótipo, código e relatório (p. 9–10) | Docs em Markdown com 7 blocos Mermaid; OpenAPI/AsyncAPI; exemplos | Parcial | Não há diagrama de componentes dedicado; a "visão lógica" faz esse papel. Os diagramas existem só em Markdown/Mermaid e não chegam ao relatório |
| 15 | "Outra equipe consiga dar continuidade" (p. 10) | README, roteiro, testes, CI | Parcial | Roteiro e demo exigem PowerShell. `tools/build_presentation.mjs:6-11` depende de caminhos locais `C:/Users/...` e não é reproduzível |
| 16 | Relatório em formato de artigo, 15–20 páginas (p. 10) | DOCX com 17 quebras forçadas de página, ou seja, ≥ 18 páginas estruturais; ~2.200 palavras | Não verificado (páginas) / Parcial (forma) | Renderização não realizada. Formato Carta (8,5×11 pol., `build_report.py:134-135`), e não A4. Ocupa a faixa de páginas com quebras forçadas e pouco texto |
| 17 | Resumo com problema, solução, metodologia e resultados (p. 10) | Seção "Resumo" do DOCX | Atendido | — |
| 18 | Introdução: contextualização, justificativa, objetivos geral e específicos, apresentação (p. 10) | DOCX §1 | Parcial | Não há subseção de justificativa. §1.1 contém erro factual (C-01) |
| 19 | Fundamentação teórica: 17 conceitos listados, referências, citações diretas e indiretas (p. 11) | DOCX §2 (8 subseções, 8 referências) | Parcial | Faltam ERP, CRM, BPM, microsserviços, arquiteturas distribuídas, camadas, escalabilidade, manutenibilidade e evolução. Não há citação direta. A ref. [8] não é citada no texto. O enunciado não é referenciado |
| 20 | Metodologia: participantes e contribuições, recursos, métodos, procedimentos (p. 11–12) | DOCX §3 | Parcial | Participantes pendentes ("nomes e contribuições pendentes"). Métodos por atividade (levantamento, modelagem etc.) pouco detalhados |
| 21 | Resultados: 15 itens e 6 perguntas de análise (p. 12–13) | DOCX §4–12 | Parcial | As perguntas estão respondidas de forma genérica em §12.1. Não há figuras de arquitetura |
| 22 | Considerações finais: 9 perguntas (p. 13) | DOCX §12.2–12.3 | Parcial | "Objetivos alcançados?" e "decisões mais relevantes" não têm resposta explícita |
| 23 | Referências no padrão da instituição (p. 13) | DOCX "Referências" | Parcial | Numeração tipo IEEE com autores em estilo ABNT; padrão institucional não especificado no repositório |

Os critérios que o enunciado **não** impõe incluem prazos (não há cronograma no `Guia.pdf`), deploy público, OIDC, tracing, RabbitMQ e número de testes. Esses itens são metas do projeto, não requisitos acadêmicos.

## 5. Matriz de coerência documental

Ordem de autoridade usada, conforme `AGENT.md:37-44`: enunciado > plano > ADR > contratos/docs de módulo. Para comportamento atual valem código, testes e `ESTADO_IMPLEMENTACAO.md` (`CLAUDE.md`).

| ID | Fontes comparadas | Conflito | Impacto | Autoridade | Correção recomendada |
|---|---|---|---|---|---|
| C-01 | `Guia.pdf` p. 1–2 × relatório §1.1 (`tools/build_report.py:182`) | O relatório afirma que "A Localiza recebeu a tarefa de modernizar" e que "o documento define" sistemas Localiza (reservas, assistência 24h). No enunciado, a ArchCorp recebe a demanda e o Cenário 4 é genérico | Alto: erro factual na entrega avaliada | Enunciado | Reescrever §1.1: ArchCorp é a contratante, Cenário 4 é "Empresa de serviços" e Localiza é a contextualização escolhida pela equipe |
| C-02 | `Guia.pdf` × relatório, referência [1] (`build_report.py:373`) | [1] cita "ARCHCORP. Plano de Execução e Cronograma Detalhado", não o enunciado | Alto: fonte primária não referenciada | Enunciado | Referenciar o `Guia.pdf` como fonte do cenário; manter o plano ArchCorp somente se ele for material da disciplina |
| C-03 | `AGENT.md:39` × árvore do repositório | Fonte nº 1 declarada: "`Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf`". O arquivo não existe; o enunciado real é `Guia.pdf`, com título ArchCorp | Médio: agentes procuram uma fonte inexistente | Repositório | Corrigir o nome para `Guia.pdf` |
| C-04 | `INTEGRACOES.md:82-84`, `EXEMPLOS_API.md:313-318`, relatório §8 × `main.py:606-607` e `tests/test_flows.py:132` (`assert event.attempts == 0`) | Os documentos dizem que o reprocessamento **não** zera o contador; o código e o teste zeram. O relatório §12.3 diz o oposto do próprio §8 | Médio: comportamento de recuperação mal documentado | Código e teste | Alinhar documentação e relatório ao comportamento real (zera e guarda `previousAttempts` na auditoria) ou mudar código e teste |
| C-05 | `FLUXOS_INTEGRACAO.md:231-233`, `ROTEIRO_DEMONSTRACAO.md:309-310`, `INTEGRACOES.md:114-115` × `support/service.py:60`, `workflow/service.py:30-47`, teste `test_indisponibilidade_de_contratos_cria_estado_pendente` | Os docs dizem que a reconciliação não publica evento e não recalcula o prazo no Workflow. O código publica `TicketEntitlementReconciled.v1` e o consumidor atualiza `due_at` (sonda P6 e teste). O relatório §9 e o AsyncAPI estão corretos | Médio: diagrama de sequência F3 e roteiro divergem do sistema | Código e teste | Atualizar o diagrama F3, o roteiro e `INTEGRACOES.md` |
| C-06 | `INTEGRACOES.md:117-119` × `support/routes.py:23-26` | Os docs dizem que a descrição do chamado "não entra … na resposta da API". `GET /api/v1/support/tickets` e `/{id}` a devolvem (sonda P4) | Médio: alegação de privacidade falsa | Código | Corrigir o doc ou remover/mascarar a descrição conforme o papel |
| C-07 | `MATRIZ_RASTREABILIDADE.md:31-32` × `ESTADO_IMPLEMENTACAO.md:13-14`, `README.md:27,139`, `AGENT.md:3` | A matriz marca SEC-01 "OIDC/OAuth 2.0 … Atendido no escopo simulado" e OBS-01 "traces … Atendido". O estado e o README afirmam que não há OIDC nem tracing | Alto: viola a regra NUNCA de `AGENT.md` | `ESTADO_IMPLEMENTACAO.md` e código | Reclassificar como "Não implementado (meta)" e separar RBAC por token local de OIDC |
| C-08 | `TO_BE.md:141`, `ATRIBUTOS_QUALIDADE.md:17`, relatório §6.2 × `security.py:25-48` | "Adaptador local simula tokens OIDC" / "Bearer OIDC simulado". O código compara strings fixas; não há claims, JWT nem emissor | Médio: sugere OIDC implementado | Código | Descrever como "tokens estáticos de demonstração com RBAC; OIDC é meta" |
| C-09 | `MATRIZ:27` ("figuras do relatório inspecionadas") × DOCX sem mídia (`build_report.py` sem `add_picture`) | O relatório não tem nenhuma figura | Alto: DOC-01 falso | Artefato gerado | Inserir diagramas AS-IS, TO-BE, componentes e sequências no relatório e na apresentação |
| C-10 | `BACKLOG_TASKS_SUBTASKS.md` (quase tudo `[x]`) e `MATRIZ` ("Atendido") × `CRONOGRAMA_EXECUCAO.md:40-61` (T05–T13 "Em andamento", T18 "Planejado"), Jira e issues | O backlog dá por concluídas as tarefas 4.1 a 9.5; o cronograma, o Jira e as issues dizem "em andamento/pendente" | Médio: duas fontes de status conflitantes | `CRONOGRAMA` e Jira (declarados principais em `CRONOGRAMA:10`) | Marcar o backlog como histórico ou derivá-lo do catálogo T01–T22 |
| C-11 | Contagem de testes: `MATRIZ:55` (13), `termino1.md:3` (17), `EVIDENCIAS:7` (18), relatório/slides ("suíte ampliada", p95 6,36 ms) | Números divergentes; execução atual: **18** | Baixo | Execução | Atualizar a matriz e remover números fixos do relatório ou regenerá-lo com valores atuais |
| C-12 | `ADR-001:73`, `PLANO:86,161,204`, `AGENT.md` (fila de erro, retry exponencial) × `integration/service.py:35-41`, `FLUXOS:148-151` | O ADR "aceito" determina fila de mensagens não processadas e retentativa. O código usa estado `FAILED` na outbox, sem fila no broker e sem backoff. `FLUXOS`/`INTEGRACOES` documentam corretamente o limite | Baixo/médio: ADR descreve meta como decisão vigente | ADR (decisão) × código (estado) | Registrar no ADR (ou em ADR-002) que a "fila de erro" é implementada como estado `FAILED` na outbox |
| C-13 | `ESTADO_IMPLEMENTACAO.md:20`, `EVIDENCIAS:12,15` × GitHub | Textos citam o "PR #2 … contém a implementação" como aberto. O PR #2 foi mesclado (merge commit `dcc1529`) em 29/09 | Baixo | GitHub | Atualizar para "mesclado em `main`" |
| C-14 | `CRONOGRAMA:11` ("atribuições permanecem sem responsável") × Jira `ARCH7` | No Jira, 18 de 22 tarefas têm responsável atribuído (conta do titular); T14, T18, T20 e T22 estão sem responsável | Baixo | Jira (principal) | Alinhar a regra do cronograma ou remover as atribuições |
| C-15 | Documentos (Localiza, reservas, assistência 24h) × apresentação (título "Empresa de Serviços", nenhuma menção a Localiza) | Enquadramento diferente entre docs e slides | Baixo | Decisão da equipe | Escolher um enquadramento e aplicá-lo aos dois entregáveis |
| C-16 | `DDD`/`INTEGRACOES` ("preparação de retirada") × `workflow/service.py:23` (`process_type="ONBOARDING"`) | Nome do processo divergente do vocabulário do domínio | Baixo | Código | Renomear para `PICKUP_PREPARATION` ou documentar o mapeamento |
| C-17 | `REQUISITOS.md:59` e `ATRIBUTOS:21` ("consultas locais do protótipo") × `scripts/performance_smoke.py:17-19` | A medição usa só `GET /health/ready`, não consultas de negócio | Baixo | Script | Medir também leituras de contrato, elegibilidade e operação ou restringir a alegação |
| C-18 | Vários documentos (ver seção 9) | A expressão "reservas e contratos" substitui indevidamente "contratos (técnicos)" | Baixo, mas recorrente | — | Revisar por busca dirigida |

## 6. Matriz de rastreabilidade (requisito → entregável)

| Req. | Decisão | Arquitetura/contrato | Implementação | Teste/evidência (29/09) | Demanda | Entregável | Situação |
|---|---|---|---|---|---|---|---|
| RF-01 ID global | ADR-001 regra 13, `AGENT.md` | UUID no OpenAPI | `crm/service.py:11-19`, `integration_legacy_ids` | F1 (UUID); mapeamento legado só na criação | T07 | Relatório §5 | Parcial: sem mapeamento para outros sistemas nem conciliação |
| RF-02 contrato sem recadastro | ADR regra 3 | `POST /contracts/drafts`, `CustomerReader` | `contracts/service.py:14-39` | `test_f1_…` aprovado; sonda P1: `500` para chave nova com mesmo negócio | T09, T11 | §7 relatório, slide 8 | Atendido com defeito T-01 |
| RF-03 ativação → cobrança + preparação | ADR regras 4, 7 | `ContractActivated.v1` | `contracts/service.py:41-68`, `finance/service.py`, `workflow/service.py:22-23` | `test_f2_…`, `test_ativacao_com_outra_chave_…` | T12, T13 | §8, slide 9 | Atendido (despacho manual) |
| RF-04 chamado com SLA | ADR regra 3 | `ContractEntitlementPort`, `TicketOpened.v1` | `support/service.py:16-43` | `test_f3_…`, `test_indisponibilidade_…` | T15, T16 | §9, slide 10 | Atendido; indisponibilidade simulada por flag, sem timeout |
| RF-05 propagação cadastral | ADR regra 4 | `CustomerUpdated.v1` | `crm/service.py:21-31`, `contracts/service.py:74-77` | `test_atualizacao_cadastral_…` | T08 | §5 | Atendido |
| RF-06 consulta por correlação | — | `GET /operations/{id}` | `main.py:612-624` | Sonda P7 (trilha de auditoria retornada); não há teste automatizado dedicado | T17 | Roteiro | Atendido sem teste dedicado |
| RF-07 reprocessamento | ADR regra 12 | `/integration/failures*` | `main.py:579-609` | `test_falha_permanente_…`; sonda P10: falha de integridade não é registrada | T17 | §8 | Parcial (T-02) |
| RNF-03 segurança | ADR riscos | HTTPBearer | `security.py` | `test_autorizacao_por_papel`, `test_public_demo_…`, RLS por mock | T17 | §6.2 | Parcial: RLS não testado em PostgreSQL real; descrição exposta (C-06) |
| RNF-04 observabilidade | — | `/metrics`, `/health/*` | `observability.py` | Sonda P8: sem métricas de retentativa ou fila | T17, T18 | §10 | Parcial |
| RNF-05 manutenibilidade | ADR regras 2, 13 | Portas públicas | — | `test_modulos_de_negocio_nao_importam_models…` aprovado | T05 | §6 | Parcial: violação em `main.py:660` não detectada (T-03) |
| RNF-07 desempenho | — | — | `performance_smoke.py` | p95 = 4,48 ms em 200 chamadas a `/health/ready` (29/09, SQLite) | T18 | §10 | Atendido para prontidão; consultas de negócio não medidas |
| RNF-09 testabilidade | — | — | `tests/` | 18/18 aprovados; CI `Verify` #10 (`563deee`) com sucesso | T18 | §10 | Atendido; sem testes de PostgreSQL/RabbitMQ reais |

## 7. Achados técnicos confirmados

Todas as sondas foram executadas contra o commit `563deee`, com SQLite em diretório temporário, `RABBITMQ_URL` ausente e `TestClient(raise_server_exceptions=False)`.

| ID | Área | Achado | Evidência | Severidade |
|---|---|---|---|---|
| T-01 | F1 / erros | Criar um segundo rascunho com mesmo cliente, serviço e início e **outra** `Idempotency-Key` viola `uq_contract_business_key` e retorna **500 Internal Server Error**. O erro não é tratado nem documentado no OpenAPI | Sonda P1: `201` e depois `500`; `contracts/models.py:24`; `contracts/service.py:33-34` sem captura | Importante |
| T-02 | Confiabilidade | Se um consumidor provoca erro de integridade, o `except` do despachante não faz `rollback`. O `session.commit()` seguinte levanta `PendingRollbackError`, o endpoint falha e o evento permanece `PENDING` com `attempts=0`, sem falha registrada | Sonda P10; `integration/service.py:35-43` | Importante |
| T-03 | Fronteiras | `POST /api/v1/contracts/reservations` (Contracts) lê `Customer` do CRM por `session.get` em vez de `CustomerReader` (`main.py:660-664`). `main.py` também importa modelos de todos os contextos (`main.py:11-52`, `demo_state` em 627-629). O teste arquitetural só inspeciona arquivos dentro de cada contexto (`tests/test_contracts_and_architecture.py:73-85`) e não percebe a violação | Leitura de código | Importante (regra NUNCA de `AGENT.md`) |
| T-04 | Privacidade | A descrição do chamado é devolvida em `GET /support/tickets` e `/{id}` para qualquer papel `support`, `operations` ou `admin` | Sonda P4; `support/routes.py:23-26` | Importante |
| T-05 | Contratos | Respostas `409` (chave idempotente reutilizada com outro corpo) de `/contracts/drafts` e `/support/tickets` existem no código (`main.py:481,545`), mas não no OpenAPI | Sonda P2/P9 | Melhoria |
| T-06 | Contratos | 25 rotas `/api` não declaram esquema de resposta (CRM auxiliar, reservas, finance, workflow) | Script sobre `openapi.yaml` | Melhoria |
| T-07 | Eventos | `causationId` é sempre `null`. Nenhum produtor o preenche, nem os eventos derivados (ex.: `TicketEntitlementReconciled.v1`) | Sonda P5; `integration/service.py:69-72` | Melhoria |
| T-08 | Observabilidade | `/metrics` expõe apenas requisições, latência somada e contadores `events_published_total`/`events_failed_total`. Não há retentativas, tamanho/idade da outbox nem histograma para p95. `/metrics` fica sem autenticação | Sonda P8; `observability.py` | Melhoria (a exigência é de `AGENT.md`, não do enunciado) |
| T-09 | Disponibilidade | Não há timeout em nenhuma chamada. A indisponibilidade de Contracts é simulada pela flag `CONTRACT_ADAPTER_AVAILABLE` (`support/service.py:22`), e a publicação `pika` é síncrona sem timeout configurado (`integration/service.py:50-62`) | Leitura de código | Melhoria; corrigir a alegação em `ATRIBUTOS:20` |
| T-10 | Mensageria | O RabbitMQ só recebe cópia após os consumidores internos. Se o broker falhar, os efeitos de negócio já confirmados permanecem, mas o evento vai a `FAILED` após 3 tentativas | `integration/service.py:24-31` | Informativo, já documentado em `INTEGRACOES.md:67-71` |
| T-11 | Persistência | `migrations/001_initial.sql` só cria schemas. As tabelas usam prefixos no schema padrão via `create_all` (`main.py:391-393`). A separação "esquema lógico por módulo" (`PLANO:124`) é apenas convenção de nome | Leitura | Melhoria |
| T-12 | Encerramento | `POST /contracts/{id}/close` não audita, não publica evento e não aceita `Idempotency-Key` | `contracts/routes.py:80-92` | Melhoria |
| T-13 | Tipos | Valores monetários saem como `float` JSON (`contracts/service.py:84`, `finance/routes.py:29-31`), apesar da regra "decimal com moeda explícita" | Leitura | Melhoria |
| T-14 | Segurança (positivo) | O modo público recusa tokens `demo-*`, exige segredo de ≥ 24 caracteres (`main.py:389-390`) e compara com `compare_digest`. Todas as rotas `/api` declaram `security` no OpenAPI | Leitura e script | Conforme |
| T-15 | Fluxos mínimos (positivo) | F1, F2 (com replay e novo despacho sem duplicar) e F3 (OPEN com SLA e PENDING→OPEN) aprovados. Os consumidores são internos ao monólito, e o despacho é manual via endpoint. Isso é coerente com `ESTADO_IMPLEMENTACAO.md:12` e não constitui integração empresarial real | `pytest` 18/18 | Conforme |

**Avaliação dos três fluxos:**

- **F1:** sustentado por código, teste e documentação. A falha de negócio (`422`) está documentada; a colisão com outra chave (T-01) não está.
- **F2:** sustentado. "Sem duplicidade" foi demonstrado para replay HTTP e redespacho. A falha de consumidor por erro de banco (T-02) não é recuperável como documentado.
- **F3:** sustentado. A documentação de reconciliação diverge do código (C-05) e a privacidade da descrição (C-06) não se confirma.

## 8. Divergências com GitHub, Jira e outras fontes (somente leitura)

| Fonte | Verificado | Resultado |
|---|---|---|
| GitHub Issues | 22 issues abertas (#4–#25), T01–T22, com etiquetas de tipo, prioridade, status e semana | Status das etiquetas iguais aos de `CRONOGRAMA_EXECUCAO.md:40-61` |
| GitHub PRs | #1, #2, #3 e #26 fechados; #2, #3 e #26 mesclados em 29/09 | `ESTADO`/`EVIDENCIAS` ainda descrevem o PR #2 como veículo ativo (C-13) |
| GitHub Actions | `Verify` run #10 (`563deee`, `main`) com sucesso; runs #1–#2 com falha em 28/09 (anteriores à correção) | Confirma a alegação de CI verde; o link de `EVIDENCIAS:15` aponta o run #4, que também teve sucesso |
| Jira `ARCH7` (site `projetooaplicado6.atlassian.net`) | 22 issues ARCH7-1 a 22 com prazos por semana coerentes com S1–S14 | T01–T04 aparecem como "Em andamento" no Jira e "Em revisão" no repositório; a perda de semântica está declarada em `MODELO_COMUM_ARCHCORP.md:9`. T14, T18, T20 e T22 estão em "Tarefas pendentes". Responsáveis atribuídos contrariam `CRONOGRAMA:11` (C-14) |
| Jira, nome do site | Host contém "aplicado6" | **Não verificado** se o site pertence a outro projeto (Projeto Aplicado 6) e é reutilizado. Nenhum dado do outro projeto foi encontrado nas 22 issues |
| Trello, Notion, Drive, GitHub Project | Não consultados | Não verificado. Os ledgers `docs/*_SYNC.json` estão fora do Git (`.gitignore`) |
| Render/Supabase | Sem URL | Não verificado, coerente com `ESTADO_IMPLEMENTACAO.md:3,16` |
| Anexos ArchCorp (cronograma, plano, organizador) | Indisponíveis no ambiente | Não verificado. Ver seção 9 |

## 9. Contaminação e conteúdo estranho ao cenário

| Local | Conteúdo | Classificação |
|---|---|---|
| `docs/CRONOGRAMA_EXECUCAO.md:3-8` | 14 semanas, 7 quinzenas e início fixado em 04/09/2026, derivados do "Plano de Execução e Cronograma Detalhado da ArchCorp" e de um "cronograma visual enviado". O `Guia.pdf` não define prazos | Risco de transferência de prazos de material externo. **Não verificado** se o material ArchCorp é da disciplina. O próprio texto marca as datas como "metas internas, sujeitas à validação" |
| Relatório, referência [1] e §1.1 | Plano ArchCorp citado como fonte do cenário | Contaminação de fonte (C-01, C-02) |
| `docs/governanca/*.md` | Adaptações de `AGENTE-ORGANIZADOR.md`, `modelo-comum.md` e `SKILL (2).md` | Material de método. Não contém fatos de outro projeto, mas mistura governança pessoal (contas Notion/Trello pessoais × universitárias) com a documentação acadêmica |
| `tools/build_presentation.mjs:6-11` | Caminhos `C:/ProjetoAplicado7`, `C:/Users/<usuário>/.codex/...` e runtime Python local | Dependência de máquina pessoal; expõe o nome de usuário local |
| `tools/publish_jira_backlog.py:16`, `publish_github_issues.py:75` | Host Jira com "aplicado6" | Possível reuso de instância de outro projeto; não verificado |
| Substituição global indevida de "contratos" por "reservas e contratos" | `AGENT.md:76,136,148`; `PLANO:144,154,235,345`; `EVOLUCAO_MANUTENCAO.md:25,86`; `VISAO_NEGOCIO.md:25`; `ATRIBUTOS_QUALIDADE.md:23`; `EVIDENCIAS_VALIDACAO.md:28`; `FLUXOS_INTEGRACAO.md:6`; `termino1.md:38,72,77,174`; `build_presentation.mjs:232` (slide 15); tabela "Recursos" do relatório; título do slide 11 | Artefato de edição que altera o sentido ("contratos de integração" virou "reservas e contratos de integração") |
| `PLANO:59` | "do preparação de retirada" | Mesmo artefato (concordância de gênero) |
| Dados pessoais | Nenhum CPF, e-mail real, token ou senha versionado. Credenciais `archcorp/archcorp` e `guest/guest` são padrões locais do Compose | Conforme; manter só em ambiente local |

## 10. Correções propostas (priorizadas)

### Bloqueadoras (antes da submissão)

| # | Origem | Correção | Resultado esperado | Critério de aceite sugerido |
|---|---|---|---|---|
| B-1 | C-09, Guia p. 9–12 | Incluir no relatório os diagramas AS-IS, TO-BE, componentes/implantação e sequências F1–F3 (exportados dos blocos Mermaid) | Relatório com evidência visual da arquitetura | DOCX contém ≥ 5 figuras numeradas e referenciadas no texto; `MATRIZ` DOC-01 cita as figuras |
| B-2 | C-01, C-02 | Corrigir §1.1 e as referências: ArchCorp como contratante, Cenário 4 genérico, Localiza como contextualização; citar `Guia.pdf` | Relatório fiel ao enunciado | Nenhuma frase atribui à Localiza a demanda ou ao enunciado sistemas específicos da Localiza; o enunciado aparece nas referências |
| B-3 | Guia p. 11, DOCX §3.1 | Preencher participantes e contribuições individuais | Metodologia completa | Seção 3.1 lista integrantes e contribuições; capa sem "pendentes" |
| B-4 | Guia p. 11 | Completar a fundamentação (ERP, CRM, BPM, camadas, microsserviços, arquiteturas distribuídas, escalabilidade, manutenibilidade, evolução) com citações diretas e indiretas | Aderência à seção 2 do enunciado | Os 17 conceitos da p. 11 aparecem; ≥ 1 citação direta; toda referência é citada no texto |
| B-5 | C-04, C-05, C-06, C-07, C-08 | Alinhar documentação ao código (reprocessamento, reconciliação, descrição do chamado, OIDC/traces) ou corrigir o código com teste | Nenhuma alegação contradiz o comportamento testado | Busca por "não zera", "não publica outro evento", "OIDC simulado" e "resposta da API" sem divergência; `MATRIZ` SEC-01 e OBS-01 marcadas como metas |
| B-6 | Guia p. 10 | Renderizar o DOCX e confirmar 15–20 páginas com conteúdo substantivo (não só quebras forçadas); considerar A4 | Limite de páginas comprovado | PDF renderizado anexado às evidências, com contagem de páginas e data/commit |

### Importantes

| # | Origem | Correção | Resultado esperado | Critério de aceite sugerido |
|---|---|---|---|---|
| I-1 | T-01 | Tratar `IntegrityError` do rascunho como `409` documentado | Nenhum `500` em F1 | Teste: duas chaves com o mesmo negócio → `409`; OpenAPI lista `409` |
| I-2 | T-02 | `session.rollback()` no `except` do despachante antes de registrar a tentativa | Falhas de consumidor sempre contabilizadas | Teste com consumidor que viola restrição → `attempts` incrementa e o endpoint retorna `200` com `failed=1` |
| I-3 | T-03 | Criar reserva via `CustomerReader`; estender o teste arquitetural a `main.py` e rotas | Fronteiras garantidas por teste | O teste falha antes da correção e passa depois |
| I-4 | T-04 / C-06 | Omitir ou mascarar a descrição nas listagens; expor só no detalhe para `support` | Privacidade coerente com a doc | Teste: `GET /support/tickets` sem `description` |
| I-5 | C-10, C-11, C-13, C-14 | Unificar status: `MATRIZ` e `BACKLOG` derivados do `CRONOGRAMA`/Jira; atualizar contagem de testes (18) e o estado dos PRs | Uma única fonte de status | Nenhum item "Atendido"/`[x]` com demanda correspondente em andamento; números iguais em todos os docs |
| I-6 | C-03 | Corrigir `AGENT.md:39` para `Guia.pdf` | Fonte de verdade localizável | O arquivo citado existe |
| I-7 | Guia p. 6; critério 8 | Mover o exemplo de problema de interoperabilidade (e-mail × código × CPF) para um documento ativo e para o relatório | Exigência "≥ 1 exemplo" rastreável | Seção dedicada em `INTEGRACOES.md` e no relatório |
| I-8 | C-12 | Registrar no ADR (ou em ADR-002) que a fila de erro é o estado `FAILED` na outbox e que não há backoff | ADR reflete a decisão implementada | ADR sem requisito contraditório não marcado como meta |
| I-9 | Guia p. 9, critério 12 | Adicionar à apresentação slides de APIs (endpoints e exemplo request/response) e de manutenção | Os 13 tópicos da p. 9 cobertos | Checklist p. 9 × slides sem lacunas |
| I-10 | Seção 9 | Corrigir as ocorrências de "reservas e contratos" usadas no sentido de "contratos técnicos" | Texto sem ambiguidade | Busca dirigida sem ocorrências indevidas |

### Melhorias

| # | Origem | Correção | Critério de aceite sugerido |
|---|---|---|---|
| M-1 | T-05, T-06 | Declarar `response_model` e `409` nas rotas | 0 rotas `/api` sem esquema de resposta |
| M-2 | T-07 | Preencher `causationId` em eventos derivados | `TicketEntitlementReconciled.v1` referencia o `TicketOpened.v1` |
| M-3 | T-08 | Métricas de retentativas e tamanho/idade da outbox; histograma de latência | `/metrics` expõe esses contadores |
| M-4 | T-09 | Timeout configurável no adaptador e no `pika`; corrigir `ATRIBUTOS:20` | Configuração documentada e testada |
| M-5 | C-17 | Medir p95 em consultas de negócio | Evidência com rotas de contrato/elegibilidade |
| M-6 | Critério 15 | Tornar `build_presentation.mjs` portável (variáveis de ambiente) e oferecer roteiro em bash/curl | Geração e demo executáveis fora do Windows |
| M-7 | T-11 | Criar tabelas nos schemas por contexto ou documentar a convenção de prefixos | Migração reproduzível alinhada ao `PLANO:124` |
| M-8 | C-15, C-16 | Unificar o enquadramento (Localiza × "Empresa de serviços") e o nome do processo `ONBOARDING` | Vocabulário único entre docs, código e slides |
| M-9 | T-12, T-13 | Auditar o encerramento de contrato; serializar valores monetários como string decimal | Teste de auditoria do `close`; contrato de API atualizado |

## 11. Perguntas sem resposta documental, comandos executados e limitações

### Perguntas em aberto

1. O "Plano de Execução e Cronograma Detalhado da ArchCorp" e o "cronograma visual" são materiais oficiais da disciplina ou de outro projeto? Qual é a data real de entrega?
2. Qual padrão de referências a instituição (UnDF, pela descrição do repositório) exige, e qual o formato de página do relatório?
3. Quem são os integrantes e quais foram suas contribuições?
4. O site Jira `projetooaplicado6` é exclusivo deste projeto?
5. O professor validou o uso da Localiza como contexto e as premissas do AS-IS (`BACKLOG` Subtask 1.5 aberta)?
6. A demo pública (T20) é requisito da disciplina ou meta interna? O `Guia.pdf` não a exige.

### Comandos e verificações

| Comando/verificação | Resultado |
|---|---|
| `git status`, `git log`, `git rev-parse HEAD origin/main` | Árvore limpa; HEAD = `origin/main` = `563deee` |
| Extração de texto do `Guia.pdf` (pypdf, 13 páginas) | Critérios mapeados por página |
| `PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider` | **18 passed**, 1 aviso de depreciação Starlette/AnyIO |
| `python scripts/performance_smoke.py` (SQLite temporário) | `amostras=200 p95_ms=4.48 resultado=PASS` |
| Comparação `app.openapi()` × `docs/api/openapi.yaml` | Iguais; OpenAPI 3.1.0; 35 paths; 25 rotas sem esquema de resposta |
| Sondas P1–P10 (script em diretório temporário) | Resultados citados em T-01, T-02, T-04, T-05, T-07, T-08, C-05 e RF-06 |
| `npm ci && npm run build` em cópia de `web/` | Build Vite concluído (JS de 240,5 kB) |
| Inspeção do DOCX (python-docx, XML) | 41 títulos, 10 tabelas, 0 figuras, 17 `pageBreakBefore`, ~2.200 palavras, formato Carta |
| Inspeção do PPTX (python-pptx) | 15 slides; texto extraído e comparado |
| Busca por segredos e dados pessoais (`grep`) | Nada sensível versionado além de credenciais locais padrão e caminho de usuário em `build_presentation.mjs` |
| GitHub (MCP, leitura): issues, PRs, Actions | Ver seção 8 |
| Jira (Rovo, leitura): `project = ARCH7` | 22 issues; ver seção 8 |

### Limitações

- Docker Compose, PostgreSQL e RabbitMQ não foram executados. O comportamento com esses serviços reais, incluindo RLS no Supabase, **não foi verificado**.
- A renderização visual do DOCX e do PPTX falhou no ambiente (LibreOffice não carregou os arquivos). O número exato de páginas e a qualidade visual **não foram verificados**.
- Os testes rodaram em Python 3.11 local; o CI usa 3.12 e estava verde no mesmo commit.
- Trello, Notion, Drive, GitHub Project e os anexos ArchCorp não foram consultados.
- As sondas usaram SQLite. O comportamento de erro de integridade em PostgreSQL pode diferir na mensagem, mas a ausência de tratamento é independente do banco.
