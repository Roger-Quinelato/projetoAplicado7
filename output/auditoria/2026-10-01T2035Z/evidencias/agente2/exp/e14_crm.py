from harness import *
with client() as c:
    cu = show("criar cliente", c.post("/api/v1/crm/customers", headers=H, json={"name": "  Empresa  Teste ", "email": "crm1@example.com", "legacyId": "CRM-77"}))
    show("email duplicado", c.post("/api/v1/crm/customers", headers=H, json={"name": "Outra", "email": "crm1@example.com"}))
    show("legacyId duplicado", c.post("/api/v1/crm/customers", headers=H, json={"name": "Outra", "email": "crm2@example.com", "legacyId": "CRM-77"}))
    show("PATCH vazio", c.patch(f"/api/v1/crm/customers/{cu['customerId']}", headers=H, json={}))
    show("PATCH null", c.patch(f"/api/v1/crm/customers/{cu['customerId']}", headers=H, json={"name": None}))
    ct = show("contato", c.post("/api/v1/crm/contacts", headers=H, json={"customerId": cu["customerId"], "name": "Pessoa Sintética", "email": "p@example.com", "phone": "+5531999990000"}))
    show("contato telefone invalido", c.post("/api/v1/crm/contacts", headers=H, json={"customerId": cu["customerId"], "name": "Pessoa", "email": "q@example.com", "phone": "3199999"}))
    show("contato cliente inexistente", c.post("/api/v1/crm/contacts", headers=H, json={"customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "name": "Pessoa", "email": "q@example.com"}))
    op = show("oportunidade", c.post("/api/v1/crm/opportunities", headers=H, json={"customerId": cu["customerId"], "title": "Frota 2027"}))
    show("op WON", c.patch(f"/api/v1/crm/opportunities/{op['opportunityId']}", headers=H, json={"status": "WON"}))
    show("op WON->LOST", c.patch(f"/api/v1/crm/opportunities/{op['opportunityId']}", headers=H, json={"status": "LOST"}))
    for tok, method, path, body in [("demo-support", "post", "/api/v1/crm/customers", {"name": "X Y", "email": "z@example.com"}),
                                    ("demo-finance", "get", "/api/v1/crm/customers", None),
                                    ("demo-support", "get", "/api/v1/crm/customers", None),
                                    ("demo-commercial", "post", f"/api/v1/crm/customers/{cu['customerId']}/deactivate", None),
                                    ("demo-finance", "post", "/api/v1/integration/outbox/dispatch", None),
                                    ("invalido", "get", "/api/v1/crm/customers", None)]:
        r = getattr(c, method)(path, headers={"Authorization": f"Bearer {tok}"}, **({"json": body} if body else {}))
        print(f"[authz] {tok:16} {method.upper()} {path[:60]} -> {r.status_code}")
    r = c.get("/api/v1/crm/customers", headers={"Authorization": "Bearer demo-admin", "X-Correlation-ID": "nao-uuid"}); show("correlacao invalida", r)
