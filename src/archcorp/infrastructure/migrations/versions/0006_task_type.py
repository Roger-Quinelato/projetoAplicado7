"""tipo próprio da tarefa (inclui devolução)

Revision ID: 0006_task_type
Revises: 0005_merge_finance_support
"""
from alembic import op
import sqlalchemy as sa


revision = '0006_task_type'
down_revision = '0005_merge_finance_support'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Acrescenta o tipo da tarefa, nulável; tarefas anteriores seguem o tipo do processo na leitura."""
    op.add_column('workflow_tasks', sa.Column('task_type', sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Remove o tipo da tarefa."""
    # DROP COLUMN direto: o lote do SQLite recriaria a tabela e deixaria resíduo se o downgrade seguinte falhar.
    op.drop_column('workflow_tasks', 'task_type')
