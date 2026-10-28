# Resumo — F-MOD (Modularização, fronteiras e domínio)

Referência: `main` = `44b8325`; `iso-mod` verificada (56 de 56 arquivos de `src`). Execução em 2026-10-19 (UTC).

**Achados (19):** crítica 0 · alta 0 · média 6 · baixa 10 · informativa 3. Parecer do mapa: P0 = 1 (MOD-08); P1 = 5 (MOD-01, 02, 03, 04, 10).

**Os cinco mais graves**
1. MOD-01 — Workflow aceita qualquer transição de tarefa; a rota atribui o estado (Q-07 / AUD-30) — média — alta — `src/archcorp/workflow/routes.py:140`
2. MOD-02 — Encerramento não chega a Support; processo COMPLETED com tarefas canceladas (AUD-28) — média — alta — `src/archcorp/workflow/service.py:101-104`; `src/archcorp/main.py:57`
3. MOD-04 — Testes de fronteira cegos a 8 de 12 formas de import (AUD-22) — média — alta — `tests/test_contracts_and_architecture.py:90-126`
4. MOD-06 — Cliente inexistente dá 404 na reserva e 422 no rascunho; UTC naive é tratado de formas diferentes — média — alta — `src/archcorp/contracts/service.py:195-199`; `src/archcorp/finance/domain.py:28-32`
5. MOD-08 — Projeção de Contracts sobrescrita por evento antigo (AUD-04; P0 no mapa) — média — média — `src/archcorp/contracts/service.py:166-169`

**Linha de base:** AUD-06 parcial · AUD-22 parcial · AUD-28 parcial · AUD-29 resolvido · AUD-30 (= Q-07) aberto · AUD-45 aberto (mitigado pela reconciliação).

**Checklist não executado, e por quê:** fase 3 da `tactical-ddd` (refatorar; o briefing pede só validar); `npm test` e build do `web/` (são da F-QUA; aqui só inspeção); suíte completa e cobertura de linha (F-QUA; rodei só `test_contracts_and_architecture.py`); reprodução de AUD-04 e experimentos de concorrência ou PostgreSQL (F-DAD); Semgrep (F-SEG); a skill `code-review` é baseada em diff, então usei a lista de smells de Fowler como julgamento sobre o código inteiro.

**Premissas**
- P1: subdomínios inferidos, porque o `DDD_LOCALIZA` não os classifica. Core: `contracts` e `support`. Supporting: `finance`, `crm` e `workflow`.
- P2: distância entre contextos tratada como alta (contextos extraíveis, ADR-001); uma equipe, sem distância social.
- P3: volatilidade alta se o módulo é core ou teve 7 ou mais commits desde 01/09 (limiar declarado).
- P4: experimentos em SQLite; PostgreSQL indisponível; concorrência não testada aqui.
- P5: `FINANCE_ALLOW_FUTURE_AS_OF=true` só na cópia isolada; tokens `demo-*` do repositório; nenhum segredo.
- P6: configuração do import-linter só em `scripts/`; não foi adicionada ao repositório.

**Perguntas para o usuário**
1. Ao encerrar um contrato, os chamados abertos devem ser cancelados, bloqueados ou mantidos? (MOD-02)
2. Aceitar chamado pendente com contrato inexistente é intencional (F3) ou defeito? A resposta fecha o ADR-006. (MOD-03)
3. `finance` é mesmo supporting? Se for core, as arestas A6 e A11 mudam de equilíbrio.

**Cruzar com outras frentes:** AUD-04 e AUD-41 (F-DAD); `settings` global (F-CFG); nome e e-mail copiados na projeção de Contracts (F-SEG).
