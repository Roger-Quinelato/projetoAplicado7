---
name: archcorp-dados-e-consistencia
description: >
  Use quando a mudança envolve transação, concorrência, bloqueio, idempotência, outbox/inbox,
  reentrega ou ordem de eventos, prazos e datas, ou diferença de comportamento entre SQLite e
  PostgreSQL no ArchCorp. Também ao revisar se um teste prova concorrência ou só repetição.
---

# Dados e consistência no ArchCorp

Os riscos de dados deste repositório são sobretudo de **isolamento e ordenação**, não de sintaxe.
Retrato do estado da outbox e dos riscos abertos em 16/10/2026:
[`references/retrato-2026-10-16.md`](references/retrato-2026-10-16.md) (reconfira no SHA atual).

## 1. Classifique o problema antes de escolher o mecanismo

| Sintoma | Classe | Mecanismo neste repositório |
|---|---|---|
| Duas requisições leem o mesmo estado e ambas transicionam (ex.: ativar contrato duas vezes com chaves diferentes) | *Lost update* / *write skew* | Bloquear a entidade (`with_for_update`) **ou** `UPDATE ... WHERE estado = esperado` e conferir linhas afetadas; reler estado e replay depois de obter exclusividade |
| Mesma requisição repetida (rede, retry do cliente) | Repetição | `Idempotency-Key` com impressão digital do pedido (`integration.public`); mesma chave + corpo diferente = `409` |
| Mesmo evento entregue de novo | Reentrega | Inbox por `eventId` + consumidor (`InboxEvent`), unicidade de negócio no destino |
| Eventos **diferentes** chegam fora de ordem | Ordenação | Inbox **não** resolve. Usar versão monotônica + atualização condicional, ou reler a fonte oficial pela porta pública no consumo |
| Efeito depende de "agora" no consumidor | Tempo do processamento ≠ tempo do evento | Usar o instante publicado no evento (`occurredAt`, `dueAt`), nunca `datetime.now()` do consumidor |

Idempotência protege contra **repetição**; não protege contra **concorrência** nem contra
**ordem**. Não trate uma como prova das outras.

## 2. Outbox e despacho: o que preservar

- O comando grava o estado e o evento na **mesma transação**.
- Falha de um consumidor não desfaz os outros e vira falha registrada para reprocessamento
  explícito.
- Não afirme entrega "exatamente uma vez"; confira no SHA atual o papel do broker antes de
  descrevê-lo.
- Logs da outbox não incluem mensagem SQL nem traceback (privacidade).

## 3. Datas e tempo

- Tudo em UTC ISO 8601 (`AGENTS.md`). SQLite devolve `datetime` sem fuso: normalize na leitura
  (padrão `as_utc`/`iso_utc` em `support/domain.py`) antes de comparar ou serializar.
- Relógio injetável nos serviços que dependem de "agora". Em teste de atraso, controle também o
  relógio do **consumidor**, senão o teste passa pelo motivo errado.

## 4. SQLite não prova o que PostgreSQL promete

| Afirmação | Onde provar |
|---|---|
| Bloqueio, `skip_locked`, corrida entre sessões | `tests/test_postgresql_concurrency.py` com `TEST_DATABASE_URL` (job `postgresql` da CI) |
| Limite `Numeric(14,2)` e tipos | PostgreSQL (SQLite aceita valores que o PostgreSQL recusa) |
| Migração e convergência | `tests/test_migration_convergence.py` em PostgreSQL |

Afirmação que **não** depende dessas propriedades pode ser provada em SQLite.

A fixture `clean_database` (`tests/conftest.py`) executa `drop_all`. **Nunca** aponte
`TEST_DATABASE_URL` para um banco de demonstração ou persistente.

## 5. Teste de concorrência que vale como evidência

1. Duas sessões independentes sincronizadas **depois** da leitura do estado (barreira), não duas
   chamadas sequenciais.
2. Casos: chaves iguais, chaves diferentes, comando concorrente oposto (ativar × cancelar).
3. Asserções sobre efeitos, não só status HTTP: uma transição, um evento na outbox, uma auditoria,
   nenhum `500`.
4. Mesmo critério de skip dos testes PostgreSQL existentes, com o skip informado no resultado.

## 6. Perguntas de revisão

- Esta mudança promete algo sob concorrência? O teste é concorrente de fato?
- O consumidor depende de ordem? O que acontece se o evento anterior chegar depois?
- O reprocessamento pode duplicar efeito de negócio (fatura, processo, tarefa)?
- Algum prazo é derivado do momento do processamento?
