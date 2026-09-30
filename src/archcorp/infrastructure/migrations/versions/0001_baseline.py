"""baseline das tabelas do protótipo

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-09-29 17:18:39.607630
"""
from alembic import op
import sqlalchemy as sa


revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('contracts_contracts',
    sa.Column('contract_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('customer_name', sa.String(length=150), nullable=False),
    sa.Column('customer_email', sa.String(length=254), nullable=False),
    sa.Column('service_code', sa.String(length=80), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('billing_cycle', sa.String(length=20), nullable=False),
    sa.Column('sla_hours', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('contract_id'),
    sa.UniqueConstraint('customer_id', 'service_code', 'starts_on', name='uq_contract_business_key')
    )
    with op.batch_alter_table('contracts_contracts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contracts_contracts_customer_id'), ['customer_id'], unique=False)

    op.create_table('contracts_reservations',
    sa.Column('reservation_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('vehicle_group', sa.String(length=50), nullable=False),
    sa.Column('protection_code', sa.String(length=50), nullable=False),
    sa.Column('service_code', sa.String(length=80), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('billing_cycle', sa.String(length=20), nullable=False),
    sa.Column('sla_hours', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('contract_id', sa.String(length=36), nullable=True),
    sa.PrimaryKeyConstraint('reservation_id')
    )
    with op.batch_alter_table('contracts_reservations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contracts_reservations_customer_id'), ['customer_id'], unique=False)

    op.create_table('crm_contacts',
    sa.Column('contact_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.PrimaryKeyConstraint('contact_id')
    )
    with op.batch_alter_table('crm_contacts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_crm_contacts_customer_id'), ['customer_id'], unique=False)

    op.create_table('crm_customers',
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('eligible', sa.Boolean(), nullable=False),
    sa.Column('consent_service', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('customer_id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('crm_opportunities',
    sa.Column('opportunity_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('opportunity_id')
    )
    with op.batch_alter_table('crm_opportunities', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_crm_opportunities_customer_id'), ['customer_id'], unique=False)

    op.create_table('finance_invoices',
    sa.Column('invoice_id', sa.String(length=36), nullable=False),
    sa.Column('contract_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('invoice_id'),
    sa.UniqueConstraint('contract_id', name='uq_invoice_contract')
    )
    with op.batch_alter_table('finance_invoices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finance_invoices_customer_id'), ['customer_id'], unique=False)

    op.create_table('finance_payments',
    sa.Column('payment_id', sa.String(length=36), nullable=False),
    sa.Column('invoice_id', sa.String(length=36), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('reference', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('payment_id'),
    sa.UniqueConstraint('reference')
    )
    with op.batch_alter_table('finance_payments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_finance_payments_invoice_id'), ['invoice_id'], unique=False)

    op.create_table('integration_audit',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('correlation_id', sa.String(length=64), nullable=False),
    sa.Column('module', sa.String(length=50), nullable=False),
    sa.Column('operation', sa.String(length=100), nullable=False),
    sa.Column('result', sa.String(length=30), nullable=False),
    sa.Column('entity_id', sa.String(length=64), nullable=True),
    sa.Column('details', sa.JSON(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('integration_audit', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_integration_audit_correlation_id'), ['correlation_id'], unique=False)

    op.create_table('integration_idempotency',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('operation', sa.String(length=100), nullable=False),
    sa.Column('response', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key', 'operation')
    )
    op.create_table('integration_inbox',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('consumer', sa.String(length=50), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'consumer', name='uq_inbox_event_consumer')
    )
    op.create_table('integration_legacy_ids',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('entity_type', sa.String(length=50), nullable=False),
    sa.Column('global_id', sa.String(length=36), nullable=False),
    sa.Column('source_system', sa.String(length=50), nullable=False),
    sa.Column('legacy_id', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_system', 'legacy_id', name='uq_legacy_source_id')
    )
    with op.batch_alter_table('integration_legacy_ids', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_integration_legacy_ids_global_id'), ['global_id'], unique=False)

    op.create_table('integration_outbox',
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('event_version', sa.Integer(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('correlation_id', sa.String(length=64), nullable=False),
    sa.Column('causation_id', sa.String(length=64), nullable=True),
    sa.Column('producer', sa.String(length=50), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('event_id')
    )
    with op.batch_alter_table('integration_outbox', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_integration_outbox_correlation_id'), ['correlation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_integration_outbox_event_type'), ['event_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_integration_outbox_status'), ['status'], unique=False)

    op.create_table('support_assignments',
    sa.Column('ticket_id', sa.String(length=36), nullable=False),
    sa.Column('owner', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('ticket_id')
    )
    op.create_table('support_tickets',
    sa.Column('ticket_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('contract_id', sa.String(length=36), nullable=False),
    sa.Column('service_code', sa.String(length=80), nullable=False),
    sa.Column('category', sa.String(length=80), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('priority', sa.String(length=20), nullable=False),
    sa.Column('sla_hours', sa.Integer(), nullable=True),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('ticket_id')
    )
    with op.batch_alter_table('support_tickets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_support_tickets_contract_id'), ['contract_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_support_tickets_customer_id'), ['customer_id'], unique=False)

    op.create_table('workflow_instances',
    sa.Column('process_id', sa.String(length=36), nullable=False),
    sa.Column('process_type', sa.String(length=40), nullable=False),
    sa.Column('reference_id', sa.String(length=36), nullable=False),
    sa.Column('customer_id', sa.String(length=36), nullable=False),
    sa.Column('state', sa.String(length=30), nullable=False),
    sa.Column('owner', sa.String(length=80), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('process_id'),
    sa.UniqueConstraint('process_type', 'reference_id', name='uq_process_reference')
    )
    with op.batch_alter_table('workflow_instances', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_instances_customer_id'), ['customer_id'], unique=False)

    op.create_table('workflow_tasks',
    sa.Column('task_id', sa.String(length=36), nullable=False),
    sa.Column('process_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('state', sa.String(length=30), nullable=False),
    sa.Column('owner', sa.String(length=80), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('task_id')
    )
    with op.batch_alter_table('workflow_tasks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workflow_tasks_process_id'), ['process_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('workflow_tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workflow_tasks_process_id'))

    op.drop_table('workflow_tasks')
    with op.batch_alter_table('workflow_instances', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workflow_instances_customer_id'))

    op.drop_table('workflow_instances')
    with op.batch_alter_table('support_tickets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_support_tickets_customer_id'))
        batch_op.drop_index(batch_op.f('ix_support_tickets_contract_id'))

    op.drop_table('support_tickets')
    op.drop_table('support_assignments')
    with op.batch_alter_table('integration_outbox', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_integration_outbox_status'))
        batch_op.drop_index(batch_op.f('ix_integration_outbox_event_type'))
        batch_op.drop_index(batch_op.f('ix_integration_outbox_correlation_id'))

    op.drop_table('integration_outbox')
    with op.batch_alter_table('integration_legacy_ids', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_integration_legacy_ids_global_id'))

    op.drop_table('integration_legacy_ids')
    op.drop_table('integration_inbox')
    op.drop_table('integration_idempotency')
    with op.batch_alter_table('integration_audit', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_integration_audit_correlation_id'))

    op.drop_table('integration_audit')
    with op.batch_alter_table('finance_payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_finance_payments_invoice_id'))

    op.drop_table('finance_payments')
    with op.batch_alter_table('finance_invoices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_finance_invoices_customer_id'))

    op.drop_table('finance_invoices')
    with op.batch_alter_table('crm_opportunities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_crm_opportunities_customer_id'))

    op.drop_table('crm_opportunities')
    op.drop_table('crm_customers')
    with op.batch_alter_table('crm_contacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_crm_contacts_customer_id'))

    op.drop_table('crm_contacts')
    with op.batch_alter_table('contracts_reservations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contracts_reservations_customer_id'))

    op.drop_table('contracts_reservations')
    with op.batch_alter_table('contracts_contracts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contracts_contracts_customer_id'))

    op.drop_table('contracts_contracts')
