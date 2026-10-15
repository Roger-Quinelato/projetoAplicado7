"""ciclo de vida da fatura, faturamento final e inadimplência (T12)

Revision ID: 0004_finance_lifecycle
Revises: 0003_contract_closing
Create Date: 2026-10-14 12:00:00

Compatibilidade (ADR-002):
- colunas novas são anuláveis ou têm valor padrão; faturas existentes recebem `kind = INITIAL`;
- a unicidade "uma fatura por contrato" (`uq_invoice_contract`) passa a ser "uma fatura por
  contrato e tipo" (`uq_invoice_contract_kind`). A restrição antiga é substituída, não removida
  sem substituta: a nova é mais ampla, os dados atuais a cumprem e nenhum leitor da versão 1
  depende da antiga. É o único ponto não puramente aditivo e está registrado em
  docs/ESTADO_IMPLEMENTACAO.md para revisão;
- faturas antigas `OPEN` com pagamento registrado passam a `PARTIALLY_PAID`, o estado que o
  novo ciclo de vida usa para o mesmo fato.

O downgrade recria a unicidade por contrato e por isso falha se existir fatura `FINAL`;
faturas financeiras não são apagadas automaticamente. `PARTIALLY_PAID` e `OVERDUE` voltam a
`OPEN`; `CANCELLED` não tem equivalente na revisão anterior e permanece como está.
"""
from alembic import op
import sqlalchemy as sa


revision = '0004_finance_lifecycle'
down_revision = '0003_contract_closing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('finance_invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('kind', sa.String(length=20), server_default='INITIAL', nullable=False))
        batch_op.add_column(sa.Column('source_event_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('overdue_since', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint('uq_invoice_contract_kind', ['contract_id', 'kind'])
        batch_op.create_unique_constraint('uq_invoice_source_event', ['source_event_id'])
        batch_op.drop_constraint('uq_invoice_contract', type_='unique')

    op.execute(
        "UPDATE finance_invoices SET status = 'PARTIALLY_PAID' WHERE status = 'OPEN' AND EXISTS "
        "(SELECT 1 FROM finance_payments WHERE finance_payments.invoice_id = finance_invoices.invoice_id)"
    )


def downgrade() -> None:
    op.execute("UPDATE finance_invoices SET status = 'OPEN' WHERE status IN ('PARTIALLY_PAID', 'OVERDUE')")
    with op.batch_alter_table('finance_invoices', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_invoice_contract', ['contract_id'])
        batch_op.drop_constraint('uq_invoice_source_event', type_='unique')
        batch_op.drop_constraint('uq_invoice_contract_kind', type_='unique')
        batch_op.drop_column('overdue_since')
        batch_op.drop_column('source_event_id')
        batch_op.drop_column('kind')
