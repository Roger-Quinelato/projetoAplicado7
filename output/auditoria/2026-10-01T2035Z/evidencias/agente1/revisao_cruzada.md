# Revisão cruzada — Agente 1 (onda 2)

Data: 01/10/2026. Referência: `3a3d8bd` (cópia `$SP/iso`). Inspeção de código mais um experimento pontual próprio (`$SP/agente1/rx/x1_meio_centavo.py`, saída em `rx/x1.out`), executado com o harness e o venv do Agente 2 em SQLite descartável (`$SP/agente2/run/x1_ag1.db`). A suíte pytest não foi executada.

Também nesta onda: **A1-17 retirado (não procede)**. O coordenador confirmou que criou `output/auditoria/2026-10-01T2035Z` de propósito.

---

## A2-04 — Pagamento aceita frações de centavo e registra pagamentos de valor efetivo 0,00

**Veredito: CONFIRMADO COM AJUSTE.** Severidade que eu atribuiria: **média** (o Agente 2 propôs alta).

### Evidência
- `src/archcorp/finance/routes.py:42`: `amount: Decimal = Field(gt=0)`, sem `decimal_places=2`. Em contraste, `schemas.py:111` e `contracts/routes.py:85` usam `decimal_places=2`, o que mostra uma inconsistência interna de validação.
- `routes.py:43`: `currency` só tem `min_length=3, max_length=3`. O efeito é nulo na prática, porque a linha 121 exige igualdade com a moeda da fatura.
- `finance/models.py:27`: `Payment.amount = Numeric(14, 2)`.
- `routes.py:129` e `:135` comparam `total + body.amount` com o valor **não quantizado** recebido. `paid_total` (linha 91) soma os valores **relidos** do banco, já em 2 casas.
- `e07.out`:
  - `0.001` e `0.004` retornaram `201`.
  - `/payments` lista os dois com `amount 0.0`.
  - O SQLite guarda `('REF-0001','real',0.001), ('REF-0004','real',0.004)`.
  - Em seguida, `100.10` quita a fatura (`PAID`). Resultado: dois lançamentos com valor exibido 0,00 e uma soma bruta (100,105) diferente do valor da fatura.
- Experimento próprio `rx/x1.out` (fatura de 100,10):
  - `100.095` → `201`, `paidAmount` relido `100.09`, status `OPEN`. O SQLite relê o float 100,095 como 100,09.
  - Depois, `0.01` → `PAID`, e `0.004` → `409`.

### Ajustes e divergências
1. A frase "em PostgreSQL `numeric(14,2)` arredondaria 0.005 → 0.01" está imprecisa. Cada pagamento é arredondado **individualmente** na gravação: 0.001 → 0.00 e 0.004 → 0.00. Nunca existe uma linha com 0.005.
2. A divergência real entre ambientes é outra, e é inferida (não executei em PG). O PostgreSQL arredonda `numeric` por meio-para-cima, então 100.095 seria gravado como 100.10. O SQLite relê o float como 100.09.
3. No PG, a linha 135 compararia 100.095 com 100.10 em memória e manteria a fatura `OPEN`, com saldo relido zero. Qualquer pagamento posterior bateria em `total + x > amount` e receberia `409`. A fatura ficaria `OPEN` para sempre e viraria `OVERDUE` ao vencer, mesmo integralmente paga. Esse cenário é mais grave que o descrito no achado e deveria ser confirmado pelo Agente 3 em PG descartável.
4. **Por que média e não alta:**
   - Exige entrada malformada (mais de 2 casas decimais) enviada por papel autorizado (`finance`/`admin`).
   - O pagamento é simulado, sem PSP nem dinheiro real.
   - O valor exibido continua coerente com a regra de 2 casas.
   - Ainda assim, viola RNF-01/`AGENT.md` ("decimal com moeda explícita") e o critério de T12 (pagamento simulado e inadimplência). Pode produzir uma fatura paga marcada como inadimplente em PG, o que justifica média.

### Correção sugerida (concordo com o Agente 2, com acréscimo)
- `Field(gt=0, decimal_places=2)`.
- Quantizar `body.amount` para `Decimal("0.01")` antes das comparações das linhas 129 e 135.
- Teste parametrizado em SQLite e PG com `100.095`, que deve retornar `422`.

---

## A3-01 — Erro de banco num consumidor bloqueia a outbox e nunca chega a FAILED (equivale a A2-01)

**Veredito: CONFIRMADO COM AJUSTE.** Severidade que eu atribuiria: **alta**, mantida, com escopo de impacto reescrito.

### Causa confirmada por inspeção (`src/archcorp/integration/service.py:21-46`)
- Os handlers chamam `session.flush()` dentro do `try`: `finance/service.py:20` e `workflow/service.py:17`. Um erro de banco (IntegrityError, DataError, OperationalError) é lançado ali e capturado pelo `except Exception` (linha 37).
- O `except` altera `event.attempts` e `event.last_error` e não faz `session.rollback()`. Não há nenhum `rollback` ou `begin_nested` em `src/` (`grep -rn "rollback\|begin_nested" src/archcorp` → vazio).
- `session.commit()` (linha 45) fica **fora** do `try/except`, no corpo do `for`. Com a sessão em estado de rollback pendente, o commit lança `PendingRollbackError`, que sai do laço e da rota `dispatch_outbox` (`main.py:522-523`) como HTTP 500.
- Consequências:
  - O incremento de `attempts` se perde, porque a transação é descartada no fechamento da sessão (`db.py:32-34`).
  - O evento continua `PENDING` com `attempts = 0`.
  - Como a leitura é `order_by(occurred_at)` (linha 22), cada novo despacho volta a parar no mesmo evento. É um bloqueio de cabeça de fila: os eventos posteriores nunca são despachados, e `/integration/failures` fica vazio.
- Exceções que **não** são de banco (por exemplo `KeyError` no payload) seguem o caminho correto: o commit funciona, `attempts` incrementa e o evento chega a `FAILED`. O defeito é específico de erros que invalidam a transação.
- Sem rollback, o efeito parcial do evento envenenado também é descartado, então não há escrita parcial. Os eventos anteriores ao veneno, já commitados um a um, ficam preservados.

### Realismo do gatilho sem injeção (ajuste principal)
1. **Despacho concorrente (A3-02): realista, mas o efeito é transitório.** Dois despachos leem o mesmo `PENDING` (sem `FOR UPDATE SKIP LOCKED`). O segundo passa pelo check-then-insert de `finance/service.py:12` ou `workflow/service.py:13` e viola `uq_invoice_contract`, `uq_process_reference` ou `uq_inbox_event_consumer` no `flush`, caindo exatamente neste caminho e retornando 500. Mas o primeiro despacho commita o evento como `PUBLISHED`, então o seguinte não fica bloqueado. Resultado: 500 intermitente, sem perda nem duplicidade. Isso é coerente com os "15/15 → [200, 500]" do A3-02.
2. **Erros transitórios do PostgreSQL** (queda de conexão no meio da transação, timeout, deadlock, pausa do Supabase Free): plausíveis na demo pública. Também resultam em 500 sem contabilizar `attempts`. Se o erro persistir, o evento nunca chega a `FAILED`.
3. **Bloqueio permanente:** exige um erro de banco **determinístico** para um evento específico. Pela API isso é improvável hoje:
   - Valores monetários do contrato já são limitados por `decimal_places=2`, e um valor fora de `Numeric(14,2)` falharia antes, na gravação do contrato (500 no rascunho), e não na outbox.
   - UUIDs e moeda são validados.
   - Restam como gatilhos realistas: deriva de esquema (migração ausente ou incompatível no banco publicado), dados legados ou um evento gravado por outro produtor. Em SQLite, o veneno de `1e20` usado no `poison_exp.py` nem seria detectado, porque o SQLite não impõe a precisão; por isso a suíte atual não pega o defeito.

### Por que manter alta
- Viola requisitos explícitos e centrais: `AGENT.md` ("Encaminhe falhas permanentes para fila de erro"; "Nunca capture uma exceção sem registrar contexto ou convertê-la em resultado tratado"), RNF-02 e o critério de T17 ("falhas recuperáveis").
- Já tinha sido apontado na auditoria de 29/09 (T-02, "Importante") e continua sem correção em `3a3d8bd`.
- Tem gatilho real demonstrado (concorrência, A3-02).
- Quando o erro é determinístico, a falha fica invisível ao operador.

### Ajuste de texto sugerido para A3-01 e A2-01
Trocar "um único evento incompatível paralisa F2/F3" por: "um erro de banco determinístico paralisa a outbox; o gatilho reproduzido sem injeção (despacho concorrente) gera HTTP 500 transitório, sem perda nem duplicidade; o bloqueio permanente foi reproduzido apenas com evento injetado (PG)". Registrar também que o `commit` da linha 45 fica fora do `try`, o que faz qualquer falha de commit abortar o lote inteiro.

### Correção (concordo)
- `session.rollback()` no `except`, seguido de recarga do evento e gravação de `attempts`/`last_error` (ou um savepoint por consumidor com `begin_nested()`).
- `commit` protegido por evento.
- `FOR UPDATE SKIP LOCKED` em PG.
- Aceite: teste com handler que viola uma restrição única chega a `FAILED` após `retry_limit`, os eventos seguintes são despachados, e dois despachos concorrentes em PG retornam 200/200.

---

## Síntese

| Achado | Veredito | Severidade proposta | Divergência principal |
|---|---|---|---|
| A2-04 | CONFIRMADO COM AJUSTE | média (Agente 2: alta) | A explicação do arredondamento em PG está imprecisa. O risco real em PG (inferido) é 100,095 → 100,10 deixar a fatura OPEN/OVERDUE com saldo zero. Precisa de confirmação em PG |
| A3-01 / A2-01 | CONFIRMADO COM AJUSTE | alta (mantida) | Causa confirmada (sem rollback e com commit fora do try). Sem injeção, o gatilho realista é o despacho concorrente, que dá 500 transitório. O bloqueio permanente exige erro de banco determinístico, hoje improvável pela API |
| A1-17 (meu) | NÃO PROCEDE | — | Diretório criado pelo coordenador |
