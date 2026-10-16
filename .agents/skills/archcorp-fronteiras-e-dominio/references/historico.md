# Histórico datado — archcorp-fronteiras-e-dominio

Escrito em 16/10/2026 sobre o SHA `3557d20` (`main`). É retrato, não regra: reconfira no SHA atual
antes de citar como fato.

- **Q-07:** `workflow/routes.py` fazia `item.state = body.state`, atribuindo estado na rota em vez
  de passar por uma máquina de estados no domínio.
- **Q-01:** o consumidor do Workflow recalculava o prazo do chamado com o relógio do processamento
  em vez de usar o `dueAt` publicado pelo Support. Corrigido no PR #42 (consumidor passa a usar o
  instante do evento).
