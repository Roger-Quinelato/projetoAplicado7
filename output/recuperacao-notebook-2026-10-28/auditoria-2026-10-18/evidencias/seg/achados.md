# Achados — F-SEG (Segurança e privacidade)

Referência `44b8325`. Contagem: crítica 0; alta 0; **média 8** (SEG-01, 02, 06, 07, 11, 12, 13, 15); **baixa 8** (SEG-03, 04, 05, 08, 09, 10, 14, 16); **informativa 1** (SEG-17). Nenhum valor de credencial aparece aqui; onde há credencial, o local é citado com `<REDACTED>`.

Leitura para o coordenador: nenhum achado é alto ou crítico. O achado com maior prioridade de correção é **SEG-02** (dados pessoais e de pagamento em chamados), que tem severidade média porque o modo público usa dados sintéticos, mas prioridade alta na modelagem de ameaças (TM-005), porque visitantes podem colar dados reais em campos livres.

---

### SEG-01 — Credencial pública única concede todos os papéis, sem limite de tentativas e sem aceite formal
- Natureza: risco (decisão de desenho não registrada em ADR)
- Severidade: média
- Confiança: alta (executado)
- Esperado: `AGENTS.md:99` (autorização por papel nas rotas protegidas); `AGENTS.md:100` (segredos fora do repositório); skill `security-best-practices`, FASTAPI-AUTH-001 (negar por padrão; autorização por rota); `archcorp-seguranca` §1 (credencial compartilhada concede todos os papéis: limite conhecido) e §4 (gate antes de expor); plano de 01/10, P-15 (papéis por credencial ou leitura, com ADR).
- Observado: com `PUBLIC_DEMO=true`, qualquer requisição com `DEMO_ACCESS_TOKEN` recebe o conjunto de papéis de `demo-admin`. A matriz no modo público mostrou 51 de 51 operações protegidas acessíveis com o token único (E-SEG-08). Não há limite de tentativas: 300 tentativas erradas responderam 300 vezes 401, sem bloqueio nem 429, e o token válido funcionou depois (E-SEG-21). Não há ADR que aceite o risco (E-SEG-34). A validação do token é só de comprimento (≥24) e de prefixo (`demo-`), sem entropia (`main.py:69-70`).
- Localização: `src/archcorp/security.py:29-32` (ramo público; a linha 32 devolve `TOKEN_ROLES["demo-admin"]`); `src/archcorp/main.py:69-70` (guarda); `web/src/App.tsx:146` (a tela de acesso pede a credencial ao responsável, ou seja, o token é distribuído a visitantes).
- Reprodução: `scripts/seg_autorizacao_matriz.py publico`; `scripts/seg_sondas_http.py publico` (bloco `forca_bruta_300_tentativas`).
- Impacto: quem tem o token reprocessa falhas de integração, registra pagamentos simulados, cancela faturas, consulta trilhas e métricas e altera o estado da demonstração. Não há dado real nem acesso ao provedor; o dano direto é a integridade da demo.
- Evidências: E-SEG-04, E-SEG-08, E-SEG-21, E-SEG-34.
- Linha de base: AUD-34 (01/10, "Credencial pública com todos os papéis; sem limite de tentativas") — **aberto**.
- Correção proposta e critério de aceite: (a) credenciais por papel no modo público (ex.: um token de leitura para visitantes) ou papéis limitados por rota; (b) limite de tentativas por origem, com 429 após N falhas por janela; (c) validar entropia do token na inicialização (ex.: 32 bytes de `secrets`); (d) ADR com o risco aceito (P-15). Aceite: teste no modo público em que um token de papel não admin recebe 403 em escrita; teste em que a N-ésima tentativa errada recebe 429; ADR publicado.
- Skill ou fluxo sugerido: `archcorp-seguranca` §1 e §4; `security-best-practices` (FASTAPI-AUTH-001); ADR (`create-adr`) para o risco aceito.

### SEG-02 — Descrição de chamado aceita e devolve CPF, cartão, telefone, placa e e-mail (a checagem existe, mas não é aplicada)
- Natureza: divergência entre código e contrato, com defeito de controle
- Severidade: média
- Confiança: alta (reproduzido na API; `grep` confirma que a função não é chamada no fluxo)
- Esperado: `AGENTS.md:24` (NUNCA incluir conteúdo sensível de chamados em código, logs ou exemplos); `AGENTS.md:102` (NUNCA registrar documentos completos nem conteúdo sensível de chamados); `AGENTS.md:103` (SEMPRE minimizar os dados em APIs); contrato `src/archcorp/support/schemas.py:29` ("sem documento, cartão, telefone, placa ou e-mail"); `archcorp-seguranca` §1 lista a detecção de conteúdo sensível como controle existente.
- Observado: `POST /api/v1/support/tickets` com descrição contendo CPF, número de cartão de teste, telefone, placa e e-mail devolve 201, e `GET /api/v1/support/tickets/{id}` com papel `support` devolve a descrição igual à enviada (E-SEG-16). A função `contains_sensitive_data` só é chamada em testes (E-SEG-15). A heurística também falha com telefone entre parênteses, `(31) 99999-9999`, e não cobre nomes de pessoas.
- Localização: `src/archcorp/support/service.py:54-83` (abertura; a descrição é gravada na linha 71, sem validação); `src/archcorp/support/routes.py:218-238` (`open_ticket`) e `:139-142` (listagem com descrição); `src/archcorp/support/schemas.py:28-29` (limites só de tamanho); `src/archcorp/support/domain.py:119-130` (heurística, sem uso no fluxo).
- Reprodução: `scripts/seg_sondas_http.py local` (bloco `chamado_dado_sensivel`); `scripts/seg_checagens_inprocesso.py` (bloco `heuristica_contains_sensitive_data`).
- Impacto: dado pessoal e de pagamento de terceiros gravado em texto puro e devolvido a todo papel que lê chamados (`support`, `operations`, `admin`). Em demo pública com campos livres, visitantes podem colar dados reais (ameaça TM-005, prioridade alta na modelagem).
- Evidências: E-SEG-15, E-SEG-16, E-SEG-35.
- Linha de base: novo (o controle foi introduzido no commit `3557d20`, de 15/10, e não foi conectado ao fluxo).
- Correção proposta e critério de aceite: validar a descrição no schema (validator Pydantic) ou no serviço, antes de `session.add`, respondendo 422 sem ecoar o conteúdo; corrigir a heurística (parênteses, separadores) mantendo-a como camada; decidir se `operations` deve ver a descrição (minimização). Aceite: POST com CPF, cartão, telefone (incluindo com parênteses), placa ou e-mail → 422 sem eco, coberto por teste de API (e não só de domínio).
- Skill ou fluxo sugerido: `archcorp-seguranca` §2 (validação na fronteira; log sem payload sensível); `security-best-practices` (FASTAPI-VALID-001); ticket de correção com teste de API.

### SEG-03 — Corpo de requisição sem limite de tamanho e lido e validado antes da autenticação
- Natureza: risco (negação de serviço)
- Severidade: baixa
- Confiança: alta (corpo de 20 MB aceito e validado; ordem confirmada pelo status)
- Esperado: `security-best-practices`, FASTAPI-LIMITS-001 (limite de tamanho no edge e na aplicação); FASTAPI-AUTH-001 (autenticar antes de processar entrada); `archcorp-seguranca` §2 (limites de tamanho na fronteira).
- Observado: corpo JSON de 20 MB, com token admin, retornou 422 em 1,16 s: nenhum limite na aplicação. Sem token: JSON inválido (`{`) retorna 422 `VALIDATION_ERROR`, e não 401; JSON válido `{}` retorna 401. Ou seja, o corpo é lido e validado antes da dependência de papel, e um cliente anônimo recebe os nomes dos campos do schema (`loc`).
- Localização: `src/archcorp/main.py:80-86` (middlewares; nenhum limite de corpo); `Dockerfile:15` (uvicorn sem limite); `render.yaml` (sem configuração de limite no edge, a verificar).
- Reprodução: `scripts/seg_sondas_http.py local` (bloco `corpo_20mb`); `scripts/seg_preautenticacao.py`.
- Impacto: uma requisição anônima de 20 MB ocupa memória e CPU antes de qualquer rejeição; em paralelo, pressiona o plano gratuito do Render. O vazamento de nomes de campos é pequeno.
- Evidências: E-SEG-17.
- Linha de base: novo.
- Correção proposta e critério de aceite: limite de tamanho no edge (Render) e na aplicação (rejeitar `Content-Length` acima de N com 413 `problem+json`, sem leitura integral); autenticar antes de ler o corpo nas rotas protegidas. Aceite: POST com corpo acima de N → 413 sem leitura integral; POST sem token com JSON inválido → 401.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-LIMITS-001, FASTAPI-AUTH-001); configuração do edge (F-CFG).

### SEG-04 — Listagem de falhas de integração sem limite de itens
- Natureza: risco (consumo de recursos)
- Severidade: baixa
- Confiança: alta (inspeção do código; query sem `limit`)
- Esperado: FASTAPI-LIMITS-001 (volume máximo em listagens); as demais listas do projeto têm teto de 200 (E-SEG-36).
- Observado: `GET /api/v1/integration/failures` retorna todos os eventos `FAILED` sem teto e sem paginação.
- Localização: `src/archcorp/integration/routes.py:42-44`.
- Reprodução: inspeção. Medição com volume não feita (depende do número de falhas).
- Impacto: resposta e memória crescem com o número de eventos com falha; restrito a papéis `operations` e `admin`.
- Evidências: E-SEG-36.
- Linha de base: novo.
- Correção proposta e critério de aceite: `limit` e `offset` com teto de 200 e ordenação estável. Aceite: com 201 falhas, a resposta traz 200 itens e a segunda página traz o restante.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-LIMITS-001).

### SEG-05 — Cabeçalho `Authorization` com caractere não ASCII gera 500 no modo público
- Natureza: defeito (robustez; sem bypass)
- Severidade: baixa
- Confiança: alta (reproduzido por socket no uvicorn)
- Esperado: credencial inválida recebe 401 (FASTAPI-AUTH-001). `secrets.compare_digest` aceita apenas `str` ASCII ou `bytes`; com caractere não ASCII lança `TypeError`.
- Observado: `Authorization: Bearer` seguido de bytes UTF-8 não ASCII → HTTP 500 `application/problem+json` ("Erro interno inesperado"), e o log registra uma linha "Erro não tratado" sem traceback. Com cabeçalho ASCII errado → 401.
- Localização: `src/archcorp/security.py:30` (`compare_digest` sobre `credentials.credentials`); `src/archcorp/main.py:100-104` (exceção capturada e convertida em 500).
- Reprodução: `scripts/seg_sondas_http.py publico` (bloco `cabecalho_nao_ascii`); `logs/uvicorn_publico_18101.stderr.log` (uma linha "Erro não tratado").
- Impacto: resposta 500 para entrada de cliente, com ruído em alertas por erro; não permite acesso.
- Evidências: E-SEG-20, E-SEG-21.
- Linha de base: novo.
- Correção proposta e critério de aceite: converter a credencial para bytes UTF-8 antes de `compare_digest`, ou rejeitar não ASCII com 401. Aceite: teste com cabeçalho não ASCII → 401 `problem+json`.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-AUTH-001).

### SEG-06 — Padrão do código ativa tokens locais conhecidos quando `PUBLIC_DEMO` não está definido
- Natureza: risco (padrão inseguro; falha aberta)
- Severidade: média
- Confiança: alta (código e configuração lidos; matrizes executadas nos dois modos)
- Esperado: FASTAPI-AUTH-001 (negar por padrão); `AGENTS.md:100` (sem valores reais no repositório; exemplos sem segredos).
- Observado: `public_demo` é `False` por padrão, então `demo-admin`, `demo-support` e demais tokens valem para qualquer requisição (matriz local: `demo-admin` recebe 200 nas operações protegidas, E-SEG-07). Os tokens estão no código; o baseline de 01/10 registra que também estão documentados no README (documentação fora de escopo, não reavaliada). O `render.yaml` define `PUBLIC_DEMO: "true"` (linha 8), mas o `docker-compose.yml` não define (zero ocorrências). Uma implantação sem essa variável expõe papel admin a quem conhece os tokens publicados.
- Localização: `src/archcorp/config.py:21` (`public_demo: bool = False`); `src/archcorp/security.py:11-18` (tokens) e `:33-35` (aceitação no modo local); `render.yaml:8`; `docker-compose.yml` (ausência).
- Reprodução: `scripts/seg_autorizacao_matriz.py local`; leitura de `config.py:21`.
- Impacto: exposição total se a implantação esquecer o modo público. Hoje está mitigado pelo `render.yaml` e pelas portas `127.0.0.1` do compose.
- Evidências: E-SEG-04, E-SEG-07, E-SEG-32.
- Linha de base: novo.
- Correção proposta e critério de aceite: exigir modo explícito (ex.: `APP_MODE=local` ou `public`); sem modo explícito, a aplicação recusa os tokens fixos. Aceite: teste de inicialização sem a variável → `demo-*` recebe 401; o compose declara o modo local explicitamente.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-AUTH-001); `archcorp-seguranca` §4.

### SEG-07 — Cabeçalhos de segurança ausentes, token de administrador em `sessionStorage` sem CSP e fonte externa
- Natureza: risco
- Severidade: média (AUD-46 era baixa; sobe porque o token de administrador fica acessível a JavaScript e não há CSP)
- Confiança: alta (observado em HTTP e no código)
- Esperado: FASTAPI-HEADERS-001 (`nosniff`, anti-clickjacking, `Referrer-Policy`, `Permissions-Policy`); REACT-CSP-001 (CSP em app que renderiza conteúdo); REACT-AUTH-001 (evitar token em Web Storage); JS-CSP-001 (fonte externa com política e integridade).
- Observado: `/` e `/health/live` sem CSP, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, HSTS e `Permissions-Policy`; o cabeçalho `server: uvicorn` revela o servidor. O `App.tsx` guarda o token em `sessionStorage` e o relê a cada carga. `style.css:1` carrega Google Fonts (IP e referer vão ao Google). Não há `innerHTML`, `dangerouslySetInnerHTML` nem `eval` (XSS não identificado), o que reduz a probabilidade, mas não elimina o risco.
- Localização: `src/archcorp/main.py:80-86` (nenhum middleware de cabeçalhos); `web/src/App.tsx:31` e `:34` (token em `sessionStorage`); `web/src/style.css:1` (`@import` externo).
- Reprodução: `scripts/seg_sondas_http.py local` (blocos `cabecalhos_pagina_inicial` e `cabecalhos_health`); grep em `web/src`.
- Impacto: se surgir um XSS, o script injetado lê o token de administrador da demo; sem `frame-ancestors`, a interface pode ser embutida em outro site para induzir a digitação da credencial; a fonte externa envia IP e referer a terceiros.
- Evidências: E-SEG-09, E-SEG-33.
- Linha de base: AUD-46 (01/10) — **parcial** (o 405 foi tratado parcialmente; ver SEG-14; cabeçalhos e fonte seguem abertos).
- Correção proposta e critério de aceite: middleware com `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'` (ajustado aos assets do Vite), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` e `Permissions-Policy` mínimo; fontes servidas pelo próprio app; token mantido em memória e recarregado pelo gate. Aceite: teste dos cabeçalhos em `/` e em `/api/...`; nenhuma requisição a `fonts.googleapis.com` no build.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-HEADERS-001, REACT-HEADERS-001, REACT-CSP-001, REACT-AUTH-001).

### SEG-08 — E-mail de cliente em query string gravado no log de acesso
- Natureza: risco (dado pessoal em log)
- Severidade: baixa
- Confiança: alta (observado nos logs)
- Esperado: `AGENTS.md:102` (NUNCA registrar dados pessoais em logs); `AGENTS.md:103` (minimizar dados); RNF-03 (plano); `archcorp-seguranca` §2 (log estruturado sem payload sensível).
- Observado: `GET /api/v1/crm/customers?email=...` aparece no log de acesso do uvicorn com o e-mail codificado (`%40`), em 2 ocorrências no log local. O log JSON da aplicação não registra o e-mail (zero ocorrências).
- Localização: `src/archcorp/crm/routes.py:145-148` (e-mail como parâmetro de query); `Dockerfile:15` (uvicorn sem `--no-access-log`).
- Reprodução: `scripts/seg_sondas_http.py local` (campo `lista_por_email_status`); contagem de `%40` em `logs/uvicorn_local_18101.stdout.log`.
- Impacto: e-mails de clientes (sintéticos na demo, mas o desenho é de dado pessoal) ficam nos logs do provedor e de qualquer agregador.
- Evidências: E-SEG-19.
- Linha de base: AUD-47 (01/10) — **aberto**.
- Correção proposta e critério de aceite: `uvicorn --no-access-log` ou filtro que remova a query string; busca por e-mail por POST com corpo. Aceite: nenhuma ocorrência de `@` ou `%40` no log de acesso após a busca por e-mail.
- Skill ou fluxo sugerido: `archcorp-seguranca` §2; `AGENTS.md` (minimização).

### SEG-09 — Autorização só por papel de contexto: perfil de suporte lê cadastro completo de clientes, e o perfil de operações lê descrições de chamados
- Natureza: risco de desenho (minimização)
- Severidade: baixa
- Confiança: alta (matriz executada; código lido)
- Esperado: FASTAPI-AUTHZ-001 (autorização por objeto e por propriedade); FASTAPI-RESP-001 (resposta com campos mínimos); `AGENTS.md:103` (minimizar dados em APIs).
- Observado: `GET /api/v1/crm/customers` aceita o papel `support` e devolve `email`, `eligible`, `consentService` e `legacyId` de todos os clientes (até 200 por página, com `offset` sem teto). `GET /api/v1/support/tickets` aceita `operations` e devolve a descrição de todos os chamados. Não há vínculo entre o papel e o objeto (cliente ou contrato).
- Localização: `src/archcorp/crm/routes.py:22` (`CUSTOMER_READERS`) e `:145-157`; `src/archcorp/support/routes.py:24` (`TICKET_READERS`) e `:139-142`; `src/archcorp/support/service.py:246-251` (descrição na listagem).
- Reprodução: `logs/e09_matriz_local.tsv` (linha `GET /api/v1/crm/customers`: `demo-finance` 403, `demo-commercial` 200); `scripts/seg_autorizacao_matriz.py`.
- Impacto: um perfil de atendimento vê dados cadastrais da base inteira. Em um sistema real isso seria exposição excessiva; na demo, o mesmo token já dá admin (SEG-01).
- Evidências: E-SEG-07, E-SEG-37.
- Linha de base: novo.
- Correção proposta e critério de aceite: decidir em ADR o que cada papel vê; response shaping por papel (campos mínimos); paginação com teto (SEG-04). Aceite: teste em que `support` não recebe e-mail, ou em que a listagem fica restrita ao vínculo, conforme a decisão.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-AUTHZ-001, FASTAPI-RESP-001); `create-adr` para a decisão de visibilidade.

### SEG-10 — Documentação interativa e OpenAPI expostos também no modo público
- Natureza: risco (superfície de ataque)
- Severidade: baixa
- Confiança: alta (observado com 200 sem token)
- Esperado: FASTAPI-OPENAPI-001 (desabilitar ou proteger em produção pública, salvo necessidade explícita); `AGENTS.md:80` (APIs documentadas em OpenAPI). Como o contrato é entregável, a publicação pode ser intencional, mas não há decisão registrada.
- Observado: `/docs`, `/redoc` e `/openapi.json` respondem 200 sem token no modo público. São os defaults do FastAPI, não uma decisão documentada.
- Localização: `src/archcorp/main.py:79` (`FastAPI(...)` sem `docs_url`, `redoc_url` nem `openapi_url`).
- Reprodução: `scripts/seg_sondas_http.py publico` (bloco `docs_publicos`).
- Impacto: mapeamento completo da superfície e exemplos de erro para um atacante; facilita SEG-01, SEG-03 e SEG-05. O esquema não contém segredos.
- Evidências: E-SEG-21.
- Linha de base: novo.
- Correção proposta e critério de aceite: no modo público, `docs_url=None`, `redoc_url=None` e `openapi_url=None` (ou proteção por papel), mantendo `docs/api/openapi.yaml` como entregável. Aceite: `/docs` → 404 no modo público.
- Skill ou fluxo sugerido: `security-best-practices` (FASTAPI-OPENAPI-001).

### SEG-11 — `alembic_version` e sequências fora da proteção de RLS e de privilégios no PostgreSQL (Q-11)
- Natureza: defeito de código; impacto a confirmar em PostgreSQL
- Severidade: média
- Confiança: média (código e estrutura executados em SQLite; PostgreSQL não executado nesta frente)
- Esperado: `archcorp-seguranca` §1 (proteção do banco público) e §4 (gate: `alembic_version` e sequências sem acesso para `anon` e `authenticated`); README/ESTADO (REVOKE para `anon` e `authenticated`).
- Observado: `protect_public_demo_tables` percorre só `Base.metadata.sorted_tables` (`db.py:49`). Depois da migração, `alembic_version` existe e não está nesse laço; sequências não são tratadas. No 01/10, com privilégios padrão simulados, `anon` tinha SELECT, UPDATE e DELETE em `alembic_version`, e um DELETE como `anon` impedia o reinício (E3-13 e E3-14 do `3a3d8bd`). Não houve nova execução em PostgreSQL nesta frente.
- Localização: `src/archcorp/infrastructure/db.py:42-53` (laço em `:49`); `src/archcorp/main.py:73-75` (migração antes da proteção).
- Reprodução: `scripts/seg_estrutura_banco_sqlite.py` (executado: `relações fora do laço de proteção: ['alembic_version']`); `scripts/seg_e06_rls_postgres.py` (pronto, **não executado**).
- Impacto: quem possuir a chave `anon` do projeto Supabase pode apagar `alembic_version` e impedir o reinício do serviço até a restauração manual. A chave não está no repositório, o que reduz a probabilidade.
- Evidências: E-SEG-22, E-SEG-23, E-SEG-24.
- Linha de base: AUD-23 = Q-11 (01/10 e 16/10) — **aberto**.
- Correção proposta e critério de aceite: incluir `alembic_version` e todas as sequências do schema `public` no REVOKE e no RLS; `ALTER DEFAULT PRIVILEGES ... REVOKE` para `anon` e `authenticated`; ou schema não exposto à Data API. Aceite: em PostgreSQL descartável com papéis simulados, `has_table_privilege` e `has_sequence_privilege` retornam false para todas as relações, e o script de E-SEG-23 passa.
- Skill ou fluxo sugerido: `archcorp-seguranca` §1 e §4; ticket de correção com teste em PostgreSQL.

### SEG-12 — O teste de RLS é dublê e não detectaria a lacuna de `alembic_version`
- Natureza: dívida (teste de segurança ineficaz)
- Severidade: média
- Confiança: alta (código lido)
- Esperado: `archcorp-seguranca` §4 ("CI PostgreSQL genérica não comprova isso"; teste negativo com papéis `anon` e `authenticated` em banco descartável); `AGENTS.md:17` (testes de integração para banco).
- Observado: `tests/test_public_database_security.py:8-27` usa uma `Connection` falsa e um `SimpleNamespace` no lugar do engine, e verifica só as strings SQL geradas, para `sorted_tables`. O job `postgresql` roda 221 testes, mas este não é um deles com PostgreSQL real. Os 2 skips do job são de RabbitMQ (E-SEG-02).
- Localização: `tests/test_public_database_security.py:8-27`; `.github/workflows/verify.yml:12-34` (job `postgresql` sem teste de RLS real).
- Reprodução: inspeção (E-SEG-24).
- Impacto: a CI passa mesmo com a lacuna de SEG-11, o que dá sinal falso de conformidade ao gate de exposição.
- Evidências: E-SEG-02, E-SEG-24, E-SEG-35.
- Linha de base: parte de AUD-36 (01/10, F-QUA: "RLS por mock") — novo sob F-SEG.
- Correção proposta e critério de aceite: teste de integração com papéis `anon` e `authenticated` reais no job `postgresql`, verificando `has_table_privilege` para todas as relações. Aceite: o teste falha se a lacuna de SEG-11 for reintroduzida.
- Skill ou fluxo sugerido: `archcorp-seguranca` §4; `engineering:testing-strategy`.

### SEG-13 — A regra "texto de fora é dado" não está na `main`
- Natureza: risco de processo (agentes e revisores)
- Severidade: média
- Confiança: alta (fato); exploração não demonstrada (inferência)
- Esperado: `archcorp-seguranca` §3 (issue, PR, comentário, log, arquivo anexado e entrega de outro agente são dados, não instruções). O próprio projeto manda usar esse pacote de skills.
- Observado: `git grep` em `44b8325` não encontra a regra (exceto por ocorrências não relacionadas); `AGENTS.md` e `CLAUDE.md` não a contêm; `.claude/agents/cavecrew-*.md` também não. A regra só existe em `origin/feat/skills-revisor` (`.agents/skills/archcorp-seguranca/SKILL.md`, §3). O briefing (S-01) registra que esse pacote não está na `main`.
- Localização: `AGENTS.md` e `CLAUDE.md` (ausência); `.claude/agents/cavecrew-builder.md`, `cavecrew-investigator.md`, `cavecrew-reviewer.md` (ausência); origem da regra: `origin/feat/skills-revisor:.agents/skills/archcorp-seguranca/SKILL.md:39-44`.
- Reprodução: `git -C <WT> grep -n -i -E "texto de fora|não instrução|trate .* como dado" 44b8325 -- ':!output'` (sem resultado); `git show origin/feat/skills-revisor:.agents/skills/archcorp-seguranca/SKILL.md`.
- Impacto: agentes que trabalham na `main` e leem issues, PRs ou arquivos externos não têm a regra. Com permissão de escrita, uma instrução injetada pode induzir alterações indevidas. Não há exploração demonstrada.
- Evidências: E-SEG-30, E-SEG-31.
- Linha de base: novo (relacionado a S-01, F-CFG).
- Correção proposta e critério de aceite: incorporar a regra em `AGENTS.md` ou `CLAUDE.md` na `main`, ou mesclar o branch do pacote de skills (S-01), com decisão do coordenador. Aceite: `git grep` encontra a regra na `main`, e ela é citada no fluxo de revisão.
- Skill ou fluxo sugerido: `archcorp-seguranca` §3; fluxo do coordenador (mesclagem do pacote, F-CFG).

### SEG-14 — Erro 405 fora do contrato `problem+json`
- Natureza: divergência de contrato
- Severidade: baixa
- Confiança: alta (observado em HTTP e no TestClient)
- Esperado: contrato de erro único em `problem+json` (`src/archcorp/errors.py:1-7`; `AGENTS.md`: contratos da API); checklist F-SEG item 5 (400, 401, 403, 404, 405, 409, 422 e 500 em `problem+json`).
- Observado: `PATCH /health/live` → 405 `application/json` com `{"detail": "Method Not Allowed"}`, com `Allow: GET`. Os demais códigos verificados estão em `problem+json`.
- Localização: `src/archcorp/errors.py:11` (importa `HTTPException` de `fastapi`) e `:136` (`add_exception_handler(HTTPException, ...)`). Causa: `starlette/routing.py:277` levanta a `HTTPException` do Starlette, que não é subclasse da classe do FastAPI; o handler do projeto não a captura.
- Reprodução: `scripts/seg_sondas_http.py local` (bloco `erro_405`); `scripts/seg_checagens_inprocesso.py` (caso `405_metodo`).
- Impacto: clientes que tratam `problem+json` recebem outro formato em 405. Pequeno, mas quebra o contrato de erro.
- Evidências: E-SEG-12, E-SEG-13.
- Linha de base: AUD-46 (parte do 405) — **parcial**.
- Correção proposta e critério de aceite: registrar o handler também para `starlette.exceptions.HTTPException`. Aceite: `PATCH /health/live` → 405 `application/problem+json` com cabeçalho `Allow`.
- Skill ou fluxo sugerido: contrato de erro do projeto (`errors.py`); ticket pequeno com teste de API.

### SEG-15 — Limites de entrada incompletos no schema (tamanho e precisão)
- Natureza: defeito de validação na fronteira
- Severidade: média
- Confiança: média (validação observada em SQLite; efeito em PostgreSQL é baseline de 01/10, não reexecutado)
- Esperado: `AGENTS.md:101` (validar todas as entradas na fronteira); `archcorp-seguranca` §2 (limites de tamanho e de valor); FASTAPI-VALID-001.
- Observado: (a) `serviceCode` de chamado não tem tamanho máximo (`support/schemas.py:27`); a entrada passa pelo schema e é recusada depois pela regra de elegibilidade (422 sem `errors`). (b) `amount` de contrato e de reserva sem `max_digits` (`contracts/schemas.py:12` e `contracts/routes.py:90`): `1e20` → 201 em SQLite. Em PostgreSQL, a mesma entrada gerou 500 no 01/10 (AUD-35, da F-DAD).
- Localização: `src/archcorp/support/schemas.py:27`; `src/archcorp/contracts/schemas.py:12`; `src/archcorp/contracts/routes.py:90`.
- Reprodução: `scripts/seg_checagens_inprocesso.py` (casos `reserva_amount_1e20`, `draft_billing_amount_1e20`, `chamado_servico_5000_caracteres`).
- Impacto: erro interno (500) em PostgreSQL com entrada de cliente ou de baixo privilégio; valores fora de `Numeric(14,2)` em rotas de evento podem gerar eventos incompatíveis (AUD-01 e AUD-35, F-DAD).
- Evidências: E-SEG-14; baseline AUD-35.
- Linha de base: novo para `serviceCode` e para o schema de contratos; cross-ref AUD-35 (F-DAD).
- Correção proposta e critério de aceite: `max_length=80` em `serviceCode`; `max_digits=14` e `decimal_places=2` com limite superior em `Billing.amount` e `ReservationInput.amount`; teste 422 em SQLite e em PostgreSQL. Aceite: `1e20` → 422 nos dois bancos; `serviceCode` com mais de 80 caracteres → 422 de validação.
- Skill ou fluxo sugerido: FASTAPI-VALID-001; `archcorp-seguranca` §2; coordenar com F-DAD (AUD-35).

### SEG-16 — Dependência de desenvolvimento com advisory conhecido (pytest 8.4.1)
- Natureza: risco (apenas desenvolvimento e teste)
- Severidade: baixa
- Confiança: alta (`pip-audit` executado)
- Esperado: FASTAPI-SUPPLY-001 (responder a advisories de dependências); `archcorp-seguranca` §2 (dependência nova: pip-audit no CI).
- Observado: `requirements-dev.txt:2` fixa `pytest==8.4.1`. O `pip-audit` aponta `PYSEC-2026-1845` (corrigido em 9.0.3). A CI audita só `requirements.txt` (`verify.yml:63-64`), então o aviso não aparece no pipeline.
- Localização: `requirements-dev.txt:2`; `.github/workflows/verify.yml:63-64`.
- Reprodução: `logs/pip_audit_dev_seg.log`.
- Impacto: baixo: a dependência roda só em desenvolvimento e na CI, não no runtime. É higiene.
- Evidências: E-SEG-25, E-SEG-03.
- Linha de base: novo (AUD-25 trata do runtime e está resolvido).
- Correção proposta e critério de aceite: atualizar `pytest` para 9.0.3 ou superior, e passar `pip-audit -r requirements-dev.txt` na CI. Aceite: `pip-audit -r requirements-dev.txt` sem achados.
- Skill ou fluxo sugerido: FASTAPI-SUPPLY-001.

### SEG-17 — Credenciais sintéticas e literais de teste no repositório e no histórico (informativo)
- Natureza: informativa
- Severidade: informativa
- Confiança: alta (detect-secrets, triagem por máscara e varredura do histórico)
- Esperado: `AGENTS.md:25` e `:100` (segredos fora do Git; exemplos sem valores reais).
- Observado: nenhuma credencial real encontrada. Na árvore: 24 achados, dos quais 13 de credencial, todos sintéticos ou de desenvolvimento. No histórico: 122 commits, 20 combinações de (tipo, arquivo, commit) de credencial, todas sintéticas, de exemplo ou literal de teste. Não há padrões de AWS, GitHub, Slack, JWT, chave privada nem `sk-`. As credenciais de desenvolvimento estão em `docker-compose.yml:5,6,21` e `verify.yml:19,26,45` (valores `<REDACTED>`); exemplos em `output/auditoria/2026-10-01T2035Z/`; literais de teste em `tests/test_reliability_regressions.py:13,68,204,207`.
- Localização: as indicadas acima.
- Reprodução: `scripts/seg_segredos_arvore.py`; `scripts/seg_segredos_historico.py`; `scripts/seg_triagem_segredos.py`.
- Impacto: nenhum segredo real exposto. Senhas fracas de serviços locais devem ficar restritas a ambiente local.
- Evidências: E-SEG-28, E-SEG-29.
- Linha de base: novo (F-CFG cobre `.env.example` e `.dockerignore`).
- Correção proposta e critério de aceite: manter como estão, com a convenção de nome sintético (o valor de CI é `<REDACTED>`); ler as credenciais de desenvolvimento do ambiente no compose (F-CFG). Aceite: nenhum detector de credencial real em `git log -p --all`.
- Skill ou fluxo sugerido: `AGENTS.md`; F-CFG.
