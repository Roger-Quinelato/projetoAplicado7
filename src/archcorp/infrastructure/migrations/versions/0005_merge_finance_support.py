"""Converge as revisões publicadas T12/T15 sem reescrever seus identificadores.

Não há prova de que nunca tenham sido aplicadas em bancos persistentes. As duas
expansões são independentes; esta revisão preserva upgrades de qualquer frente.
"""

revision = "0005_merge_finance_support"
down_revision = ("0004_finance_lifecycle", "0004_support_sla_history")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
