"""adicionar situação ativa ao cliente

Revision ID: 0002_customer_active
Revises: 0001_baseline
Create Date: 2026-09-29 17:34:01.706459
"""
from alembic import op
import sqlalchemy as sa


revision = '0002_customer_active'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Acrescenta a situação ativa/inativa do cliente."""
    with op.batch_alter_table('crm_customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade() -> None:
    """Remove a situação ativa/inativa do cliente."""
    with op.batch_alter_table('crm_customers', schema=None) as batch_op:
        batch_op.drop_column('active')

