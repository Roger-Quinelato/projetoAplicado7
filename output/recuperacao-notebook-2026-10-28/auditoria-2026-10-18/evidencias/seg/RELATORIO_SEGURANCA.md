# Relatório de segurança e privacidade — ArchCorp (F-SEG)

Referência: `main` = `44b8325`. Data de execução: 19/10/2026 (UTC). Cópia de execução: `iso-seg` (porta 18101; SQLite na cópia). Relatório no formato da skill `security-best-practices` (seção "Report Format"), com as regras dos arquivos Python/FastAPI e JavaScript/React da skill e `archcorp-seguranca`. Achados com ID `SEG-nn`; evidências em `evidencias.md` (`E-SEG-nn`); linha de base em `linha_de_base.md`; modelo de ameaças em `MODELO_AMEACAS.md`.

## Resumo executivo

Não há achado crítico nem alto. São 17 achados: 8 médios, 8 baixos e 1 informativo. A autorização por papel está correta nas 51 operações protegidas da API, nos dois modos (matriz E-09; as outras 2 são health, públicas por desenho), e não há SQL injection, XSS, CSRF nem travessia de caminho identificados. Os riscos relevantes estão em quatro pontos. A credencial pública da demo concede papel de administrador sem limite de tentativas (SEG-01). Chamados aceitam e devolvem CPF, cartão, telefone, placa e e-mail, porque a checagem existe mas não é aplicada (SEG-02). O padrão do código ativa tokens fixos conhecidos quando o modo público não está declarado (SEG-06). A proteção do PostgreSQL não cobre `alembic_version` nem sequências, e o teste que deveria cobrir isso é um dublê (SEG-11 e SEG-12). Há também a ausência de cabeçalhos de segurança com o token de administrador em `sessionStorage` (SEG-07) e a regra de tratamento de texto externo fora da `main` (SEG-13). Dois itens não puderam ser executados: a RLS real em PostgreSQL (script pronto, sem PostgreSQL local) e o Semgrep (instalação vetada no venv compartilhado).

## Escopo, método e limitações

- **Escopo:** código e configuração de execução do serviço, pipeline, configuração de agentes; frontend em `web/`. Documentação fora de escopo, Docker proibido e PostgreSQL, RabbitMQ e Supabase reais indisponíveis.
- **Método:** leitura de código; execução do uvicorn na cópia isolada (modo local e modo público); TestClient para a matriz de autorização e os erros; detect-secrets (árvore e histórico); bandit; pip-audit e npm audit; testes de segurança existentes (52 passed).
- **Limites:** TLS, HSTS e limites de corpo do edge (Render) não verificados; resultados de PostgreSQL com confiança média; medições de latência do cliente Windows têm variação (ver E-SEG-19 e E-SEG-21).

---

## Crítica

Nenhum achado nesta severidade.

## Alta

Nenhum achado nesta severidade.

## Média

### SEG-01 — Credencial pública única concede todos os papéis, sem limite de tentativas e sem aceite formal
- **Rule ID:** FASTAPI-AUTH-001 (autenticação e autorização por rota; negar por padrão); REACT-AUTH-001 (token em armazenamento); `archcorp-seguranca` §1.
- **Severidade:** média. **Confiança:** alta (executado).
- **Localização:** `src/archcorp/security.py:29-32` (`if settings.public_demo:` ... `return Principal("public-demo", TOKEN_ROLES["demo-admin"])`); `src/archcorp/main.py:69-70` (guarda só de comprimento e prefixo); `web/src/App.tsx:146` (a tela de acesso pede a credencial ao responsável).
- **Evidência:** matriz pública com 51 de 51 operações protegidas acessíveis pelo token único (E-SEG-08); 300 tentativas erradas responderam 300×401 sem bloqueio nem 429, e o token válido funcionou depois (E-SEG-21); nenhum ADR aceita o risco (E-SEG-34).
- **Impacto:** quem tem a credencial reprocessa falhas, registra pagamentos simulados, cancela faturas e lê trilhas e métricas. Não há dado real nem acesso ao provedor; o dano direto é a integridade da demonstração.
- **Correção:** credenciais por papel no modo público (ou um papel de leitura para visitantes); limite de tentativas por origem com 429; validar entropia do token na inicialização (≥32 bytes de `secrets`); ADR com o risco aceito (P-15 do plano).
- **Mitigação:** registrar as ações por principal `public-demo` na auditoria; alerta de volume de comandos.
- **Falso positivo:** o modo público é intencional (`README` e plano). O achado é a falta de limites e de decisão formal, não a existência do modo.
- **Linha de base:** AUD-34 — aberto.
- **Skill ou fluxo:** `archcorp-seguranca` §1 e §4; ADR (`create-adr`).

### SEG-02 — Descrição de chamado aceita e devolve CPF, cartão, telefone, placa e e-mail
- **Rule ID:** FASTAPI-VALID-001 (validação por schema na fronteira); `AGENTS.md:102-103` (NUNCA registrar conteúdo sensível de chamados; SEMPRE minimizar dados em APIs); contrato de `support/schemas.py:29`.
- **Severidade:** média. **Confiança:** alta.
- **Localização:** `src/archcorp/support/service.py:54-83` (a descrição é gravada na linha 71 sem validação); `src/archcorp/support/routes.py:218-238` (`open_ticket`) e `:139-142` (listagem devolve `description`); `src/archcorp/support/schemas.py:28-29` (somente tamanho); `src/archcorp/support/domain.py:119-130` (heurística; `contains_sensitive_data` só é chamada em testes).
- **Evidência:** 201 ao enviar CPF, cartão de teste, telefone, placa e e-mail; leitura devolve a descrição igual (E-SEG-16); a heurística erra `(31) 99999-9999` (falso negativo, E-SEG-15).
- **Impacto:** dado pessoal e de pagamento de terceiros gravado em texto puro e lido por `support`, `operations` e `admin`. Em demo pública com campos livres, visitantes podem colar dados reais (prioridade alta na modelagem, TM-004).
- **Correção:** validar no schema ou no serviço, antes de `session.add`, com 422 que não ecoa o conteúdo; corrigir a heurística (parênteses, separadores) e manter o detector como camada; decidir se `operations` vê a descrição.
- **Mitigação:** aviso na interface; varredura periódica do banco por padrões sensíveis.
- **Falso positivo:** os valores usados foram sintéticos ou de teste público, e nenhum dado real foi enviado. A severidade média reflete isso; em um ambiente com dado real, a severidade sobe.
- **Linha de base:** novo (controle introduzido em 15/10, commit `3557d20`).
- **Skill ou fluxo:** `archcorp-seguranca` §2; ticket de correção com teste de API.

### SEG-06 — Padrão do código ativa tokens locais conhecidos quando `PUBLIC_DEMO` não está definido
- **Rule ID:** FASTAPI-AUTH-001 (negar por padrão); `AGENTS.md:100` (exemplos sem valores reais).
- **Severidade:** média. **Confiança:** alta.
- **Localização:** `src/archcorp/config.py:21` (`public_demo: bool = False`); `src/archcorp/security.py:11-18` (tokens `demo-*` no código) e `:33-35` (`if credentials.credentials not in TOKEN_ROLES`); `render.yaml:8` (`PUBLIC_DEMO: "true"`); `docker-compose.yml` (sem `PUBLIC_DEMO`).
- **Evidência:** no modo local, `demo-admin` recebe 200 nas operações protegidas (E-SEG-07); os tokens estão no código, e o baseline de 01/10 registra que estão no README.
- **Impacto:** uma implantação sem a variável expõe administração total a quem conhece os tokens publicados. Hoje o `render.yaml` e as portas `127.0.0.1` do compose reduzem a probabilidade.
- **Correção:** modo explícito (`APP_MODE`) com recusa por padrão: sem modo declarado, a aplicação não aceita tokens fixos; teste de inicialização.
- **Mitigação:** log de inicialização com o modo; alerta se `demo-*` autentica fora do ambiente local.
- **Falso positivo:** o padrão local é o comportamento de desenvolvimento esperado. O risco é o padrão, não o uso local.
- **Linha de base:** novo.
- **Skill ou fluxo:** `security-best-practices` (FASTAPI-AUTH-001); `archcorp-seguranca` §4.

### SEG-07 — Cabeçalhos de segurança ausentes, token de administrador em `sessionStorage` sem CSP e fonte externa
- **Rule ID:** FASTAPI-HEADERS-001; REACT-HEADERS-001; REACT-CSP-001; REACT-AUTH-001; JS-CSP-001.
- **Severidade:** média (AUD-46 era baixa; sobe pela combinação de token de administrador acessível a JavaScript com ausência de CSP). **Confiança:** alta.
- **Localização:** `src/archcorp/main.py:80-86` (nenhum middleware de cabeçalhos); `web/src/App.tsx:31` (`sessionStorage.getItem(TOKEN_KEY)`) e `:34` (`sessionStorage.setItem(TOKEN_KEY, token)`); `web/src/style.css:1` (`@import url('https://fonts.googleapis.com/...')`).
- **Evidência:** `/` e `/health/live` sem `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, `Strict-Transport-Security` e `Permissions-Policy`; `server: uvicorn` presente (E-SEG-09); nenhum sink de DOM perigoso encontrado (E-SEG-33).
- **Impacto:** se surgir um XSS, o script lê o token de administrador. Sem `frame-ancestors`, a interface pode ser embutida em outro site para induzir a digitação da credencial. A fonte externa envia IP e referer ao Google.
- **Correção:** middleware com `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'` (ajustado aos assets do Vite), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` mínimo; fontes servidas pelo app; token mantido em memória e recarregado pelo gate.
- **Mitigação:** HSTS e TLS no edge (não verificados aqui).
- **Falso positivo:** HSTS pode vir do Render; verificar no edge antes de concluir a ausência para HSTS.
- **Linha de base:** AUD-46 — parcial (o 405 ainda está fora de `problem+json`, SEG-14).
- **Skill ou fluxo:** `security-best-practices` (FASTAPI-HEADERS-001, REACT-CSP-001, REACT-AUTH-001).

### SEG-11 — `alembic_version` e sequências fora da proteção de RLS e de privilégios (Q-11)
- **Rule ID:** `archcorp-seguranca` §1 e §4 (gate de exposição: `alembic_version` e sequências sem acesso para `anon` e `authenticated`).
- **Severidade:** média. **Confiança:** média (código e estrutura executados em SQLite; PostgreSQL não executado).
- **Localização:** `src/archcorp/infrastructure/db.py:49` (`for table in Base.metadata.sorted_tables:`), no bloco `:42-53`; `src/archcorp/main.py:73-75` (migração antes da proteção).
- **Evidência:** `relações fora do laço de proteção: ['alembic_version']` (E-SEG-22, executado); no 01/10, com privilégios padrão simulados, `anon` executava `DELETE` em `alembic_version` e a aplicação não reiniciava (E3-13 e E3-14 do `3a3d8bd`).
- **Impacto:** quem possuir a chave `anon` do projeto Supabase pode impedir o reinício do serviço até a restauração manual. A chave não está no repositório, o que reduz a probabilidade.
- **Correção:** incluir `alembic_version` e todas as sequências do schema `public` no REVOKE e no RLS; `ALTER DEFAULT PRIVILEGES ... REVOKE` para `anon` e `authenticated`; ou schema não exposto à Data API.
- **Mitigação:** alerta de falha de inicialização no Render.
- **Falso positivo:** se o projeto Supabase real já tiver revogado os privilégios por outro meio, o risco cai; a verificação está no script de E-SEG-23, não executado.
- **Linha de base:** AUD-23 = Q-11 — aberto.
- **Skill ou fluxo:** `archcorp-seguranca` §1 e §4; teste em PostgreSQL descartável (`scripts/seg_e06_rls_postgres.py`, não executado).

### SEG-12 — O teste de RLS é um dublê e não detectaria a lacuna
- **Rule ID:** `archcorp-seguranca` §4 ("CI PostgreSQL genérica não comprova isso").
- **Severidade:** média. **Confiança:** alta.
- **Localização:** `tests/test_public_database_security.py:8-27` (`Connection` falsa; `SimpleNamespace` como engine; verifica só strings SQL para `sorted_tables`); `.github/workflows/verify.yml:12-34` (job `postgresql` sem teste de RLS real).
- **Evidência:** o job `postgresql` tem 221 testes passando e 2 skips, que são de RabbitMQ, não de RLS (E-SEG-02).
- **Impacto:** a CI mostra conformidade mesmo com a lacuna de SEG-11.
- **Correção:** teste de integração com papéis `anon` e `authenticated` reais no job `postgresql`, checando `has_table_privilege` e `has_sequence_privilege` em todas as relações.
- **Mitigação:** nenhuma no código; registrar a limitação no gate.
- **Falso positivo:** o teste não afirma cobrir PostgreSQL; a leitura é de cobertura, não de intenção.
- **Linha de base:** parte de AUD-36 (F-QUA) — novo sob F-SEG.
- **Skill ou fluxo:** `archcorp-seguranca` §4; `engineering:testing-strategy`.

### SEG-13 — A regra "texto de fora é dado" não está na `main`
- **Rule ID:** `archcorp-seguranca` §3 (processo).
- **Severidade:** média. **Confiança:** alta (fato); exploração não demonstrada (inferência).
- **Localização:** ausência em `AGENTS.md`, `CLAUDE.md` e `.claude/agents/cavecrew-*.md`; a regra existe em `origin/feat/skills-revisor:.agents/skills/archcorp-seguranca/SKILL.md` (§3).
- **Evidência:** `git grep` em `44b8325` sem resultado para as expressões de regra (E-SEG-30).
- **Impacto:** agentes que trabalham na `main` e leem issues, PRs ou arquivos não têm a regra. Com permissão de escrita, uma instrução injetada pode induzir alterações.
- **Correção:** incorporar a regra em `AGENTS.md` ou `CLAUDE.md` na `main`, ou mesclar o pacote de skills (S-01), com decisão do coordenador.
- **Mitigação:** revisão humana de PRs gerados por agentes.
- **Falso positivo:** o pacote de skills pode estar em uso fora da `main`; o achado é o estado da `main`.
- **Linha de base:** novo (relacionado a S-01).
- **Skill ou fluxo:** `archcorp-seguranca` §3; fluxo do coordenador.

### SEG-15 — Limites de entrada incompletos no schema (tamanho e precisão)
- **Rule ID:** FASTAPI-VALID-001; `AGENTS.md:101` (validar entradas na fronteira).
- **Severidade:** média. **Confiança:** média (SQLite observado; PostgreSQL é baseline de 01/10).
- **Localização:** `src/archcorp/support/schemas.py:27` (`serviceCode: str`, sem máximo); `src/archcorp/contracts/schemas.py:12` (`amount: Decimal = Field(gt=0, decimal_places=2)`, sem `max_digits`); `src/archcorp/contracts/routes.py:90` (mesmo padrão em `ReservationInput`).
- **Evidência:** `amount=1e20` → 201 em reserva e em rascunho no SQLite; `serviceCode` de 5.000 caracteres → 422 pela regra de elegibilidade (E-SEG-14). No PostgreSQL, o mesmo valor gerou 500 no 01/10 (AUD-35, F-DAD).
- **Impacto:** 500 com entrada anônima ou de baixo privilégio em PostgreSQL; valores fora de `Numeric(14,2)` em rotas de evento podem gerar eventos incompatíveis (AUD-01, F-DAD).
- **Correção:** `max_length=80` em `serviceCode`; `max_digits=14` e `decimal_places=2` com limite superior em `Billing.amount` e `ReservationInput.amount`; teste 422 em SQLite e PostgreSQL.
- **Mitigação:** nenhuma adicional.
- **Falso positivo:** `serviceCode` longo é recusado pela elegibilidade antes da gravação, exceto quando o adaptador de Contracts está indisponível; nesse caso, o problema vira o mesmo do PostgreSQL.
- **Linha de base:** novo para `serviceCode` e para o schema de contratos; cross-ref AUD-35 (F-DAD).
- **Skill ou fluxo:** FASTAPI-VALID-001; coordenar com F-DAD.

## Baixa

### SEG-03 — Corpo sem limite de tamanho, lido antes da autenticação
- **Rule ID:** FASTAPI-LIMITS-001; FASTAPI-AUTH-001.
- **Severidade:** baixa. **Confiança:** alta.
- **Localização:** `src/archcorp/main.py:80-86` (nenhum limite de corpo); `Dockerfile:15` (uvicorn sem limite); `render.yaml` (sem configuração de limite, a verificar no edge).
- **Evidência:** corpo de 20 MB com token admin → 422 em 1,16 s (E-SEG-17). Sem token, JSON inválido → 422 (não 401), e JSON válido → 401: o corpo é lido e validado antes da dependência de papel; o 422 expõe os nomes de campos (`loc`) a anônimos (E-SEG-17, `scripts/seg_preautenticacao.py`).
- **Impacto:** memória e CPU ocupadas por requisições anônimas antes de qualquer rejeição; pressão sobre o plano gratuito.
- **Correção:** limite de tamanho no edge e na aplicação (413 sem leitura integral); autenticar antes de ler o corpo nas rotas protegidas.
- **Mitigação:** limite de taxa no edge.
- **Falso positivo:** o Render pode aplicar limite no edge; a verificação está pendente no painel.
- **Linha de base:** novo.
- **Skill ou fluxo:** FASTAPI-LIMITS-001; configuração do edge (F-CFG).

### SEG-04 — Listagem de falhas de integração sem teto
- **Rule ID:** FASTAPI-LIMITS-001.
- **Severidade:** baixa. **Confiança:** alta (inspeção).
- **Localização:** `src/archcorp/integration/routes.py:42-44` (`session.scalars(select(OutboxEvent).where(OutboxEvent.status == "FAILED")).all()`).
- **Evidência:** as demais listas têm teto de 200 (E-SEG-36).
- **Impacto:** resposta e memória crescem com o número de eventos com falha.
- **Correção:** `limit` e `offset` com teto de 200 e ordenação estável.
- **Mitigação:** nenhuma.
- **Falso positivo:** o volume é baixo na demo; o achado é de padrão.
- **Linha de base:** novo.
- **Skill ou fluxo:** FASTAPI-LIMITS-001.

### SEG-05 — Cabeçalho `Authorization` não ASCII gera 500 no modo público
- **Rule ID:** FASTAPI-AUTH-001 (robustez da comparação).
- **Severidade:** baixa. **Confiança:** alta.
- **Localização:** `src/archcorp/security.py:30` (`compare_digest(credentials.credentials, settings.demo_access_token)`); `src/archcorp/main.py:100-104` (exceção transformada em 500).
- **Evidência:** bytes UTF-8 não ASCII no cabeçalho → 500 `problem+json` ("Erro interno inesperado") e uma linha "Erro não tratado" no log, sem traceback; ASCII errado → 401 (E-SEG-21, E-SEG-20).
- **Impacto:** sem bypass; resposta 500 e ruído de alertas.
- **Correção:** converter a credencial para bytes UTF-8 antes de `compare_digest` ou rejeitar não ASCII com 401.
- **Mitigação:** nenhuma.
- **Falso positivo:** nenhum.
- **Linha de base:** novo.
- **Skill ou fluxo:** FASTAPI-AUTH-001.

### SEG-08 — E-mail de cliente em query string no log de acesso
- **Rule ID:** `AGENTS.md:102` (dados pessoais em logs); `archcorp-seguranca` §2.
- **Severidade:** baixa. **Confiança:** alta.
- **Localização:** `src/archcorp/crm/routes.py:145-148` (`email: EmailStr | None` como query); `Dockerfile:15` (uvicorn sem `--no-access-log`).
- **Evidência:** `"GET /api/v1/crm/customers?email=...%40..."` no log de acesso, 2 ocorrências (E-SEG-19); o log JSON da aplicação não tem o e-mail (zero ocorrências).
- **Impacto:** e-mails de clientes (sintéticos na demo) ficam no log do provedor e em agregadores.
- **Correção:** `--no-access-log` ou filtro que remova a query; busca por e-mail via POST com corpo.
- **Mitigação:** retenção curta de logs.
- **Falso positivo:** dado sintético; o risco é o padrão.
- **Linha de base:** AUD-47 — aberto.
- **Skill ou fluxo:** `archcorp-seguranca` §2; AGENTS.md (minimização).

### SEG-09 — Autorização só por papel de contexto: suporte lê cadastro completo de clientes; operações lê descrições de chamados
- **Rule ID:** FASTAPI-AUTHZ-001 (autorização por objeto e propriedade); FASTAPI-RESP-001 (resposta com campos mínimos).
- **Severidade:** baixa. **Confiança:** alta.
- **Localização:** `src/archcorp/crm/routes.py:22` (`CUSTOMER_READERS = require_roles("commercial", "contracts", "support", "admin")`) e `:145-157` (`email`, `eligible`, `consentService`, `legacyId` de todos os clientes, até 200 por página); `src/archcorp/support/routes.py:24` (`TICKET_READERS` com `operations`) e `:139-142`.
- **Evidência:** matriz local: `GET /api/v1/crm/customers` → 403 para `demo-finance`, 200 para `demo-commercial` (E-SEG-07); não há vínculo entre papel e objeto no código.
- **Impacto:** perfil de atendimento vê o cadastro da base inteira. Em sistema real, exposição excessiva; na demo, o mesmo token já dá admin (SEG-01).
- **Correção:** decidir em ADR o que cada papel vê; response shaping por papel; paginação com teto (SEG-04).
- **Mitigação:** auditoria de leituras em massa por principal.
- **Falso positivo:** a visibilidade pode ser intencional para o fluxo de atendimento; o achado é a falta de decisão registrada.
- **Linha de base:** novo.
- **Skill ou fluxo:** FASTAPI-AUTHZ-001; `create-adr`.

### SEG-10 — Documentação interativa e OpenAPI públicos no modo público
- **Rule ID:** FASTAPI-OPENAPI-001.
- **Severidade:** baixa. **Confiança:** alta.
- **Localização:** `src/archcorp/main.py:79` (`FastAPI(...)` sem `docs_url`, `redoc_url` nem `openapi_url`).
- **Evidência:** `/docs`, `/redoc` e `/openapi.json` → 200 sem token no modo público (E-SEG-21).
- **Impacto:** mapeamento completo da superfície; facilita SEG-01, SEG-03 e SEG-05. Não há segredo no esquema.
- **Correção:** no modo público, `docs_url=None`, `redoc_url=None`, `openapi_url=None` (ou proteção por papel); manter `docs/api/openapi.yaml` como entregável.
- **Mitigação:** nenhuma.
- **Falso positivo:** a publicação pode ser intencional (contrato como artefato); falta a decisão formal.
- **Linha de base:** novo.
- **Skill ou fluxo:** FASTAPI-OPENAPI-001.

### SEG-14 — Erro 405 fora do contrato `problem+json`
- **Rule ID:** contrato de erro do projeto (`src/archcorp/errors.py:1-7`); checklist F-SEG item 5.
- **Severidade:** baixa. **Confiança:** alta.
- **Localização:** `src/archcorp/errors.py:11` (importa `HTTPException` de `fastapi`) e `:136` (`app.add_exception_handler(HTTPException, ...)`); causa: `starlette/routing.py:277` levanta `starlette.exceptions.HTTPException`, que não é capturada pelo handler registrado.
- **Evidência:** `PATCH /health/live` → 405 `application/json` com `{"detail": "Method Not Allowed"}` e `Allow: GET` (E-SEG-12, E-SEG-13).
- **Impacto:** cliente que trata `problem+json` recebe outro formato em 405.
- **Correção:** registrar o handler também para `starlette.exceptions.HTTPException`.
- **Mitigação:** nenhuma.
- **Falso positivo:** nenhum.
- **Linha de base:** AUD-46 (parte do 405) — parcial.
- **Skill ou fluxo:** ticket pequeno com teste de API.

### SEG-16 — Dependência de desenvolvimento com advisory (pytest 8.4.1)
- **Rule ID:** FASTAPI-SUPPLY-001.
- **Severidade:** baixa. **Confiança:** alta (pip-audit executado).
- **Localização:** `requirements-dev.txt:2` (`pytest==8.4.1`); `.github/workflows/verify.yml:63-64` (pip-audit só no runtime).
- **Evidência:** `pip-audit -r requirements-dev.txt`: `Found 2 known vulnerabilities in 1 package` — `pytest 8.4.1`, `PYSEC-2026-1845` (corrigido em 9.0.3) (E-SEG-25).
- **Impacto:** baixo; restrito a desenvolvimento e à CI.
- **Correção:** atualizar `pytest` para 9.0.3 ou superior; incluir `pip-audit -r requirements-dev.txt` na CI.
- **Mitigação:** nenhuma.
- **Falso positivo:** a vulnerabilidade pode não se aplicar ao uso do projeto; avaliar antes de descartar.
- **Linha de base:** novo (AUD-25 cobre o runtime, resolvido).
- **Skill ou fluxo:** FASTAPI-SUPPLY-001.

## Informativa

### SEG-17 — Credenciais sintéticas e literais de teste no repositório e no histórico
- **Rule ID:** `AGENTS.md:25` e `:100` (segredos fora do Git).
- **Severidade:** informativa. **Confiança:** alta.
- **Localização:** `docker-compose.yml:5,6,21`; `.github/workflows/verify.yml:19,26,45`; `tests/test_reliability_regressions.py:13,68,204,207`; exemplos em `output/auditoria/2026-10-01T2035Z/`.
- **Evidência:** nenhuma credencial real na árvore (24 achados, 13 de credencial, todos sintéticos ou de desenvolvimento) nem no histórico (122 commits; 20 combinações de tipo, arquivo e commit, todas de credencial sintética, de exemplo ou literal de teste). Sem padrões de AWS, GitHub, Slack, JWT, chave privada ou `sk-` (E-SEG-28, E-SEG-29). Valores registrados como `<REDACTED>`.
- **Impacto:** nenhum segredo real exposto.
- **Correção:** manter a convenção `synthetic-*`; ler credenciais de desenvolvimento do ambiente no compose (F-CFG).
- **Falso positivo:** os achados de alta entropia (hashes de integridade, logs de pytest) são ruído, 11 na árvore e cerca de 132 mil no histórico.
- **Linha de base:** novo.
- **Skill ou fluxo:** F-CFG (`.env.example`, `.dockerignore`).

---

## Controles verificados e conformes

- **Autenticação no modo público:** a comparação é em tempo constante (`security.py:30`), e no modo público não há outra fonte de credencial (E-SEG-04). A fragilidade está na política (SEG-01), não na comparação.
- **Autorização por rota:** 51 de 53 operações com `require_roles`; as duas sem papel são health, públicas por desenho (E-SEG-07 e E-SEG-08; zero divergências, zero 5xx).
- **Erros em `problem+json`:** 400, 401, 403, 404, 409, 422 e 500 sem traceback; 422 não ecoa o valor enviado (E-SEG-12, E-SEG-13, E-SEG-14). Exceção: 405 (SEG-14).
- **Correlação:** `X-Correlation-ID` validado como UUID e normalizado (`main.py:86-97`), o que evita injeção de cabeçalho em logs.
- **Métricas:** `/metrics` exige papel e tem cardinalidade limitada (AUD-24 resolvido; E-SEG-18).
- **Injeção de SQL:** consultas via ORM ou `text()` sem interpolação de entrada (bandit sem achado em `src/`, E-SEG-26; inspeção de `text()` e `exec_driver_sql`).
- **XSS:** nenhum `innerHTML`, `dangerouslySetInnerHTML`, `eval`, `new Function`, `document.write` ou `window.open` em `web/src` (E-SEG-33).
- **CSRF e CORS:** autenticação por cabeçalho, sem cookies; sem CORS (preflight 405) (E-SEG-09).
- **Travessia de caminho:** estáticos e fallback não vazam arquivos fora de `web/dist` (E-SEG-11).
- **Proxy e host:** nenhuma decisão de segurança usa `X-Forwarded-*`, IP do cliente ou `Host` (grep em `src/archcorp`).
- **Modo de execução:** uvicorn sem `--reload` (`Dockerfile:15`); `FastAPI` sem `debug=True` (`main.py:79`).
- **Range:** starlette 1.8.0; intervalos múltiplos respondem em menos de 1,1 s (E-SEG-10). Versão acima da correção de CVE-2025-62727.
- **Dependências de runtime:** `pip-audit` sem achados; `npm audit` com 0 vulnerabilidades (E-SEG-25), igual à CI de 17/10.
- **Expressões regulares de contrato:** `^\+[1-9]\d{7,14}$` e `^[A-Z]{3}$` são limitadas, sem risco de ReDoS. A heurística `_SENSITIVE_PATTERNS` tem custo quadrático no pior caso, mas opera sobre descrições de até 2.000 caracteres.
- **Testes de segurança existentes:** 52 testes passam (`test_security_hardening.py`, `test_public_database_security.py`, `test_t15_atendimento.py`), com as limitações de SEG-12 (E-SEG-35).

## Itens não executados e não verificáveis

- **RLS e privilégios em PostgreSQL real (E-SEG-23):** script pronto (`scripts/seg_e06_rls_postgres.py`), compilado e não executado; sem PostgreSQL local e Docker proibido.
- **Semgrep (E-SEG-27):** não instalado; instalação vetada no venv compartilhado; sem ferramenta isolada autorizada.
- **HSTS, TLS e limites de corpo do edge (Render):** não verificáveis localmente.
- **Configuração do painel do Render e do Supabase:** não vista; `DATABASE_URL` e `DEMO_ACCESS_TOKEN` são de origem externa.
- **Imagem Docker e `docker build`:** proibidos nesta frente; a CI de 17/10 é declarada como evidência (não como verificação desta execução).
- **Carga de Range com 8.000 intervalos:** não reproduzível pelo limite de cabeçalho do uvicorn (16 KB); medido com 3.000.

## Sobreposições com outras frentes

- **F-CFG:** headers e limites no edge (SEG-03, SEG-07); `.env.example` e credenciais de compose (SEG-17); Dockerfile, CI e configuração (SEG-06, SEG-08); S-01 (pacote de skills fora da `main`, SEG-13).
- **F-DAD:** AUD-35 (valores monetários no PostgreSQL, cross-ref de SEG-15); AUD-39 (idempotência não escopada por principal, citada em `E-SEG-14`).
- **F-QUA:** AUD-32 (log sem tipo de exceção; a sonda E-SEG-21 confirma uma linha "Erro não tratado" sem tipo); AUD-36 (teste de RLS por mock, SEG-12); skips do job `postgresql` são de RabbitMQ (E-SEG-02).

## Próximos passos (sem correção nesta frente)

Não houve correção de código, em conformidade com o escopo. Se o coordenador autorizar, a ordem sugerida é: SEG-06 (padrão seguro), SEG-01 e SEG-02 (decisões com o responsável, ver as três perguntas do check-in), SEG-07 (cabeçalhos e token), SEG-11 e SEG-12 (proteção do banco com teste em PostgreSQL), SEG-05 e SEG-14 (correções pequenas com teste de API). Posso iniciar as correções a partir da aprovação dessa ordem.

## Fontes de evidência

- Registros: `evidencias/seg/evidencias.md`, `achados.md`, `linha_de_base.md`, `resumo.md`, `MODELO_AMEACAS.md`.
- Logs e saídas brutas: `evidencias/seg/logs/` (inclui os logs da CI de 17/10 em `ci_job_*.log`, as sondas `sondas_*.json`, as matrizes `e09_matriz_*.tsv` e a triagem de segredos mascarada).
- Scripts: `evidencias/seg/scripts/`.
