"""Exemplos sintéticos e limites compartilhados do contrato HTTP v1."""
from typing import Annotated
from pydantic import StringConstraints


IDEMPOTENCY_KEY_MAX_LENGTH = 100


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]


EXAMPLE_CORRELATION_ID = "11111111-1111-4111-8111-111111111111"


EXAMPLE_CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


EXAMPLE_CONTRACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


EXAMPLE_CONTRACT_EVENT_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


EXAMPLE_TICKET_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


EXAMPLE_CUSTOMER_RESPONSE = {
    "customerId": EXAMPLE_CUSTOMER_ID,
    "name": "Cliente Frota Localiza Ltda.",
    "email": "gestor.frota@cliente-sintetico.example.com",
    "eligible": True,
    "consentService": True,
    "active": True,
    "legacyId": "WEB-LOCALIZA-1001",
}


EXAMPLE_CONTRACT_DRAFT_RESPONSE = {
    "contractId": EXAMPLE_CONTRACT_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "serviceCode": "RENTAL-FLEX",
    "startsOn": "2026-10-01",
    "billing": {
        "amount": 2500.00,
        "currency": "BRL",
        "cycle": "MONTHLY",
    },
    "slaHours": 8,
    "status": "DRAFT",
}


EXAMPLE_CONTRACT_ACTIVATED_RESPONSE = {
    **EXAMPLE_CONTRACT_DRAFT_RESPONSE,
    "status": "ACTIVE",
    "eventId": EXAMPLE_CONTRACT_EVENT_ID,
}


EXAMPLE_TICKET_RESPONSE = {
    "ticketId": EXAMPLE_TICKET_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "contractId": EXAMPLE_CONTRACT_ID,
    "serviceCode": "RENTAL-FLEX",
    "category": "OUTAGE",
    "status": "OPEN",
    "priority": "HIGH",
    "slaHours": 8,
    "dueAt": "2026-10-01T18:10:00Z",
    "openedAt": "2026-10-01T10:10:00Z",
    "resolvedAt": None,
    "slaStatus": "WITHIN",
}


EXAMPLE_PENDING_TICKET_RESPONSE = {
    **EXAMPLE_TICKET_RESPONSE,
    "category": "QUESTION",
    "status": "PENDING_ENTITLEMENT",
    "priority": "NORMAL",
    "slaHours": None,
    "dueAt": None,
    "slaStatus": "PENDING",
}

