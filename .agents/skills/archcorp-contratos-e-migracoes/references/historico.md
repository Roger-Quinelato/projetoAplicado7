# Histórico datado — archcorp-contratos-e-migracoes

Escrito em 16/10/2026 sobre o SHA `3557d20` (`main`). É retrato, não regra: reconfira no SHA atual
antes de citar como fato.

- **Q-04:** validação de múltiplo monetário com `float` rejeitava `19.99` com `multipleOf: 0.01`.
- **Q-05:** exemplos de contrato omitiam campos obrigatórios anuláveis (`overdueSince`,
  `contractId`) e não validavam contra o schema.
- **Q-06:** limite monetário mais restrito na entrada (compatível com `Numeric(14,2)`) seria mudança
  incompatível na v1 sem exceção registrada.
