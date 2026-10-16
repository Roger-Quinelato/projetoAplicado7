# Histórico datado — archcorp-implementacao

Escrito em 16/10/2026 sobre o SHA `3557d20` (`main`). É retrato, não regra: reconfira no SHA atual
antes de citar como fato.

- **Q-01, sítio irmão:** a correção do prazo do Workflow (PR #42) tratou `TICKET_RESOLUTION`; o
  processo `ONBOARDING` ainda calculava prazo com `datetime.now()` naquele SHA. Exemplo de "corrija
  a classe, não só o caso": o escopo restrito precisava estar declarado na entrega.
