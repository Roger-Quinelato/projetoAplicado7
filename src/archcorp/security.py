from dataclasses import dataclass
from secrets import compare_digest

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from archcorp.config import settings


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
    """Identifica o chamador pelo token Bearer; na demo pública, aceita apenas DEMO_ACCESS_TOKEN."""
    if settings.public_demo:
        if not settings.demo_access_token or credentials is None or not compare_digest(credentials.credentials, settings.demo_access_token):
            raise HTTPException(status_code=401, detail="Credencial de demonstração ausente ou inválida")
        return Principal("public-demo", TOKEN_ROLES["demo-admin"])
    if credentials is None or credentials.credentials not in TOKEN_ROLES:
        raise HTTPException(status_code=401, detail="Token ausente ou inválido")
    return Principal(credentials.credentials, TOKEN_ROLES[credentials.credentials])


def require_roles(*allowed: str):
    """Cria uma dependência que exige ao menos um dos papéis informados."""
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        """Levanta 403 se o chamador não tiver nenhum dos papéis permitidos."""
        if not principal.roles.intersection(allowed):
            raise HTTPException(status_code=403, detail="Papel sem permissão para esta operação")
        return principal
    return dependency
