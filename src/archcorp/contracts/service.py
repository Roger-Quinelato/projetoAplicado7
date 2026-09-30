from datetime import date
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from archcorp.contracts.domain import ContractStatus, ReservationStatus, ensure_contract_transition, ensure_reservation_transition
from archcorp.contracts.models import Contract, Reservation
from archcorp.crm.public import CustomerData, CustomerReader
from archcorp.exceptions import BusinessRuleError, ConflictError, InvalidStateError, NotFoundError
from archcorp.infrastructure.db import count_rows, get_or_raise
from archcorp.integration.service import IdempotencyStore, audit, enqueue


def money(value) -> str:
    """Normaliza um valor monetário para texto com duas casas decimais."""
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


class ContractService:
    def __init__(self, customers: CustomerReader):
        """Recebe a porta de leitura de clientes do CRM."""
        self.customers = customers

    def eligible_customer(self, session: Session, customer_id: str) -> CustomerData:
        """Lê o cliente pelo CRM e exige que ele possa originar contrato."""
        customer = self.customers.get(session, customer_id)
        if not customer or not customer.can_contract:
            raise BusinessRuleError("Cliente inexistente ou inelegível")
        return customer

    def create_draft(self, session: Session, data: dict, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        """Cria o rascunho de contrato de forma idempotente e confirma a transação."""
        response, replay = self._draft(session, data, idempotency_key, correlation_id)
        session.commit()
        return response, replay

    def _draft(self, session: Session, data: dict, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        """Cria o rascunho sem confirmar a transação; reutiliza a resposta de uma Idempotency-Key já usada."""
        request = {
            "customerId": data["customerId"], "serviceCode": data["serviceCode"], "startsOn": str(data["startsOn"]),
            "endsOn": str(data["endsOn"]) if data.get("endsOn") else None,
            "billing": {"amount": money(data["billing"]["amount"]), "currency": data["billing"]["currency"], "cycle": data["billing"]["cycle"]},
            "slaHours": data.get("slaHours", 8),
        }
        stored = IdempotencyStore.replay(session, idempotency_key, "create_contract_draft", request, "Idempotency-Key já utilizada com outro contrato")
        if stored:
            return stored, True
        customer = self.eligible_customer(session, data["customerId"])
        existing = session.scalar(select(Contract).where(
            Contract.customer_id == customer.customer_id, Contract.service_code == data["serviceCode"], Contract.starts_on == data["startsOn"],
        ))
        if existing:
            raise ConflictError(f"Já existe o contrato {existing.contract_id} para este cliente, serviço e início")
        contract = Contract(
            customer_id=customer.customer_id, customer_name=customer.name, customer_email=customer.email,
            service_code=data["serviceCode"], starts_on=data["startsOn"], ends_on=data.get("endsOn"), amount=data["billing"]["amount"],
            currency=data["billing"]["currency"], billing_cycle=data["billing"]["cycle"], sla_hours=data.get("slaHours", 8),
        )
        session.add(contract)
        session.flush()
        response = self.to_dict(contract)
        IdempotencyStore.save(session, idempotency_key, "create_contract_draft", request, response)
        audit(session, correlation_id, "contracts", "create_draft", "success", contract.contract_id)
        return response, False

    def activate(self, session: Session, contract_id: str, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        """Ativa o contrato em rascunho, ativa a reserva vinculada e grava ContractActivated.v1 na outbox, de forma idempotente."""
        operation = f"activate_contract:{contract_id}"
        stored = IdempotencyStore.replay(session, idempotency_key, operation, {}, "Idempotency-Key já utilizada com outra ativação")
        if stored:
            return stored, True
        contract = self.require(session, contract_id)
        if contract.status == ContractStatus.ACTIVE:
            previous = IdempotencyStore.previous(session, operation)
            if previous:
                return previous, True
            raise InvalidStateError("Contrato já ativo sem registro da ativação original")
        ensure_contract_transition(contract.status, ContractStatus.ACTIVE)
        self.eligible_customer(session, contract.customer_id)
        contract.status = ContractStatus.ACTIVE
        reservation = self._reservation_of(session, contract_id)
        if reservation:
            ensure_reservation_transition(reservation.status, ReservationStatus.ACTIVE)
            reservation.status = ReservationStatus.ACTIVE
        payload = self.to_dict(contract)
        event = enqueue(session, "ContractActivated.v1", "contracts", payload, correlation_id)
        session.flush()
        response = {**payload, "eventId": event.event_id}
        IdempotencyStore.save(session, idempotency_key, operation, {}, response)
        audit(session, correlation_id, "contracts", "activate_contract", "success", contract.contract_id)
        session.commit()
        return response, False

    def close(self, session: Session, contract_id: str, data: dict, idempotency_key: str | None, correlation_id: str) -> tuple[dict, bool]:
        """Encerra o contrato ativo e a reserva vinculada e grava ContractClosed.v1 na outbox, de forma idempotente."""
        operation = f"close_contract:{contract_id}"
        request = {"endsOn": str(data["endsOn"]) if data.get("endsOn") else None, "reason": data.get("reason")}
        if idempotency_key:
            stored = IdempotencyStore.replay(session, idempotency_key, operation, request, "Idempotency-Key já utilizada com outro encerramento")
            if stored:
                return stored, True
        contract = self.require(session, contract_id)
        if contract.status == ContractStatus.CLOSED and idempotency_key:
            previous = IdempotencyStore.previous(session, operation)
            if previous:
                return previous, True
        ensure_contract_transition(contract.status, ContractStatus.CLOSED)
        ends_on = data.get("endsOn") or max(date.today(), contract.starts_on)
        if ends_on < contract.starts_on:
            raise BusinessRuleError("Data de encerramento anterior ao início do contrato")
        contract.status = ContractStatus.CLOSED
        contract.ends_on = ends_on
        contract.close_reason = data.get("reason")
        reservation = self._reservation_of(session, contract_id)
        if reservation:
            ensure_reservation_transition(reservation.status, ReservationStatus.CLOSED)
            reservation.status = ReservationStatus.CLOSED
        contract_data = self.to_dict(contract)
        event = enqueue(session, "ContractClosed.v1", "contracts", {**contract_data, "closeReason": contract.close_reason}, correlation_id)
        session.flush()
        response = {**contract_data, "eventId": event.event_id}
        IdempotencyStore.save(session, idempotency_key or f"auto:{event.event_id}", operation, request, response)
        audit(session, correlation_id, "contracts", "close_contract", "success", contract.contract_id, endsOn=ends_on.isoformat())
        session.commit()
        return response, False

    def entitlement(self, session: Session, contract_id: str, customer_id: str, service_code: str) -> dict:
        """Informa se há contrato ativo para cliente e serviço e devolve o SLA em horas."""
        contract = session.scalar(select(Contract).where(Contract.contract_id == contract_id, Contract.customer_id == customer_id, Contract.service_code == service_code, Contract.status == ContractStatus.ACTIVE))
        return {"eligible": bool(contract), "slaHours": contract.sla_hours if contract else None}

    @staticmethod
    def count(session: Session) -> int:
        """Conta os contratos gravados."""
        return count_rows(session, Contract)

    @staticmethod
    def require(session: Session, contract_id: str) -> Contract:
        """Devolve o contrato ou levanta NotFoundError."""
        return get_or_raise(session, Contract, contract_id, "Contrato não encontrado")

    @staticmethod
    def _reservation_of(session: Session, contract_id: str) -> Reservation | None:
        """Devolve a reserva vinculada ao contrato, se houver."""
        return session.scalar(select(Reservation).where(Reservation.contract_id == contract_id))

    @staticmethod
    def apply_customer_update(session: Session, event: dict) -> None:
        """Consumidor de CustomerUpdated.v1: atualiza a cópia de nome e e-mail do cliente nos contratos."""
        payload = event["payload"]
        session.execute(update(Contract).where(Contract.customer_id == payload["customerId"]).values(customer_name=payload["name"], customer_email=payload["email"]))

    @staticmethod
    def to_dict(contract: Contract) -> dict:
        """Serializa o contrato no formato da API e dos eventos."""
        return {
            "contractId": contract.contract_id, "customerId": contract.customer_id,
            "serviceCode": contract.service_code, "startsOn": contract.starts_on.isoformat(),
            "endsOn": contract.ends_on.isoformat() if contract.ends_on else None,
            "billing": {"amount": float(contract.amount), "currency": contract.currency, "cycle": contract.billing_cycle},
            "slaHours": contract.sla_hours, "status": str(contract.status),
        }


class ReservationService:
    def __init__(self, contracts: ContractService):
        """Recebe o ContractService usado para gerar rascunhos."""
        self.contracts = contracts

    def create(self, session: Session, data: dict, idempotency_key: str | None, correlation_id: str) -> tuple[dict, bool]:
        """Registra reserva para cliente elegível; com Idempotency-Key, reutiliza a resposta anterior."""
        request = {**data, "startsOn": str(data["startsOn"]), "endsOn": str(data["endsOn"]), "amount": money(data["amount"])}
        if idempotency_key:
            stored = IdempotencyStore.replay(session, idempotency_key, "create_reservation", request, "Idempotency-Key já utilizada com outra reserva")
            if stored:
                return stored, True
        customer = self.contracts.customers.get(session, data["customerId"])
        if not customer:
            raise NotFoundError("Cliente não encontrado")
        if not customer.can_contract:
            raise BusinessRuleError("Cliente inelegível ou sem consentimento")
        reservation = Reservation(
            customer_id=data["customerId"], vehicle_group=data["vehicleGroup"], protection_code=data["protectionCode"],
            service_code=data["serviceCode"], starts_on=data["startsOn"], ends_on=data["endsOn"], amount=data["amount"],
            currency=data["currency"], billing_cycle=data["billingCycle"], sla_hours=data["slaHours"],
        )
        session.add(reservation)
        session.flush()
        response = self.to_dict(reservation)
        if idempotency_key:
            IdempotencyStore.save(session, idempotency_key, "create_reservation", request, response)
        audit(session, correlation_id, "contracts", "create_reservation", "success", reservation.reservation_id)
        session.commit()
        return response, False

    def draft(self, session: Session, reservation_id: str, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        """Gera ou devolve o rascunho de contrato vinculado à reserva."""
        reservation = self.require(session, reservation_id)
        if reservation.contract_id:
            contract = ContractService.require(session, reservation.contract_id)
            return {"reservationId": reservation.reservation_id, "contract": ContractService.to_dict(contract)}, True
        ensure_reservation_transition(reservation.status, ReservationStatus.DRAFTED)
        data = {"customerId": reservation.customer_id, "serviceCode": reservation.service_code,
                "startsOn": reservation.starts_on, "endsOn": reservation.ends_on, "slaHours": reservation.sla_hours,
                "billing": {"amount": reservation.amount, "currency": reservation.currency, "cycle": reservation.billing_cycle}}
        contract, replay = self.contracts._draft(session, data, idempotency_key, correlation_id)
        reservation.contract_id = contract["contractId"]
        reservation.status = ReservationStatus.DRAFTED
        audit(session, correlation_id, "contracts", "draft_from_reservation", "success", reservation.reservation_id, contractId=contract["contractId"])
        session.commit()
        return {"reservationId": reservation.reservation_id, "contract": contract}, replay

    def cancel(self, session: Session, reservation_id: str, correlation_id: str) -> dict:
        """Cancela a reserva e o rascunho vinculado; cancelar de novo devolve o mesmo estado."""
        reservation = self.require(session, reservation_id)
        if reservation.status == ReservationStatus.CANCELLED:
            return self.to_dict(reservation)
        ensure_reservation_transition(reservation.status, ReservationStatus.CANCELLED)
        if reservation.contract_id:
            contract = ContractService.require(session, reservation.contract_id)
            ensure_contract_transition(contract.status, ContractStatus.CANCELLED)
            contract.status = ContractStatus.CANCELLED
        reservation.status = ReservationStatus.CANCELLED
        audit(session, correlation_id, "contracts", "cancel_reservation", "success", reservation.reservation_id, contractId=reservation.contract_id)
        session.commit()
        return self.to_dict(reservation)

    @staticmethod
    def require(session: Session, reservation_id: str) -> Reservation:
        """Devolve a reserva ou levanta NotFoundError."""
        return get_or_raise(session, Reservation, reservation_id, "Reserva não encontrada")

    @staticmethod
    def to_dict(item: Reservation) -> dict:
        """Serializa a reserva no formato da API."""
        return {"reservationId": item.reservation_id, "customerId": item.customer_id,
                "vehicleGroup": item.vehicle_group, "protectionCode": item.protection_code,
                "serviceCode": item.service_code, "startsOn": item.starts_on.isoformat(),
                "endsOn": item.ends_on.isoformat(), "amount": float(item.amount),
                "currency": item.currency, "billingCycle": item.billing_cycle,
                "slaHours": item.sla_hours, "status": str(item.status), "contractId": item.contract_id}
