"""encerramento de contrato e impressão digital de idempotência

Revision ID: 0003_contract_closing
Revises: 0002_customer_active
Create Date: 2026-09-29 17:38:13.154443
"""
from alembic import op
import sqlalchemy as sa


revision = '0003_contract_closing'
down_revision = '0002_customer_active'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Acrescenta data e motivo de encerramento do contrato e a impressão digital de idempotência."""
    with op.batch_alter_table('contracts_contracts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ends_on', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('close_reason', sa.String(length=200), nullable=True))

    with op.batch_alter_table('integration_idempotency', schema=None) as batch_op:
        batch_op.add_column(sa.Column('request_hash', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Remove os campos de encerramento e a impressão digital de idempotência."""
    with op.batch_alter_table('integration_idempotency', schema=None) as batch_op:
        batch_op.drop_column('request_hash')

    with op.batch_alter_table('contracts_contracts', schema=None) as batch_op:
        batch_op.drop_column('close_reason')
        batch_op.drop_column('ends_on')

