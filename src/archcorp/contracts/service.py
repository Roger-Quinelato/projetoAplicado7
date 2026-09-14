from sqlalchemy import select, update
from sqlalchemy.orm import Session

from archcorp.contracts.models import Contract
from archcorp.crm.public import CustomerReader
from archcorp.integration.models import IdempotencyRecord
from archcorp.integration.service import audit, enqueue


class ContractService:
    def __init__(self, customers: CustomerReader):
        self.customers = customers

    def create_draft(self, session: Session, data: dict, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        stored = session.get(IdempotencyRecord, {"key": idempotency_key, "operation": "create_contract_draft"})
        if stored:
            return stored.response, True
        customer = self.customers.get(session, data["customerId"])
        if not customer or not customer.eligible or not customer.consent_service:
            raise ValueError("Cliente inexistente ou inelegível")
        contract = Contract(
            customer_id=customer.customer_id, customer_name=customer.name, customer_email=customer.email,
            service_code=data["serviceCode"], starts_on=data["startsOn"], amount=data["billing"]["amount"],
            currency=data["billing"]["currency"], billing_cycle=data["billing"]["cycle"], sla_hours=data.get("slaHours", 8),
        )
        session.add(contract)
        session.flush()
        response = self.to_dict(contract)
        session.add(IdempotencyRecord(key=idempotency_key, operation="create_contract_draft", response=response))
        audit(session, correlation_id, "contracts", "create_draft", "success", contract.contract_id)
        session.commit()
        return response, False

    def activate(self, session: Session, contract_id: str, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        stored = session.get(IdempotencyRecord, {"key": idempotency_key, "operation": f"activate_contract:{contract_id}"})
        if stored:
            return stored.response, True
        contract = session.get(Contract, contract_id)
        if not contract:
            raise LookupError("Contrato não encontrado")
        contract.status = "ACTIVE"
        payload = self.to_dict(contract)
        event = enqueue(session, "ContractActivated.v1", "contracts", payload, correlation_id)
        session.flush()
        response = {**payload, "eventId": event.event_id}
        session.add(IdempotencyRecord(key=idempotency_key, operation=f"activate_contract:{contract_id}", response=response))
        audit(session, correlation_id, "contracts", "activate_contract", "success", contract.contract_id)
        session.commit()
        return response, False

    def entitlement(self, session: Session, contract_id: str, customer_id: str, service_code: str) -> dict:
        contract = session.scalar(select(Contract).where(Contract.contract_id == contract_id, Contract.customer_id == customer_id, Contract.service_code == service_code, Contract.status == "ACTIVE"))
        return {"eligible": bool(contract), "slaHours": contract.sla_hours if contract else None}

    @staticmethod
    def apply_customer_update(session: Session, event: dict) -> None:
        payload = event["payload"]
        session.execute(update(Contract).where(Contract.customer_id == payload["customerId"]).values(customer_name=payload["name"], customer_email=payload["email"]))

    @staticmethod
    def to_dict(contract: Contract) -> dict:
        return {
            "contractId": contract.contract_id, "customerId": contract.customer_id,
            "serviceCode": contract.service_code, "startsOn": contract.starts_on.isoformat(),
            "billing": {"amount": float(contract.amount), "currency": contract.currency, "cycle": contract.billing_cycle},
            "slaHours": contract.sla_hours, "status": contract.status,
        }
