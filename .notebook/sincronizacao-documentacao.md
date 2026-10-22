---
tags: [docs, cronograma, estado, git, worktree]
atualizado: 2026-10-22
---

# Sincronização da documentação com o código

## Onde cada fato vive

- Estado verificado por área: `docs/ESTADO_IMPLEMENTACAO.md` (uma linha por contexto, coluna de limites).
- Status das tarefas T01–T22 e pacotes A–J: `docs/CRONOGRAMA_EXECUCAO.md`. Status só vira `Concluído` com issue fechada e artefato; as issues T12–T22 ficam abertas mesmo quando o pacote fecha.
- Contagens de testes, p95 e o que não foi executado: `docs/EVIDENCIAS_VALIDACAO.md` (seção mais recente no topo).
- Requisito → código → teste: `docs/MATRIZ_RASTREABILIDADE.md`.

## Conferência rápida docs × código

- Eventos: `src/archcorp/main.py` (mapa `eventType` → consumidores, ~L56-61) contra `docs/events/asyncapi.yaml`.
- REST: `python tools/export_openapi.py --check` (saída 0 = sincronizado).
- Variáveis de ambiente: `src/archcorp/config.py:Settings` contra a tabela "Configuração" do README.
- Migrações: `src/archcorp/infrastructure/migrations/versions/` — duas `0004` convergem na `0005_merge_finance_support`.
- Limites de listagem (200): `finance/service.py`, `workflow/routes.py`, `contracts/routes.py`; afetam os indicadores da Visão geral (#73).

## Armadilhas

- O `main` local pode estar dezenas de commits atrás do `origin/main`; sempre `git fetch` antes de comparar.
- Vários PRs foram mesclados em branches empilhadas, não na `main`: #45–#49 (skills, em `feat/skills-conhecimento`), #70 e #72 (chegaram à `main` só pelo #71). #68 e #69 aparecem fechados sem merge, mas o conteúdo está na `main` via #71.
- No Windows, `EnterWorktree` com `name` falha porque o Git resolve o caminho como `projetoAplicado7` (minúsculo). Contorno: `git worktree add -b <branch> .claude/worktrees/<nome> origin/main` e depois `EnterWorktree` com `path`.
- `web/e2e/a11y.spec.ts` tem asserção desde o #62 (`expect(resumo).toEqual`); textos antigos ainda podem chamá-la de "informativa".
- O PPTX em `output/` não é regenerado fora do ambiente local (`@oai/artifact-tool`); pode divergir de `tools/build_presentation.mjs`.
