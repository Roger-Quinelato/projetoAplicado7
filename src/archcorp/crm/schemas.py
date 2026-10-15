"""Schemas HTTP do contexto crm."""
from typing import ClassVar
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


class PartialUpdate(BaseModel):
    non_nullable: ClassVar[frozenset[str] | None] = None
    null_message: ClassVar[str] = "Campos não aceitam null"

    @model_validator(mode="after")
    def at_least_one_value(self):
        """Exige ao menos um campo e rejeita null nos campos que não aceitam remoção."""
        provided = self.model_dump(exclude_unset=True)
        if not provided:
            raise ValueError("Informe ao menos um campo para atualizar")
        checked = provided.keys() if self.non_nullable is None else self.non_nullable & provided.keys()
        if any(provided[field] is None for field in checked):
            raise ValueError(self.null_message)
        return self


class CustomerUpdate(PartialUpdate):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Cliente Frota Sintética Atualizada", "consentService": True}]})
    null_message = "Campos do cliente não aceitam null"

    name: Name | None = None
    email: EmailStr | None = None
    eligible: bool | None = None
    consentService: bool | None = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_CUSTOMER_RESPONSE]})

    customerId: UUID
    name: str
    email: EmailStr
    eligible: bool
    consentService: bool
    active: bool = True
    legacyId: str | None = None

