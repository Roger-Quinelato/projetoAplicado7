# Resumo — F-QUA (Testes, qualidade, operação e interface)

Referência `main` = 44b8325. Execução em `iso-qua` (SQLite; porta 18103). Pacote: `evidencias\qua\`.

**Suítes**
- Rodada 1 (cobertura de ramos): 213 passou, 10 ignorados, 1 aviso, 387 s. Rodada 2 (repetição): 213 / 10 / 1, 224 s. Mesmo resultado nas duas.
- Cobertura de `src/` (SQLite): linhas 94,8%; ramos 87,1%; combinada 93,2%. Piores pacotes: workflow (ramos 60,0%) e infrastructure (ramos 67,6%).
- Frontend: `npm ci`, `npm test` (4 passam), `npm run build` ok. Cobertura do Node só de `api.ts` (60,6%); componentes 0%.
- CI (run 39063148796): PostgreSQL 221 / 2 ignorados; RabbitMQ 20; application 213 / 10. Os números locais coincidem com a CI em SQLite.

**Achados por severidade** (total 20; confiança alta em 16): crítica 0, alta 0, média 10, baixa 9, informativa 1.
**Os cinco mais graves**
1. QUA-13 — Ativação concorrente sem teste; 500 no SQLite (`database is locked`) e dois eventos no PostgreSQL (01/10). Média, alta. `src/archcorp/contracts/service.py:88-95`
2. QUA-03 — Teste de RLS cego a `alembic_version` e às sequências. Média, alta. `tests/test_public_database_security.py:8-27`
3. QUA-06 — Guarda de token do modo público sem teste. Média, alta. `src/archcorp/main.py:69-70`
4. QUA-04 — Testes de contrato sem `FormatChecker` (`occurredAt` sem `Z` passa). Média, alta. `tests/test_contracts_and_architecture.py:21-23`
5. QUA-05 — Rotas de tarefas do Workflow sem nenhum teste. Média, alta. `src/archcorp/workflow/routes.py:116-149`

**Linha de base da F-QUA**
- AUD-26: parcial (resolvido por inspeção; duplo clique não verificado sem navegador; cadastro sem chave).
- AUD-27: parcial (rodapé 4,32:1 e bordas 1,42:1; landmarks resolvidos; axe não reexecutado).
- AUD-32: aberto (reproduzido agora no caminho do middleware).
- AUD-36: parcial (PostgreSQL e RabbitMQ na CI; RLS por mock; acessibilidade e F1–F3 fora da CI; ativação sem teste).

**Não executado (e motivo)**
- Suíte, ativação concorrente e E-14 em PostgreSQL; RLS real com papéis `anon`/`authenticated`: sem PostgreSQL local. Evidência de CI para a suíte; script de ativação pronto (`scripts/ativacao_concorrente_api.py`).
- Jornada de navegador, duplo clique real, axe, leitor de tela e zoom de 200%: sem navegador.
- `npm audit`/`pip-audit`: fora da F-QUA (F-CFG). Docker: proibido nesta auditoria.

**Premissas**
- E-14 mede SQLite no Windows (i5-8250U), não PostgreSQL. A cauda de até 19 s não tem causa determinada (QUA-12).
- Contraste calculado a partir do CSS, sem renderização. A regra ARIA de QUA-09 vem da especificação 1.2, sem reconsulta online.
- Os 2 skips do job PostgreSQL são inferidos como os 2 testes de RabbitMQ (o job não usa `-rs`).
- O log de 1,6 KB da rodada 1 é a saída `-q` completa (213 + 10 = 223), não um log parcial.
- Tokens de demonstração locais são públicos, usados só na cópia e redigidos nos registros. O ambiente recusou executar um `.sh`: os comandos rodaram linha a linha (`scripts/comandos_executados.txt`).

**Perguntas para o usuário**
1. A exceção de segurança de `GET /metrics` no baseline v1 (QUA-14) deve ganhar ADR próprio?
2. A cauda de latência (QUA-12) deve ser medida em PostgreSQL (Supabase) antes da publicação, ou o SQLite local basta como referência?
