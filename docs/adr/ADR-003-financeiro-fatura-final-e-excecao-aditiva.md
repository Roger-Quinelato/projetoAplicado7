# ADR-003 - Financeiro da T12: exceção à migração aditiva, vencimento por evento e infraestrutura compartilhada

- Status: Proposto, em revisão do CTO (T12)
- Data: 2026-10-14
- Decisores: equipe do Projeto Aplicado; revisão do CTO
- Tarefa: T12 (ARCH7-12) - fatura, pagamento simulado e inadimplência por vencimento
- Relaciona-se com: [ADR-001](ADR-001-integracao-empresa-de-servicos.md) e [ADR-002](ADR-002-migracoes-aditivas.md)

## Contexto

A T12 exige uma fatura final quando Contracts publica `ContractClosed.v1`. Até a
revisão `0003`, `finance_invoices` tinha a restrição `uq_invoice_contract`
(uma fatura por contrato), que impede a segunda fatura do mesmo contrato. A T12
também passou a calcular vencimento e saldo por regras explícitas de domínio e a
reutilizar utilitários do contexto `integration`.

## Decisão

### 1. Exceção pontual à regra aditiva (migração `0004_finance_lifecycle`)

- A migração acrescenta `kind` (padrão `INITIAL`), `source_event_id` e
  `overdue_since`, cria `uq_invoice_contract_kind` (contrato e tipo) e
  `uq_invoice_source_event`, e remove `uq_invoice_contract`.
- Não há caminho puramente aditivo: enquanto a unicidade antiga existir, a fatura
  `FINAL` não pode ser gravada. Seguindo o item 5 do ADR-002 (expandir e
  contrair), a expansão (nova restrição) e a contração (remoção da antiga) ocorrem
  na mesma revisão, porque a contração não quebra leitor algum: a nova restrição é
  mais ampla, os dados existentes a cumprem e a primeira fatura continua única por
  contrato.
- A mesma migração reclassifica dados: faturas `OPEN` com pagamento passam a
  `PARTIALLY_PAID`, o estado que o novo ciclo de vida usa para o mesmo fato.
- O downgrade restaura a 0003 (`PARTIALLY_PAID`/`OVERDUE` voltam a `OPEN`;
  `CANCELLED` permanece) e é bloqueado, antes de qualquer alteração, se existir
  fatura `FINAL`. Faturas não são apagadas automaticamente.
- `tests/test_foundation.py` passa a detectar também `drop_constraint`,
  `drop_index` e `op.execute` com `UPDATE`/`DELETE` no upgrade. Exceções ficam em
  uma lista explícita, datada e vinculada a este ADR; hoje só a `0004`.

### 2. Vencimento pela data UTC do evento

O consumidor antigo usava `date.today() + 10 dias` (data local do processamento).
Agora o vencimento é a data UTC de `occurredAt` do evento mais 10 dias. Reprocessar
um evento dias depois gera o mesmo vencimento, e o resultado não depende do fuso da
máquina. É uma mudança de comportamento: um mesmo evento processado perto da
meia-noite pode receber vencimento um dia diferente do anterior. O prazo de 10 dias
e o uso da data do evento são premissas a validar com o negócio.

### 3. `IdempotencyStore` e `audit` como infraestrutura compartilhada

Finance usa `IdempotencyStore` e `audit` de `archcorp.integration.service`, como
Contracts e Support já fazem. Esses utilitários são tratados como infraestrutura
transversal (idempotência de comandos e trilha de auditoria) e não como regra de
negócio de Integration; nenhum modelo de outro contexto de negócio é importado. O
código não é movido agora. **Dívida registrada:** extrair esses utilitários para
`archcorp.infrastructure` em tarefa própria, com os demais contextos.

## Consequências

- Positivas: fatura final idempotente por `eventId` e única por contrato; vencimento
  determinístico; guarda de migração mais rigorosa e exceções auditáveis.
- Negativas: a 0004 não é puramente aditiva e seu downgrade exige tratar antes as
  faturas `FINAL`; Finance continua dependente de um módulo de `integration` até a
  extração.
- Riscos abertos: execução da 0004 em PostgreSQL real não verificada (só SQL
  offline); premissas de prazo e de faturamento por ciclo iniciado a validar.

## Alternativas consideradas

- Tabela separada para faturas finais: mantém a 0004 aditiva, mas duplica o modelo
  de fatura e espalha saldo e pagamento por duas tabelas.
- Somar o valor final à primeira fatura: reabriria faturas já pagas, o que não é
  aceitável em finanças.
- Manter `date.today()`: vencimento mudaria conforme o dia e o fuso do reprocessamento.
