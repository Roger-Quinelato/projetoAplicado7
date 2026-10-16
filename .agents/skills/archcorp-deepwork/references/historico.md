# Histórico datado — archcorp-deepwork

Escrito em 16/10/2026 sobre o SHA `3557d20` (`main`). É retrato, não regra: reconfira no SHA atual
antes de citar como fato.

Candidatos a deepwork apontados pela auditoria de 16/10/2026:

- **Q-02, ativação concorrente de contrato:** exige caracterizar a corrida em PostgreSQL antes de
  escolher entre bloqueio e atualização condicional.
- **Q-07, política de Workflow:** `workflow/routes.py` atribuía estado diretamente; mover a regra
  para uma máquina de estados envolve contrato e consumidores.
- Migração Alembic não aditiva (contração de coluna, troca de unicidade).

Não era candidato: **Q-01** (prazo do Workflow), correção pontual feita como tarefa comum no PR #42.
