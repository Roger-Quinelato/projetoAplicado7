# Resumo — F-SEG (Segurança e privacidade), `44b8325`, 19/10/2026

**Contagem por severidade:** crítica 0; alta 0; média 8; baixa 8; informativa 1 (total 17).

**Os cinco mais graves** (ID, título, severidade, confiança, local):
1. SEG-01 — Credencial pública única dá papel de admin, sem limite de tentativas — média — alta — `src/archcorp/security.py:29-32`; `src/archcorp/main.py:69-70`
2. SEG-02 — Chamado aceita e devolve CPF, cartão, telefone, placa e e-mail — média — alta — `src/archcorp/support/service.py:54-83`; `src/archcorp/support/domain.py:119-130`
3. SEG-06 — Padrão ativa tokens fixos conhecidos quando `PUBLIC_DEMO` não está definido — média — alta — `src/archcorp/config.py:21`; `src/archcorp/security.py:11-18`
4. SEG-07 — Sem cabeçalhos de segurança; token de admin em `sessionStorage`; fonte externa — média — alta — `src/archcorp/main.py:80-86`; `web/src/App.tsx:31,34`
5. SEG-11 — `alembic_version` e sequências fora da proteção de RLS (Q-11) — média — média — `src/archcorp/infrastructure/db.py:49`

**Itens não executados e motivo:**
- E-SEG-23, RLS em PostgreSQL real: sem PostgreSQL local e Docker proibido. Script pronto e compilado (`evidencias/seg/scripts/seg_e06_rls_postgres.py`).
- E-SEG-27, Semgrep: não instalado, pois a instalação no `venv-auditoria` compartilhado foi vetada.
- HSTS, TLS e limites de corpo do edge; painel do Render e do Supabase; imagem Docker: não verificáveis aqui.

**Premissas assumidas:**
1. Modo público com dados sintéticos e credencial distribuída a visitantes (`web/src/App.tsx:146`).
2. Render e Supabase gratuitos como alvo; controles de borda não vistos.
3. Achados que dependem de PostgreSQL com confiança média (SQLite e código).
4. SQLite equivale à lógica de autorização e de validação.
5. Latências do cliente Windows não são do servidor; as medições têm variação.
6. Documentação pública da API (`/docs`) não é decisão declarada.

**Perguntas ao usuário (máximo 3):**
1. Modo público: manter um token com todos os papéis (AUD-34), ou separar credenciais por papel ou leitura, com ADR?
2. Chamados: bloquear CPF, cartão, telefone, placa e e-mail na API (SEG-02), com a decisão registrada?
3. A regra "texto de fora é dado" (`archcorp-seguranca` §3) entra na `main`, ou o branch `feat/skills-revisor` será mesclado (S-01)?

**Linha de base (F-SEG):** AUD-23 (= Q-11) aberto; AUD-24 resolvido; AUD-25 resolvido; AUD-34 aberto; AUD-46 parcial; AUD-47 aberto.

**Sobreposições:** F-CFG (SEG-03 e SEG-07 no edge; SEG-17 e `.env.example`; SEG-13 e S-01). F-DAD (SEG-15 ↔ AUD-35; AUD-39). F-QUA (AUD-32; AUD-36 ↔ SEG-12; os 2 skips do job `postgresql` são de RabbitMQ).

**Arquivos:** `evidencias/seg/evidencias.md`, `achados.md`, `linha_de_base.md`, `resumo.md`, `MODELO_AMEACAS.md`, `RELATORIO_SEGURANCA.md`; `scripts/` e `logs/` na mesma pasta.

**Estado do ambiente:** servidores encerrados nos dois modos, porta 18101 fechada; `pytest` dos testes de segurança com rc 0 (52 passed); nenhuma alteração fora da pasta da frente nem na cópia do repositório além de `tmp/` e `web/`.
