# Superfície de segurança — retrato de 16/10/2026

Escrito em 16/10/2026 sobre o SHA `3557d20` (`main`). É retrato, não regra: reconfira cada linha no
SHA atual (arquivos citados) antes de usá-la como fato numa avaliação ou documento.

| Área | Implementação naquele SHA | Limite conhecido naquele SHA |
|---|---|---|
| Autenticação | Tokens locais `demo-*` (`security.py`); com `public_demo`, só `demo_access_token` via `compare_digest` | Credencial compartilhada concede todos os papéis; sem OIDC |
| Inicialização pública | `main.py` recusa subir com `public_demo` e token ausente, curto (< 24) ou `demo-*`; recusa `finance_allow_future_as_of` em modo público | — |
| Autorização | `require_roles(...)` por rota | Matriz de papéis testada por contexto |
| Banco público | `protect_public_demo_tables` (`infrastructure/db.py`): RLS e revogação de `anon`/`authenticated` nas tabelas dos modelos | Não cobre `alembic_version` nem sequências; testado só com dublê (achado Q-11) |
| Dados de chamado | Detecção de conteúdo sensível na descrição (`support/domain.py`, `_SENSITIVE_PATTERNS`) | Heurística; não substitui minimização |
| Erros e métricas | `422` sanitizado; `/metrics` restrito a `operations`/`admin` com cardinalidade limitada | Erro genérico do middleware sem tipo no log |
| Execução | Compose publica portas só em `127.0.0.1` | Contêiner roda como root; transitivas Python sem lock |
