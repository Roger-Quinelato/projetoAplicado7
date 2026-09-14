from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.integration.service import audit
from archcorp.workflow.models import ProcessInstance


def _start(session: Session, envelope: dict, process_type: str, reference_field: str, due_hours: int) -> None:
    payload = envelope["payload"]
    reference_id = payload[reference_field]
    if session.scalar(select(ProcessInstance).where(ProcessInstance.process_type == process_type, ProcessInstance.reference_id == reference_id)):
        return
    process = ProcessInstance(process_type=process_type, reference_id=reference_id, customer_id=payload["customerId"], due_at=datetime.now(timezone.utc) + timedelta(hours=due_hours))
    session.add(process)
    session.flush()
    audit(session, envelope["correlationId"], "workflow", f"start_{process_type.lower()}", "success", process.process_id, referenceId=reference_id)


def handle_contract_activated(session: Session, envelope: dict) -> None:
    _start(session, envelope, "ONBOARDING", "contractId", 72)


def handle_ticket_opened(session: Session, envelope: dict) -> None:
    _start(session, envelope, "TICKET_RESOLUTION", "ticketId", envelope["payload"].get("slaHours") or 24)
