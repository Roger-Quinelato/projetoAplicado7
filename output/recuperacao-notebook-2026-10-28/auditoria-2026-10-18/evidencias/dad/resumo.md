# Resumo da frente F-DAD

Referência: `main` = `44b8325`. Execução na cópia `iso-dad` com SQLite descartável, em 19/10/2026 (UTC 11:09–11:25). Sem Docker; PostgreSQL e RabbitMQ indisponíveis localmente.

## Contagem de achados (18)
- Alta: 1 (DAD-03). Média: 8 (DAD-01, 02, 04, 06, 07, 08, 09, 10). Baixa: 8 (DAD-05, 11, 12, 13, 14, 15, 16, 17). Informativa: 1 (DAD-18).

## Cinco mais graves
1. DAD-03 · Broker acoplado ao consumo interno (AUD-05/Q-10) · alta · confiança alta · `integration/service.py:38,46,108-145` e `docker-compose.yml:6`.
2. DAD-02 · Reprocessamento sobrescreve a projeção mais nova (AUD-04/Q-03) · média · alta · `contracts/service.py:166-169`.
3. DAD-07 · 11 de 278 exemplos OpenAPI inválidos; tipo monetário diferente entre rotas (AUD-20/Q-05) · média · alta · `contracts/schemas.py:49`, `contracts/service.py:178`.
4. DAD-08 · `Money` do AsyncAPI rejeita 19,99 e 0,07 (AUD-21/Q-04) · média · alta · `docs/events/asyncapi.yaml:397`.
5. DAD-10 · ONBOARDING de 72 h conta do despacho, não do evento (resíduo do Q-01) · média · alta · `workflow/service.py:40-42`.
(DAD-01, ativação sem bloqueio (AUD-10/Q-02), também é média, com confiança média: a dupla gravação só foi confirmada por inspeção.)

## Não executados e motivo
- Corridas de PostgreSQL (ativação, reserva com chave repetida, pagamentos e resolução em PG): sem PG local; roteiros `e01`, `e08` com `ADB_URL` prontos.
- DataError real de PG (poison e drafts de 1e12): sem PG local; roteiros `e07` e `e04` prontos.
- Fila cheia e recusa do broker: sem RabbitMQ local; coberto por `tests/test_rabbitmq_real.py` (job rabbitmq da CI).
- Caso 5 de migração em PG (AUD-33): sem PG; `mig_exp.py` de 01/10 reaproveitado, não executado.
- Host sem resposta do broker (10–15 s): não reexecutado; medido só com porta fechada.
- Suíte completa: fica com F-QUA; aqui, 11 arquivos ligados à F-DAD (152 passed, 10 skipped).
- Revisão cruzada (`archcorp-revisao`): fase posterior, não feita.

## Premissas
1. Resultados de SQLite não são afirmados para PostgreSQL. Onde a afirmação depende de PG, o estado é aberto ou parcial e a evidência é inspeção, CI ou 01/10.
2. `RABBITMQ_URL` é definida só no `docker-compose.yml` (linha 6); `render.yaml` não a define. DAD-03 vale para essa configuração.
3. AGENTS.md, AsyncAPI, OpenAPI e ADRs são critério, não redação. O dinheiro como número na v1 é dívida aceita (ADR-003 §2), não achado.
4. Os 500 de E-08 são causados por bloqueio do SQLite: inferência, porque o tipo da exceção só aparece no log do dispatch (`OperationalError`).
5. Os 2 skips do job `postgresql` da CI são os 2 testes de RabbitMQ (inferência pela configuração do job; o `-q` não lista o motivo).
6. Dados sintéticos; logs de INFO desligados; nenhum segredo ou credencial real nos logs.

## Perguntas ao usuário (3)
1. Com `RABBITMQ_URL` definida, o broker é obrigatório (consumo ou auditoria) ou é cópia opcional? Decide DAD-03: desacoplar o código ou ajustar o contrato com ADR.
2. O prazo de 72 h do ONBOARDING conta do evento (`occurredAt`) ou do despacho? (DAD-10)
3. Na API v1, o valor monetário fica como número (dívida aceita) ou padroniza como string com exceção registrada em ADR? (DAD-07)

## Arquivos
- `evidencias.md` (E-DAD-01 a E-DAD-24), `achados.md` (DAD-01 a DAD-18), `linha_de_base.md` (17 itens), `resumo.md`.
- `scripts\` (`dad_common.py` e 11 roteiros de E-01 a E-12) e `logs\` (16 arquivos: execuções, CI filtrada, uvicorn e pytest).
