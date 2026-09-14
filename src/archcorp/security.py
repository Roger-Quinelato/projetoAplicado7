from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)
TOKEN_ROLES = {
    "demo-admin": {"admin", "commercial", "contracts", "finance", "support", "operations"},
    "demo-commercial": {"commercial"},
    "demo-contracts": {"contracts"},
    "demo-finance": {"finance"},
    "demo-support": {"support"},
    "demo-operations": {"operations"},
}


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: set[str]


def current_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if credentials is None or credentials.credentials not in TOKEN_ROLES:
        raise HTTPException(status_code=401, detail="Token ausente ou inválido")
    return Principal(credentials.credentials, TOKEN_ROLES[credentials.credentials])


def require_roles(*allowed: str):
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if not principal.roles.intersection(allowed):
            raise HTTPException(status_code=403, detail="Papel sem permissão para esta operação")
        return principal
    return dependency
