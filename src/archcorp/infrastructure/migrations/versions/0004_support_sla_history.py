"""histórico, abertura, reconciliação e resolução do chamado (T15)

Revision ID: 0004_support_sla_history
Revises: 0003_contract_closing
Create Date: 2026-10-14 21:41:19.499881

Migração aditiva (ADR-002): cria `support_ticket_history` e acrescenta colunas
anuláveis a `support_tickets`. Chamados existentes ficam sem `opened_at`; o
serviço trata a ausência como dado legado.
"""
from alembic import op
import sqlalchemy as sa


revision = '0004_support_sla_history'
down_revision = '0003_contract_closing'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('support_ticket_history',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('ticket_id', sa.String(length=36), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('action', sa.String(length=30), nullable=False),
    sa.Column('from_status', sa.String(length=30), nullable=True),
    sa.Column('to_status', sa.String(length=30), nullable=False),
    sa.Column('owner', sa.String(length=80), nullable=True),
    sa.Column('previous_owner', sa.String(length=80), nullable=True),
    sa.Column('actor_role', sa.String(length=30), nullable=True),
    sa.Column('sla_status', sa.String(length=20), nullable=True),
    sa.Column('correlation_id', sa.String(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('support_ticket_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_support_ticket_history_correlation_id'), ['correlation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_support_ticket_history_ticket_id'), ['ticket_id'], unique=False)

    with op.batch_alter_table('support_tickets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('support_tickets', schema=None) as batch_op:
        batch_op.drop_column('resolved_at')
        batch_op.drop_column('reconciled_at')
        batch_op.drop_column('opened_at')

    with op.batch_alter_table('support_ticket_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_support_ticket_history_ticket_id'))
        batch_op.drop_index(batch_op.f('ix_support_ticket_history_correlation_id'))

    op.drop_table('support_ticket_history')
