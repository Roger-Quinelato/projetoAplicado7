# Briefing comum — Auditoria Projeto Aplicado 7 (Cenário 4 Localiza)

Data da auditoria: 2026-10-01 (UTC). Coordenador: sessão principal.

## Estado congelado (referência auditada)

- Repositório: `/home/user/projetoAplicado7` (somente leitura para agentes; NÃO editar, NÃO commitar, NÃO executar testes aqui).
- Referência auditada: `main` = `3a3d8bd` ("Sprint Q3 · APIs e fundação (T06–T09) (#28)"). Branch local de trabalho `ccr-06dd26ce-y0wn6q` = mesmo commit, árvore limpa.
- A branch `execucao-tarefas-pendentes` / HEAD `3fdb533` citada no plano de auditoria NÃO existe no remoto nem no clone (`git cat-file` falha). Os "13 commits posteriores a 3a3d8bd" não são auditáveis → limitação de verificação L-01 (trabalho apenas local do usuário, não publicado).
- Outras refs remotas relevantes (já buscadas: `origin/*` e `pr/*`):
  - `origin/claude/sprint-3-4-status-3mbie4` (PR #29 aberto?, +2 commits sobre main: refactor + docstrings).
  - `origin/ccr-1c5dff06-gdznnu` (+1 commit: `docs/auditorias/auditoria-completa-2026-09-29.md`, auditoria anterior não mergeada).
  - `origin/add-claude-md`, `origin/sobe-artefatos-cenario-4`, `origin/docs/agent-guidelines-always-never`, `origin/claude/install-skills-cloud-8vla1f`.
- Cópia isolada (git archive de 3a3d8bd, sem .env/bancos/caches/node_modules): `$SP/iso`; manifesto SHA-256: `$SP/manifest_3a3d8bd.sha256` (110 arquivos excluindo .claude/).
- `$SP` = `/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad`

## Ambiente

- Python 3.11.15 (CI usa 3.12), Node 22.22.0 / npm 10.9.4 (CI e Dockerfile usam Node 24), Chromium Playwright em `/opt/pw-browsers`.
- Docker: cliente presente, **daemon indisponível** (sem /var/run/docker.sock) → build de imagem e compose NÃO executáveis.
- PostgreSQL 16 binários locais em `/usr/lib/postgresql/16/bin` (initdb/pg_ctl) → PostgreSQL descartável possível.
- RabbitMQ: não instalado (verificar). Rede de saída via proxy; algumas fontes externas podem falhar.
- `web/package.json` em 3a3d8bd NÃO tem script `test:browser` (o comando do plano não se aplica a este estado).

## Fontes de verdade (ordem, AGENT.md)

1. Enunciado acadêmico "Projeto Aplicado – Localiza_ Arquitetura de Sistemas Corporativos.pdf" — NÃO está no repositório; apenas `Guia.pdf`. Procurar no Drive/Notion.
2. `PLANO_IMPLEMENTACAO_CENARIO_4.md`. 3. ADR-001. 4. Demais ADRs, OpenAPI/AsyncAPI, docs de módulo.
Tarefas T01–T22 e critérios: `docs/CRONOGRAMA_EXECUCAO.md` (status declarado em 27/09).

## Classificação obrigatória

Atendimento: **comprovado | parcial | não atendido | não verificado | não aplicável (com justificativa)**.
Natureza do achado: **defeito demonstrado | risco | dívida técnica | meta futura | divergência documental**.
Severidade: **crítica | alta | média | baixa | informativa**. Confiança da evidência: **alta (reproduzido/executado) | média (inspeção de código/documento) | baixa (inferência)**.
Separar sempre: comportamento comprovado (executado), declaração documental, decisão aprovada, hipótese, evolução futura.

## Formato do registro de evidências (cada agente grava o seu)

Arquivo `$SP/agenteN/evidencias.md` com entradas:

```
### E<N>-<seq> — <título curto>
- Tipo: comando | inspeção de código | inspeção documental | consulta externa
- Fonte/local: arquivo:linha, URL, ferramenta + data/hora UTC
- Comando (se houver) e ambiente
- Resultado observado (trecho literal curto)
- Limitações
```

Arquivo `$SP/agenteN/achados.md` com entradas:

```
### A<N>-<seq> — <título>
- Natureza / Severidade / Confiança
- Esperado (com a fonte: enunciado, AGENT.md, ADR, critério Txx, RF/RNF)
- Observado
- Localização (arquivo:linha)
- Reprodução (passos/comando)
- Impacto
- Evidências: E<N>-...
- Correção proposta + critério de aceite (para o plano de ação)
```

E `$SP/agenteN/matriz_parcial.md` com, para cada tarefa Txx da sua frente: critério, implementação, evidência, origem histórica (commit), estado declarado, conclusão auditada (classificação) e RF/RNF vinculados.

## Regras

- Somente leitura: não alterar código, contratos, tickets, issues, PRs, páginas Notion/Drive/Trello/Jira, nem publicar nada. Em ferramentas externas, apenas consultas.
- Nunca copiar segredos/tokens/dados pessoais para os registros (se encontrar, registre só a localização e o tipo).
- Apenas o Agente 3 executa suítes compartilhadas (pytest, export_openapi --check, npm build, performance). Agentes 1 e 2 podem executar scripts pontuais de leitura/inspeção, mas não a suíte; se precisarem de um resultado de execução, registrem a necessidade em `$SP/agenteN/pedidos_execucao.md`.
- Escrever tudo em português do Brasil.
