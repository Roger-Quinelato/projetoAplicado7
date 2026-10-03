# Pedidos de execução — Agente 2 → Agente 3

Execuções que exigem PostgreSQL, RabbitMQ ou a suíte, e por isso não foram feitas aqui. Os scripts de referência estão em `$SP/agente2/exp/` (aceitam `DATABASE_URL` externo: o harness usa `os.environ.setdefault`, então basta exportar `DATABASE_URL=postgresql+psycopg://...` antes de rodar; apague as tabelas entre execuções).

| ID | Pedido | Script base | O que registrar |
|---|---|---|---|
| P-01 | Despacho concorrente em PostgreSQL 16 (duas sessões/threads, barreira após verificação da inbox) | `e06_concorrencia.py` | Quantas vezes o handler roda; erro do perdedor (`IntegrityError`/`PendingRollbackError`/500); faturas criadas |
| P-02 | Ativações concorrentes com chaves diferentes em PostgreSQL (READ COMMITTED) | `e12_tx_corrida.py` | Número de `ContractActivated.v1` para o mesmo contrato |
| P-03 | Pagamentos com 0.001, 0.004, 0.005 e quitação de 100.10 em PostgreSQL (`numeric(14,2)`) | `e07_pagamentos.py` | Valores persistidos e resposta de quitação (comparar com SQLite: E2-13) |
| P-04 | `dueAt` de chamado e de processo após releitura em PostgreSQL (`timestamptz`) e validação AsyncAPI com `FormatChecker` | `e09_ordem_contrato.py` (parte 2), `e08_f3.py` | Presença de `Z`/offset e erros de formato |
| P-05 | Erro de banco dentro de consumidor em PostgreSQL (transação abortada) | `e04_falhas.py` cenário B, `e05_bloqueio.py` B2 | Confirmar 500 em loop, `attempts` sem incremento, bloqueio de eventos posteriores |
| P-06 | RabbitMQ real (se possível instalar): publicar com `RABBITMQ_URL` válido e verificar mensagens na exchange `archcorp.events` sem fila vinculada | `e04_falhas.py` cenário C adaptado | Mensagens retidas ou descartadas (`rabbitmqctl list_queues`, `list_exchanges`); tempo por evento |
| P-07 | Suíte completa + `tools/export_openapi.py --check` em 3a3d8bd | — | Confirmar que os achados A2-08/A2-09 não são detectados pela suíte (os testes usam só 2500 e não validam exemplos contra schema) |
