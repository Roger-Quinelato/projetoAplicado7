# Instruções para Claude Code

## SEMPRE

- Leia [`AGENTS.md`](AGENTS.md) antes de qualquer tarefa neste repositório e siga suas regras **SEMPRE** e **NUNCA**.
- Leia [`README.md`](README.md), as instruções mais próximas do arquivo alterado e as fontes de verdade indicadas em `AGENTS.md`.
- Separe fatos implementados, metas arquiteturais e hipóteses. Confira [`docs/ESTADO_IMPLEMENTACAO.md`](docs/ESTADO_IMPLEMENTACAO.md) antes de relatar o estado do protótipo.
- Preserve o escopo acadêmico: o projeto usa dados sintéticos e não acessa sistemas reais da Localiza.
- Antes de commitar, confira `git config user.name` e `git config user.email`: todo commit e PR sai somente com a identidade do autor do projeto, Roger Quinelato.

## NUNCA

- Registre Claude como autor, committer ou co-autor: sem `Claude <noreply@anthropic.com>`, sem `Co-Authored-By: Claude` e sem rodapé `Generated with Claude Code` em commits, PRs, issues ou documentos. O crédito do trabalho é do Roger.
- Afirme que integrações, autenticação, observabilidade ou publicação estão funcionando sem evidência verificável.
- Inclua segredos ou dados pessoais reais no repositório, logs ou documentação.
- Contorne as fronteiras de módulo ou altere decisões estruturais sem seguir o processo de ADR descrito em `AGENTS.md`.

Se houver conflito, siga o enunciado acadêmico e a ordem de fontes de verdade em `AGENTS.md`. Este arquivo é um atalho de orientação; `AGENTS.md` contém as regras completas do projeto.
