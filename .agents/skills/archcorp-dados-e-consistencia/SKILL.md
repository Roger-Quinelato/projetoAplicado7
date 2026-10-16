---
name: archcorp-dados-e-consistencia
description: >
  Use quando a mudança envolve transação, concorrência, bloqueio, idempotência, outbox/inbox,
  reentrega ou ordem de eventos, prazos e datas, ou diferença de comportamento entre SQLite e
  PostgreSQL no ArchCorp. Também ao revisar se um teste prova concorrência ou só repetição.
---

# Dados e consistência no ArchCorp

Ponto de partida: os riscos P1 abertos na auditoria de 16/10/2026 são de **isolamento e
ordenação**, não de sintaxe (Q-02 ativação concorrente, Q-03 evento fora de ordem).

## 1. Classifique o problema antes de escolher o mecanismo

| Sintoma | Classe | Mecanismo neste repositório |
|---|---|---|
| Duas requisições leem o mesmo estado e ambas transicionam (ex.: ativar contrato duas vezes com chaves diferentes) | *Lost update* / *write skew* | Bloquear a entidade (`with_for_update`) **ou** `UPDATE ... WHERE estado = esperado` e conferir linhas afetadas; reler estado e replay depois de obter exclusividade |
| Mesma requisição repetida (rede, retry do cliente) | Repetição | `Idempotency-Key` com impressão digital do pedido (`integration.public`); mesma chave + corpo diferente = `409` |
| Mesmo evento entregue de novo | Reentrega | Inbox por `eventId` + consumidor (`InboxEvent`), unicidade de negócio no destino |
| Eventos **diferentes** chegam fora de ordem | Ordenação | Inbox **não** resolve. Usar versão monotônica + atualização condicional, ou reler a fonte oficial pela porta pública no consumo |
| Efeito depende de "agora" no consumidor | Tempo do processamento ≠ tempo do evento | Usar o instante publicado no evento (`occurredAt`, `dueAt`), nunca `datetime.now()` do consumidor (Q-01) |

Idempotência protege contra **repetição**; não protege contra **concorrência** nem contra
**ordem**. Não trate uma como prova das outras.

## 2. Outbox e despacho (estado atual, `integration/service.py`)

- O comando grava o estado e o evento na **mesma transação** (`enqueue`).
- `dispatch_pending` pega eventos `PENDING` com `with_for_update(skip_locked=True)` e executa cada
  consumidor em `begin_nested()`; falha de um consumidor não desfaz os outros e vira falha
  registrada para reprocessamento explícito.
- RabbitMQ recebe cópia opcional; ele **não** entrega aos consumidores de negócio e uma recusa do
  broker desfaz a tentativa (Q-10). Não afirme entrega "exatamente uma vez".
- Logs da outbox não incluem mensagem SQL nem traceback (privacidade); preserve isso.

## 3. Datas e tempo

- Tudo em UTC ISO 8601 (`AGENTS.md`). SQLite devolve `datetime` sem fuso: normalize na leitura
  (padrão `as_utc`/`iso_utc` em `support/domain.py`) antes de comparar ou serializar.
- Relógio injetável nos serviços que dependem de "agora" (Finance, Support). Em teste de atraso,
  controle também o relógio do **consumidor**, senão o teste passa pelo motivo errado.

## 4. SQLite não prova o que PostgreSQL promete

| Afirmação | Onde provar |
|---|---|
| Bloqueio, `skip_locked`, corrida entre sessões | `tests/test_postgresql_concurrency.py` com `TEST_DATABASE_URL` (job `postgresql` da CI) |
| Limite `Numeric(14,2)` e tipos | PostgreSQL (SQLite aceita valores que o PostgreSQL recusa; Q-06) |
| Migração e convergência | `tests/test_migration_convergence.py` em PostgreSQL |

A fixture `clean_database` (`tests/conftest.py`) executa `drop_all`. **Nunca** aponte
`TEST_DATABASE_URL` para um banco de demonstração ou persistente.

## 5. Teste de concorrência que vale como evidência

1. Duas sessões independentes sincronizadas **depois** da leitura do estado (barreira), não duas
   chamadas sequenciais.
2. Casos: chaves iguais, chaves diferentes, comando concorrente oposto (ativar × cancelar).
3. Asserções sobre efeitos, não só status HTTP: uma transição, um evento na outbox, uma auditoria,
   nenhum `500`.
4. Marcar com o mesmo critério de skip dos testes PostgreSQL existentes e informar o skip no
   resultado.

## 6. Perguntas de revisão

- Esta mudança promete algo sob concorrência? O teste é concorrente de fato?
- O consumidor depende de ordem? O que acontece se o evento anterior chegar depois?
- O reprocessamento pode duplicar efeito de negócio (fatura, processo, tarefa)?
- Algum prazo é derivado do momento do processamento?
