# F-CFG · Resumo para o coordenador

**Achados (19):** crítica 0 · alta 0 · média 8 · baixa 10 · informativa 1.

**Os cinco mais graves** (ID — título — severidade — confiança — local):
1. CFG-05 — Compose: `api` publica no RabbitMQ como `guest`, recusado fora do loopback (inferido, não reproduzido) — média — média — `docker-compose.yml:6, 29-37`
2. CFG-02 — Modo público sobe com SQLite e a RLS é ignorada sem aviso — média — alta — `src/archcorp/main.py:69-75`; `src/archcorp/infrastructure/db.py:42-44`
3. CFG-04 — Sem `PUBLIC_DEMO`, o token `demo-admin` dá acesso administrativo — média — alta — `src/archcorp/config.py:21`; `src/archcorp/security.py:33-35`
4. CFG-01 — `Settings` aceita faixas inválidas; a falha aparece só no despacho ou na leitura do CRM — média — alta — `src/archcorp/config.py:9-20`; `src/archcorp/integration/service.py:95, 117-120`
5. CFG-11 — Repositório público; `main` sem proteção; alertas de vulnerabilidade desabilitados — média — alta — GitHub API (`branches/main/protection`: 404)

**Linha de base:** AUD-42 aberto · AUD-49 parcial · AUD-50 aberto (detalhes em `linha_de_base.md`).

**Itens não executados e por quê:**
- Docker (build local, `compose config`, Trivy, PID 1, reprodução do broker): decisão 2 do briefing. Roteiro pronto em `scripts/reproduzir_compose_broker_guest.py`.
- PostgreSQL e RabbitMQ reais: indisponíveis. Casos de broker só com porta fechada; concorrência e RLS ficam para F-DAD e F-SEG.
- Gitleaks, Trivy e Semgrep: ausentes e não instalados (nada foi instalado no `venv-auditoria`).
- Suíte completa e build do `web/`: são da F-QUA. Aqui rodou só o recorte `-k openapi` (3 testes, passaram).
- Redação de AGENTS.md e CLAUDE.md, e a skill `writing-for-agents` (decisão 1; fora do briefing). Skills opcionais `research` e `ai-firstify`: não usadas. `computedHash` do `skills-lock.json`: formato não documentado, não verificável. Scripts de `tools/` que escrevem no GitHub e no Jira: lidos, não executados.

**Premissas:**
- P-01: a CI (run 39063148796, 17/10) é a única evidência de build da imagem. A declaração de que o Docker funcionou em 17/10 não foi tratada como evidência.
- P-02: o fechamento transitivo foi calculado com o venv em Windows; a CI Linux pode diferir.
- P-03: GitHub, PyPI e npm consultados em 19/10 (11:12 a 11:30 UTC). As refs de CFG-12 vêm da coleta de 18/10 (~20:30 UTC), reaproveitada.
- P-04: visibilidade "public" lida da API do GitHub.
- P-05: logs gravados em `.txt` e `.json`, porque `.gitignore:59` (`*.log`) excluiria os novos do versionamento.
- P-06: credenciais de desenvolvimento e de CI são sintéticas; os registros usam `<REDACTED>`.
- P-07: documentos não avaliados como redação; usados só como existência de referência e como critério.

**Perguntas para o usuário:**
1. Há URL publicada do T20 (Render ou Supabase) fora do repositório? Se houver, AUD-42 passa a parcial e CFG-18 é reavaliado.
2. O modo público deve recusar a subida sem PostgreSQL (CFG-02)?
3. Qual o destino da pilha #45–#49 (D2) e da `feat/fluxo-coordenado` (20 commits sem remota): publicar ou descartar?

**Para outras frentes:** AUD-25 (pip-audit limpo para starlette 1.8.0, F-SEG); `/openapi.json` responde 200 sem credencial no modo público (F-SEG, item 9); `scripts/demo.ps1` fixa `Bearer demo-admin` (F-SEG); `tools/build_presentation.mjs` tem caminhos `C:/Users/roger/...` (AUD-38, fora do escopo).

Arquivos desta frente: `evidencias.md`, `achados.md`, `linha_de_base.md`, `resumo.md`, `scripts/` e `logs/` (em `output/auditoria/2026-10-18T2018Z/evidencias/cfg/`).
