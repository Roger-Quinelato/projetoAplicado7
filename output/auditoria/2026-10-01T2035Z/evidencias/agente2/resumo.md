# Resumo — Agente 2 (Arquitetura e comportamento) · referência `3a3d8bd`

**Escopo:** T06–T13, T15, T16. Inspeção de código/documentos + 14 experimentos próprios (TestClient, SQLite descartável, cópia isolada). Suíte pytest **não** executada (Agente 3).

## Fatos comprovados (executados)
- OpenAPI salvo = gerado; 49 operações = 49 rotas. AsyncAPI: 6 eventos = 6 tipos do dispatcher; envelope completo.
- F1: cliente → reserva → rascunho sem recadastro; replay por `Idempotency-Key`; payload diferente → 409; cliente inativo/inexistente → 422.
- F2: ativação + outbox atômicas (falha injetada antes do commit não deixa rastro); dupla ativação e duplo despacho sem duplicar fatura/processo; reentrega e reprocessamento não duplicam efeitos (inbox + restrições únicas).
- F3: chamado com SLA, `PENDING_ENTITLEMENT`, reconciliação, resolução → Workflow concluído.
- Sem ciclos de import; nenhum contexto de negócio importa `models` de outro; Integration não contém regra de negócio.

## Achados alta severidade (nenhum crítico)
- **A2-01** Erro de banco em consumidor → 500 em loop, `attempts` não sobe, nunca `FAILED`, bloqueia eventos posteriores (`exp/e04_falhas.py` B, `exp/e05_bloqueio.py`).
- **A2-02** Broker configurado e indisponível → eventos `FAILED` com consumidores internos já concluídos, `reason: ""`, ~10 s por evento; cópia sem fila vinculada (`exp/e04`, `exp/e05`).
- **A2-03** Reprocessar `CustomerUpdated.v1` antigo sobrescreve projeção mais nova (última escrita vence) (`exp/e09`).
- **A2-04** Pagamento aceita 0,001 e registra lançamentos de 0,00; quitação depende do banco (`exp/e07`).

## Média
A2-05 despacho concorrente sem lock (handler roda 2×, perdedor 500); A2-06 ativações concorrentes → 2 `ContractActivated.v1`; A2-07 efeito parcial de consumidor que falhou é confirmado; A2-08 11/261 exemplos OpenAPI inválidos e dinheiro string×número; A2-09 AsyncAPI `multipleOf 0.01` rejeita 19,99; A2-10 contracts/support/main usam `integration.models` e os testes de arquitetura não detectam isso nem formas alternativas de import; A2-11 hexagonal parcial (Session nas portas, regras em rotas, `main.py` com 619 linhas); A2-12 encerramento não afeta fatura/chamados; A2-13 Workflow sem máquina de estados; A2-14 inadimplência só na leitura, pagamentos sem auditoria; A2-15 sem backoff/jitter, logs de falha sem `eventId`, reprocessamento sem solicitante.

## Baixa
A2-16 idempotência heterogênea (chamado ignora descrição; UI gera chave por clique); A2-17 códigos de erro divergentes e rascunho no passado; A2-18 `dueAt` sem `Z` em SQLite; A2-19 TO-BE/DDD listam 3 eventos, `causationId` sempre nulo; A2-20 chamado pendente aceita contrato inexistente.

## Conclusão por tarefa
| T | Conclusão |
|---|---|
| T06 | Parcial |
| T07 | Parcial (migrações/dados sintéticos: não verificado) |
| T08 | Comprovado (amostra) |
| T09 | Parcial |
| T10 | Parcial (inspeção; build não verificado) |
| T11 | Comprovado via API |
| T12 | Parcial |
| T13 | Parcial |
| T15 | Comprovado via API, com ressalvas |
| T16 | Parcial |

## Adequação
Arquitetura adequada e proporcional ao protótipo (monólito modular, outbox, portas); não há necessidade de microsserviços. Prioridade de correção: despachante (savepoint por consumidor, rollback, lock/lease, separar broker), versão em projeções, tipo monetário único, validação de exemplos/contratos em teste, ampliar teste de fronteiras.

## Limitações
SQLite serializa escritas (concorrência com barreira forçada); falhas de consumidor injetadas em memória; RabbitMQ/PostgreSQL não executados (pedidos P-01..P-07); commits posteriores a 3a3d8bd não auditáveis (L-01); diagrama Mermaid não renderizado (não enviado a serviço externo).
