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

## T15 — Atendimento e assistência

- Estado: concluída no escopo do protótipo.
- Correção: mesma chave com descrição diferente retorna 409, em vez de ocultar a
  mudança. Pedidos novos usam hash completo; registros antigos usam o chamado
  original, sem migração e sem copiar a descrição para eventos ou logs.
- Prova de regressão: os dois cenários de `tests/test_support.py` falharam antes
  da correção (201 em vez de 409) e passaram depois.
- Verificação em 30/09: `pytest -q tests/test_support.py tests/test_flows.py
  tests/test_extended_modules.py tests/test_contracts_and_architecture.py
  -p no:cacheprovider`: **23 aprovados**, incluindo SLA, atribuição, resolução,
  reconciliação, F3, reentrega e contratos de eventos.
- Documentação de integração atualizada. Autenticação e sistemas externos seguem
  simulados; a configuração pública será verificada separadamente.

## T10 — Interface dos cinco contextos

- Estado: concluída para a interface local; URL HTTPS pública pertence à T20.
- Correção: campos são preservados após erro e só são limpos após sucesso;
  botão de formulário fica desabilitado durante envio, com `aria-busy`.
- Prova de regressão: dois testes de navegador falharam antes da correção
  (campos vazios após 409 e botão habilitado durante envio) e passaram depois.
- Verificação em 30/09: `npm run test:browser`: **3 aprovados**, com navegação
  nos cinco contextos e respostas sintéticas da API; `npm run build`: aprovado.
- Execução documentada no README e testes incluídos no CI. Isso não comprova
  publicação, acessibilidade completa ou todas as operações de uma URL externa.

## T11 — F1, cliente para reserva e contrato

- Estado: concluída no escopo do protótipo, após aceite de T08, T09 e T10.
- Verificação em 30/09: testes
  `tests/test_flows.py::test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia`
  e `tests/test_extended_modules.py::test_reservation_to_contract_and_finance_payment`:
  **2 aprovados**. O mesmo UUID cadastral chega ao rascunho, a repetição preserva
  o contrato e o caminho pela reserva chega à ativação e pagamento simulado.
- Interface local já verificada na T10. A demonstração manual está em
  `ROTEIRO_DEMONSTRACAO.md`, seção F1; não foi declarada integração real ou pública.

## T16 — Workflow e F3

- Estado: concluída no escopo do protótipo.
- Correção: tarefas finais não podem reabrir; todas as tarefas finais com algum
  cancelamento encerram o processo em `CANCELLED`. Todas `DONE` o concluem.
  Repetição exata não duplica efeitos; criação e alteração são auditadas.
- Prova de regressão: quatro cenários falharam antes da correção e passaram
  depois. Prazo herdado, responsável, estados e autorização também verificados.
- Verificação em 30/09: `pytest -q tests/test_workflow.py tests/test_flows.py
  tests/test_extended_modules.py tests/test_contracts_and_architecture.py
  -p no:cacheprovider`: **30 aprovados** em uma execução sequencial.
- OpenAPI, TDD, diagrama e estado documentado atualizados. Sem motor BPM externo.

## T12 — Financeiro

- Estado: concluída no escopo canônico do protótipo: fatura, pagamento simulado
  e inadimplência por vencimento (ARCH7-12).
- Correção: frações de centavo são rejeitadas antes de arredondamento no banco;
  pagamentos efetivos são auditados, com regra no serviço do Finance.
- Prova de regressão: dois valores inválidos eram aceitos e auditoria estava
  ausente; os três cenários falharam antes e passaram após a correção.
- Verificação em 30/09: `pytest -q tests/test_finance.py
  tests/test_extended_modules.py tests/test_contracts_and_architecture.py
  -p no:cacheprovider`: **19 aprovados**. Inclui parcial/total, repetição,
  conflito, excesso, moeda, vencimento, quitação e papéis.
- OpenAPI, TDD e estado atualizados. A atribuição anterior de faturamento final
  à T12 não constava no aceite do Jira; recorrência/acerto final permanecem futuros.
  Bloqueio por linha foi incluído para PostgreSQL, sem alegar teste em banco real.
