# Histórico datado — archcorp-tdd

Escrito em 16/10/2026 sobre o SHA `3557d20` (`main`). É retrato, não regra: reconfira no SHA atual
antes de citar como fato.

- **Q-01 (prazo do Workflow):** o primeiro teste de regressão passava pelo motivo errado. O
  consumidor lia `datetime.now()` e o relógio falso só valia para o produtor; a revisão independente
  pegou isso. A correção (PR #42) fixou o `datetime` do consumidor por `monkeypatch` e testou a
  reentrega chamando o consumidor diretamente. Origem da regra "falhar na base pelo motivo do bug".
