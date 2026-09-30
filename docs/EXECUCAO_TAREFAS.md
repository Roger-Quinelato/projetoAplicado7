# Execução das tarefas pendentes

Início: 30/09/2026. Base: `main`, commit `3a3d8bd` (PR #28).
Uma tarefa é verificada e recebe um commit antes do início da próxima.
Este registro comprova aceite técnico local; não altera automaticamente Jira,
Trello ou GitHub, nem comprova publicação ou integração com a Localiza.

Ordem prevista, considerando esforço e dependências: T06, T07, T08, T09,
T15, T10, T11, T16, T12, T13, T17, T19 e T21.

## T06 — Contratos REST e eventos

- Estado: concluída no escopo do protótipo.
- Entrega: OpenAPI 3.1 gerado pela aplicação, respostas e erros com exemplos;
  AsyncAPI com os seis eventos e envelope canônico; fronteiras de módulos.
- Verificação em 30/09: `pytest -q tests/test_contracts_and_architecture.py
  -p no:cacheprovider`: **9 aprovados**; `tools/export_openapi.py --check`: aprovado.
- A implementação já estava incorporada pelo PR #28. Esta tarefa registra seu
  aceite sem introduzir mudanças desnecessárias no código.
- Limite: consumidores internos; publicação RabbitMQ opcional; nenhum sistema
  corporativo externo foi acessado.

## T07 — Fundação, migrações e dados sintéticos

- Estado: concluída no escopo local; validação PostgreSQL publicada pertence à T20.
- Entrega: UUID global e consulta de legado, conflito de unicidade em 409,
  contrato de erro com correlação, carga sintética idempotente e Alembic aditivo.
- Verificação em 30/09: `pytest -q tests/test_foundation.py -p no:cacheprovider`:
  **10 aprovados**, incluindo upgrade de banco vazio/antigo, ausência de divergência
  dos modelos e geração de SQL offline para PostgreSQL.
- Limite: SQL offline não comprova execução no Supabase/Render; nenhum banco
  publicado foi usado. A implementação aceita já estava no PR #28.

## T08 — CRM

- Estado: concluída no escopo do protótipo.
- Entrega: clientes filtrados/paginados e inativação, contatos CRUD,
  oportunidades com estados finais, validação, autorização e auditoria.
- Verificação em 30/09: `pytest -q tests/test_crm.py -p no:cacheprovider`:
  **14 aprovados**, incluindo telefone/e-mail inválido, duplicidade, PATCH vazio,
  cliente inativo, recursos ausentes e matriz de papéis (401/403).
- A implementação já estava no PR #28; dados e autenticação seguem simulados.

## T09 — Reservas e contratos

- Estado: concluída no escopo do protótipo.
- Entrega: reserva e rascunho transacionais, cancelamento, ativação com
  revalidação cadastral, encerramento idempotente e `ContractClosed.v1`.
- Verificação em 30/09: `pytest -q tests/test_contracts.py -p no:cacheprovider`:
  **11 aprovados**, cobrindo período inválido, consentimento/elegibilidade,
  conflitos de idempotência, estados/datas, autorização e encerramento do workflow.
- Limite: faturamento de encerramento é responsabilidade da T12; frota e cobrança
  externas continuam fora do protótipo. Implementação incorporada pelo PR #28.
