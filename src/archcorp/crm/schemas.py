"""Schemas HTTP do contexto crm."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from archcorp.api_examples import Name, EXAMPLE_CUSTOMER_RESPONSE


class CustomerCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Cliente Frota Localiza Ltda.",
                    "email": "gestor.frota@cliente-sintetico.example.com",
                    "eligible": True,
                    "consentService": True,
                    "legacyId": "WEB-LOCALIZA-1001",
                }
            ]
        }
    )

    name: Name
    email: EmailStr
    eligible: bool = True
    consentService: bool = True
    legacyId: str | None = Field(default=None, min_length=1, max_length=100)


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Cliente Frota Sintética Atualizada", "consentService": True}]})

    name: Name | None = None
    email: EmailStr | None = None
    eligible: bool | None = None
    consentService: bool | None = None

    @model_validator(mode="after")
    def at_least_one_value(self):
        provided = self.model_dump(exclude_unset=True)
        if not provided:
            raise ValueError("Informe ao menos um campo para atualizar")
        if any(value is None for value in provided.values()):
            raise ValueError("Campos do cliente não aceitam null")
        return self


class CustomerResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_CUSTOMER_RESPONSE]})

    customerId: UUID
    name: str
    email: EmailStr
    eligible: bool
    consentService: bool
    active: bool = True
    legacyId: str | None = None

