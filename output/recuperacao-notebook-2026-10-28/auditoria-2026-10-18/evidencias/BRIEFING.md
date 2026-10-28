# Briefing comum — Auditoria completa de 18/10/2026

Coordenador: sessão principal do Claude Code. Plano aprovado pelo responsável do repositório em 18/10/2026: `C:\Users\roger\.claude\plans\auditoria-completa-archcorp.md`.

Este briefing ajusta o plano às decisões tomadas pelo usuário em 18/10/2026:

- **Escopo sem documentação:** auditar código, configuração, contratos técnicos executáveis e testes.
- **Sem Docker:** não usar Docker; detalhes na seção 2.

## 1. Estado congelado e caminhos

| Item | Valor |
|---|---|
| Referência auditada | `main` = `44b83254b43bfcc043766d69b9fb6b8970330cbf` (18/10/2026). `origin/main` não mudou desde então |
| Pacote da auditoria (`PKG`) | `C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18\output\auditoria\2026-10-18T2018Z\` |
| Worktree (`WT`) | `C:\Users\roger\projetoAplicado7\.claude\worktrees\auditoria-2026-10-18`, branch `auditoria/2026-10-18`, mesmo SHA. Use-o para **ler** o código e para `git log`/`git show` |
| Cópia de execução da sua frente (`ISO`) | `C:\Users\roger\.claude\jobs\f5019419\tmp\iso-<frente>`, extraída por `git archive` de `44b8325`, sem `.git`. **Toda execução** (pytest, uvicorn, scripts, npm) roda aqui |
| Python da auditoria (`PY`) | `C:\Users\roger\.claude\jobs\f5019419\tmp\venv-auditoria\Scripts\python.exe`. Contém as dependências do projeto e as ferramentas: `pytest`, `coverage`, `ruff`, `bandit`, `radon`, `import-linter`, `detect-secrets`, `mypy` e `pip-audit` |
| Node | `node`/`npm` do sistema |
| Manifesto do código congelado | `PKG\evidencias\manifest_44b8325.sha256` (292 arquivos, sem `.claude/`) |
| Skills `archcorp-*` (fora da `main`) | Cópias em `C:\Users\roger\.claude\jobs\f5019419\tmp\archcorp-skills\`. Original por `git -C WT show origin/feat/skills-revisor:.agents/skills/<nome>/SKILL.md` |
| Skills pessoais | `C:\Users\roger\.agents\skills\<nome>\SKILL.md`, com as pastas `references/` ao lado |
| Skills de plugin | `C:\Users\roger\.claude\plugins\synced\941fa4e7-c333-405b-b7e9-5b93562565ce_2e532347-6470-4e8c-af6f-dc894d187d33\<engineering|design>\skills\<nome>\SKILL.md` |

Para executar o código da cópia isolada no PowerShell, defina `$env:PYTHONPATH = "<ISO>\src"` e use `PY`. O `tests/conftest.py` grava o SQLite em `./tmp/test-archcorp.db`, relativo ao diretório corrente. Por isso, rode o pytest **de dentro da sua cópia** (`Set-Location <ISO>`) e nunca de outro diretório.

## 2. Decisões do usuário que mudam o plano

1. **Fora do escopo: documentação.** `docs/` como texto, `README.md`, `CRONOGRAMA_EXECUCAO.md`, `MATRIZ_RASTREABILIDADE.md`, `ESTADO_IMPLEMENTACAO.md`, ADRs como texto, relatório, slides, `AGENTS.md` e `CLAUDE.md` como redação.
   - **Continuam no escopo** os artefatos que o código ou os testes leem como contrato: `docs/api/openapi.yaml`, `docs/events/asyncapi.yaml` e `tests/fixtures/*`.
   - Também continuam os **fatos de configuração** de agentes: o que está versionado em `.claude/`, `skills-lock.json` e as branches.
   - Ao usar um ADR como critério ("a exceção tem ADR?"), cite-o. Não avalie a redação dele.
2. **Sem Docker.** O daemon não está disponível nesta máquina, e o usuário não consegue ligá-lo agora.
   - Não iniciar o Docker Desktop, não rodar contêiner e não executar `docker build`.
   - `Dockerfile` e `docker-compose.yml` são auditados **estaticamente**.
   - O usuário declarou que a stack Docker funcionou em 17/10/2026. Registre isso como **declaração**, não como evidência.
3. **PostgreSQL e RabbitMQ reais indisponíveis localmente.** A evidência disponível é a execução da CI sobre o próprio SHA auditado. Ela não substitui experimento: afirmação que depende de concorrência, bloqueio ou limite numérico do PostgreSQL só tem confiança alta se um teste da CI a cobrir de fato. Nesse caso, cite o teste e o job.

| Evidência da CI | Valor |
|---|---|
| Run | `39063148796` (workflow `Verify`, push de `44b8325`, 17/10/2026 19:35 UTC), conclusão `success` |
| Job `postgresql` (id `117485116770`) | `221 passed, 2 skipped, 1 warning in 43.83s` |
| Job `application` (id `117485116908`) | `pip_audit`: "No known vulnerabilities found"; pytest `213 passed, 10 skipped`; `npm audit`: "found 0 vulnerabilities"; `docker build` gerou a imagem `sha256:3fafe877…` |
| Job `rabbitmq` (id `117485117016`) | `20 passed, 1 warning in 0.99s` |

Para ler um log completo: `gh run view --repo Roger-Quinelato/projetoAplicado7 --job <id> --log`.

Quando um experimento precisar de PostgreSQL ou RabbitMQ:

1. Escreva o script pronto em `PKG\evidencias\<frente>\scripts\`.
2. Rode o que for possível em SQLite, deixando o limite explícito.
3. Registre o restante como **não executado (sem PostgreSQL/RabbitMQ local)**.

## 3. Classificação

Mesma escala da auditoria de 01/10, para permitir comparação.

| Eixo | Valores |
|---|---|
| Atendimento | comprovado · parcial · não atendido · não verificado · não aplicável (com justificativa) |
| Natureza | defeito demonstrado · risco · dívida técnica · meta futura · divergência entre código e contrato |
| Severidade | crítica · alta · média · baixa · informativa |
| Confiança | alta (reproduzido ou executado agora) · média (inspeção de código ou teste existente lido) · baixa (inferência) |

Separe sempre o comportamento comprovado (executado), a inspeção e a inferência.

Achado **alto ou crítico** precisa de confiança alta. Quando a execução for impossível (por exemplo, sem PostgreSQL), registre confiança média, o motivo e o script pronto.

Saída de ferramenta (Ruff, Bandit, `pip-audit`, `detect-secrets`, Radon) é **sinal**. Ela só vira achado depois de triagem com evidência no código.

## 4. Formato dos arquivos da sua frente

Grave tudo em `PKG\evidencias\<frente>\`, onde `<frente>` é um de `cfg`, `seg`, `mod`, `dad` ou `qua`.

`evidencias.md`: uma entrada por evidência.

```
### E-<FRENTE>-<seq> — <título curto>
- Tipo: comando | inspeção de código | log da CI | consulta externa
- Fonte/local: arquivo:linha, URL ou ferramenta, com data/hora UTC
- Comando e ambiente (se houver)
- Resultado observado (trecho literal curto; segredos como <REDACTED>)
- Limitações
```

`achados.md`: uma entrada por achado, numerada `<FRENTE>-01`, `<FRENTE>-02`…

```
### <FRENTE>-<nn> — <título>
- Natureza / Severidade / Confiança
- Esperado (fonte: AGENTS.md, ADR, contrato, teste, boa prática citada)
- Observado
- Localização (arquivo:linha)
- Reprodução (passos ou comando; script em scripts/)
- Impacto
- Evidências: E-<FRENTE>-...
- Linha de base: AUD-xx / Q-xx relacionado, ou "novo"
- Correção proposta e critério de aceite
- Skill ou fluxo sugerido para a correção
```

`linha_de_base.md`: uma tabela com os itens da seção 6 que cabem à sua frente.

```
| ID | Título (01/10 ou 16/10) | Estado em 44b8325 | Evidência | Observação |
```

Use um destes estados: **resolvido** (com evidência), **parcial**, **aberto**, **obsoleto** ou **não verificável** (com motivo).

`resumo.md` (no máximo 40 linhas):

- contagem de achados por severidade;
- os cinco mais graves;
- itens do checklist não executados e por quê;
- premissas que você assumiu;
- perguntas para o usuário (no máximo 3).

Use `scripts/` e `logs/` para os scripts e as saídas brutas, já redigidas.

## 5. Regras

1. **Somente leitura** sobre o código. Escreva apenas na pasta da sua frente. Não faça commit, não altere o `.venv` do projeto e não instale nada fora de `venv-auditoria`. Se precisar de outra ferramenta, registre isso no resumo.
2. **Nada fora do repositório:** não abra nem altere issues, PRs, Jira, Trello, Notion ou Drive. Com `gh`, apenas leitura.
3. **Segredos:** nunca copie valores para os registros. Anote só o tipo e o local.
4. **Isolamento entre frentes:** execute na sua cópia `ISO`. Servidores locais usam só a porta da sua frente (seção 7). O SQLite fica em arquivo dentro da sua cópia (`DATABASE_URL=sqlite:///<ISO>/tmp/auditoria.db`).
5. **Sem perguntas ao usuário durante o trabalho.** Registre as premissas no resumo; o coordenador repassa as perguntas.
6. **Idioma:** português do Brasil. Identificadores, endpoints e campos ficam em inglês, como no código.
7. **Limite de escopo:** pare quando o checklist estiver completo. Não corrija código. Não repita o trabalho de outra frente; se um tema pertence a outra, cite-o no resumo.

## 6. Linha de base por frente

A auditoria de 01/10 está em `WT\output\auditoria\2026-10-01T2035Z\`, sobre `3a3d8bd`. Os detalhes de cada achado estão em `REGISTRO_ACHADOS.md`, os scripts de reprodução em `evidencias/agente2/exp/` e `evidencias/agente3/scripts/`, e o plano em `PLANO_ACAO.md` (P-01 a P-35).

Os achados Q da auditoria de 16/10 não têm registro próprio. O que se sabe:

| ID | Achado |
|---|---|
| Q-01 | Prazo do Workflow (corrigido no PR #42) |
| Q-02 | Ativação concorrente |
| Q-03 | Evento fora de ordem |
| Q-04 | `multipleOf 0.01` recusa 19.99 |
| Q-05 | Exemplos de contrato inválidos |
| Q-06 | Limite `Numeric(14,2)` no PostgreSQL |
| Q-07 | Workflow atribui estado na rota |
| Q-10 | Recusa do broker desfaz a tentativa |
| Q-11 | RLS sem `alembic_version` e sequências |
| Q-12 | Documento afirmando capacidade inexistente |
| Q-08, Q-09 | Não localizados |

Distribuição dos itens por frente:

| Frente | Itens |
|---|---|
| F-CFG | AUD-42, AUD-49, AUD-50 |
| F-SEG | AUD-23 (= Q-11), AUD-24, AUD-25, AUD-34, AUD-46, AUD-47 |
| F-MOD | AUD-06, AUD-22, AUD-28, AUD-29, AUD-30 (= Q-07), AUD-45 |
| F-DAD | AUD-01, AUD-04 (= Q-03), AUD-05 (Q-10), AUD-09, AUD-10 (= Q-02), AUD-11, AUD-12, AUD-20 (= Q-05), AUD-21 (= Q-04), AUD-31, AUD-33, AUD-35 (= Q-06), AUD-39, AUD-40, AUD-41, AUD-48, e verificar a correção de Q-01 |
| F-QUA | AUD-26, AUD-27, AUD-32, AUD-36 |
| Fora do escopo (documentação ou ferramentas externas) | AUD-02, 03, 07, 08, 13, 14, 15, 16, 17, 18, 19, 37, 38, 43, 44 e Q-12 |

O AUD-40 usava a `INTEGRACOES.md` como critério. Como a documentação está fora do escopo, avalie-o pela coerência entre código, OpenAPI e testes.

## 7. Frentes

Em cada frente, leia primeiro o `SKILL.md` de cada skill listada e as referências que ele mandar ler. Os sinais S-xx citados vêm da seção 11 do plano.

### F-CFG · Configuração, ambiente, cadeia de suprimentos e agentes

**Recursos:** cópia `iso-cfg`, porta `18104`.

**Skills:** `archcorp-seguranca` (§1 e §4) e `engineering:deploy-checklist` (como checklist do `render.yaml`).

**Checklist:**

1. **`src/archcorp/config.py`:**
   - valores padrão;
   - validação de faixa;
   - leitura de `.env` pelo diretório corrente;
   - objeto `settings` global e mutável.

   **Experimento:** suba a aplicação (TestClient ou uvicorn na porta da frente) com valores inválidos e registre o que acontece em cada caso, se ela falha cedo ou só em tempo de execução: `RETRY_LIMIT=0` e `-1`, `CRM_READER_MAX_ATTEMPTS=0`, `CRM_READER_TIMEOUT_SECONDS=-1`, `RABBITMQ_*` negativos, `DATABASE_URL` inválido.
2. **Guardas de inicialização em `main.py`** (cerca das linhas 67-74):
   - `PUBLIC_DEMO=true` sem token, com token curto ou com token `demo-*`;
   - `FINANCE_ALLOW_FUTURE_AS_OF=true` junto com `PUBLIC_DEMO`;
   - migração automática na inicialização.
3. **Segredos e exemplos:** `.env` no `.gitignore`, mas não no `.dockerignore` (S-06); ausência de `.env.example`; credenciais de desenvolvimento em `docker-compose.yml` e `verify.yml` (devem ser claramente sintéticas e só locais).
4. **`Dockerfile`, estático** (S-05):
   - usuário root;
   - imagens-base sem digest;
   - `pip install` sem hashes;
   - ausência de `HEALTHCHECK`;
   - `COPY web/ ./`: o código do `web/` usa `import.meta.env.VITE_*`?;
   - `CMD ["sh","-c",…]` e o encaminhamento de sinais ao uvicorn (PID 1);
   - camadas e cache.

   Evidência de que a imagem constrói: o job `application` da CI.
5. **`docker-compose.yml`, estático:**
   - portas em `127.0.0.1`;
   - healthchecks e `depends_on`;
   - o serviço `api` não tem healthcheck nem `restart`;
   - ausência de limites de recurso;
   - painel do RabbitMQ;
   - volume.
6. **`render.yaml`:** `sync: false`, `PUBLIC_DEMO`, `healthCheckPath`, migração na inicialização. Aplique os itens cabíveis do `deploy-checklist`.
7. **`.github/workflows/verify.yml`** (S-04):
   - `permissions`;
   - actions por tag;
   - gatilho de push em `sobe-artefatos-cenario-4` (a branch existe no remoto?);
   - ausência de lint, tipos, SAST, varredura de segredos e de imagem;
   - `concurrency`;
   - repetição de instalação;
   - coerência de versões com o `Dockerfile`;
   - o que cada job cobre.
8. **Dependências:**
   - só as diretas são fixadas: compare `requirements.txt` com o `pip freeze` do `venv-auditoria` e conte as transitivas soltas;
   - `pip-audit -r requirements.txt` agora;
   - `pip list --outdated` das diretas;
   - em `iso-cfg\web`: `npm audit` (usa o lockfile) e `npm outdated`.
9. **Configuração do `web/`:** flags do `tsconfig.json`, `vite.config.ts` (host e proxy de desenvolvimento), scripts e `engines` do `package.json`.
10. **Configuração de agentes e ferramentas** (fatos, não redação):
    - S-01: o pacote `archcorp-*`, `tools/perfil_skills.py` e `docs/agentes/IMPLEMENTADOR.md`/`REVISOR.md` não estão na `main`; os PRs #45–#49 foram mesclados nas branches-base empilhadas. Confirme com `git merge-base --is-ancestor`;
    - o que está versionado em `.claude/` (`agents/cavecrew-*`, `skills/caveman*`) e em `skills-lock.json`;
    - S-02: `.claude/worktrees/` fora do `.gitignore`;
    - entradas `.codex-*` do `.gitignore`;
    - os scripts de `tools/` que publicam no GitHub e no Jira: de onde vêm as credenciais, e o que gravam.
11. **Alembic:** `alembic.ini` e `infrastructure/migrations/env.py` (sem credenciais; URL tirada de `settings`).
12. **Governança de refs:**
    - branches remotas com commits fora da `main` (`git for-each-ref` + `git rev-list --count origin/main..<ref>`);
    - worktrees locais;
    - o AUD-50 tem análogo hoje?
13. **GitHub** (somente leitura, `gh api`): proteção da `main`, checagens obrigatórias, alertas de vulnerabilidade e varredura de segredos. Se a API recusar por permissão, registre "não verificável".

### F-SEG · Segurança e privacidade

**Recursos:** cópia `iso-seg`, porta `18101`.

**Skills:**

- `security-threat-model` e as referências dela (`references/prompt-template.md`). **Não pause para perguntar**: escreva as premissas e até 3 perguntas no resumo.
- `security-best-practices`: leia as referências de Python/FastAPI e de JavaScript/React em `references/`.
- `archcorp-seguranca`.
- `engineering:code-review`, na dimensão de segurança.

**Checklist:**

1. **Modelo de ameaças** em `PKG\evidencias\seg\MODELO_AMEACAS.md`, no formato da skill.
   - Entradas: as 53 operações, `/docs`, `/openapi.json`, `/metrics`, health e os estáticos de `web/dist`.
   - Fronteiras: navegador → API, API → banco, API → broker, CI e provedor.
   - Ativos.
   - Atacante: o visitante da demo pública.
2. **Autenticação:** `compare_digest`; token único com todos os papéis no modo público; ausência de limite de tentativas; token no `sessionStorage` do `web/` (impacto de um XSS).
3. **Autorização (E-09):**
   - gere a lista de rotas a partir de `app.routes`;
   - teste cada rota com: sem token, token de papel errado, token de papel certo e `demo-admin` (TestClient com SQLite);
   - grave a matriz;
   - aponte as rotas sem `require_roles` e diga se são públicas de propósito.
4. **Entrada:** limites dos schemas Pydantic (tamanho, faixa, enum), tamanho máximo do corpo, paginação máxima, regex.
5. **Erros:** `problem+json` em 400, 401, 403, 404, 405, 409, 422 e 500; ausência de rastro de pilha; o 422 não ecoa a entrada.
6. **Cabeçalhos, CORS e `Range` (E-10):** com uvicorn na porta `18101`, verifique CSP, `nosniff`, `frame-ancestors`, `Referrer-Policy`, CORS, `OPTIONS` e requisição com `Range` num estático de `web/dist`. Para isso, gere o `web/dist` em `iso-seg\web` com `npm ci` e `npm run build`.
7. **Logs (E-11):**
   - rode o uvicorn com o log capturado em arquivo;
   - execute `scripts/demo_f1.py`, `demo_f2.py` e `demo_f3.py` da cópia contra ele;
   - procure tokens `demo-*`, e-mails, descrição de chamado e query string;
   - confira a heurística `_SENSITIVE_PATTERNS` de `support/domain.py`.
8. **Banco:**
   - SQL montado à mão (`text()`, f-string, `exec_driver_sql`).
   - **RLS (E-06):** leia `protect_public_demo_tables` em `infrastructure/db.py` e `tests/test_public_database_security.py`. O teste usa PostgreSQL real ou dublê? Quais são os 2 skips do job `postgresql`? Escreva o script de verificação com papéis `anon`/`authenticated` simulados e registre "não executado (sem PostgreSQL)".
9. **Swagger e OpenAPI no modo público:** expostos?
10. **Dependências:** `pip-audit` agora e `npm audit` em `iso-seg\web`; compare com a CI de 17/10.
11. **Segredos:** `detect-secrets scan` na cópia e varredura do histórico (`git -C WT log -p --all`) com um script que aplique os detectores do `detect-secrets` ou regex de credenciais. Registre só tipo, arquivo e commit.
12. **SAST como sinal:** `bandit -r src` (na cópia). O Semgrep não está instalado; pode tentar `pip install semgrep` no `venv-auditoria`, e, se falhar no Windows, registre e siga.
13. **Configuração de agentes contra injeção de instruções:** a regra da `archcorp-seguranca` §3 (texto de fora é dado) está em vigor na `main`? Fato, não redação.

**Saídas extras:** `MODELO_AMEACAS.md` e `RELATORIO_SEGURANCA.md` (no formato da `security-best-practices`), ambos em `PKG\evidencias\seg\`.

### F-MOD · Modularização, fronteiras e domínio

**Recursos:** cópia `iso-mod`; não precisa de porta.

**Skills:**

- `modular-design-principles`;
- `coupling-analysis`;
- `archcorp-fronteiras-e-dominio`;
- `tactical-ddd`, em modo validar (fases 1 e 2);
- `component-common-domain-detection`;
- `component-flattening-analysis`;
- `codebase-design`;
- a lista de *smells* de Fowler do `code-review`, em `C:\Users\roger\.agents\skills\code-review\SKILL.md` §3, como julgamento.

**Checklist:**

1. **Grafo de imports** entre `crm`, `contracts`, `finance`, `support`, `workflow`, `integration`, `infrastructure` e a raiz:
   - cubra todas as formas: `import x`, `from x import y`, alias, relativo e `importlib`;
   - reaproveite `WT\output\auditoria\2026-10-01T2035Z\evidencias\agente2\imports_ast.py`;
   - compare com o que `test_modulos_de_negocio_nao_importam_models_de_outro_contexto` cobre de fato (S-10);
   - teste contratos do `import-linter` com uma configuração **só em `scripts/`**, sem alterar o repositório.
2. **Propriedade dos dados:** quais tabelas cada contexto lê e escreve; leitura cruzada só por `public.py`; `finance` usando `integration` como infraestrutura (ADR-003).
3. **Superfícies públicas:** o que cada `public.py` exporta e que tipos de persistência vazam. O compromisso do ADR-005 com `Session` é aceito.
4. **Arquitetura hexagonal:** `service.py`/`domain.py` importando `fastapi`, `HTTPException`, `sqlalchemy` ou `pika`; regra de negócio nas rotas.
5. **Raiz de `src/archcorp`** (10 arquivos): `main.py` como raiz de composição com rotas próprias; `schemas.py`, `api_examples.py`, `api_docs.py`, `errors.py`, `exceptions.py`, `observability.py`, `security.py`, `config.py`. Núcleo compartilhado legítimo ou lugar errado?
6. **Acoplamento em três dimensões:**
   - força e distância por aresta;
   - volatilidade por `git -C WT log --since=2026-09-01 --name-only` (pontos quentes);
   - subdomínios inferidos do código e de `docs/DDD_LOCALIZA.md`, apenas como classificação de entrada.
7. **Domínio:** modelos anêmicos; máquina de estados única por contexto (Workflow, Q-07/AUD-30); encerramento propagado (AUD-28); auditoria de pagamentos e inadimplência (AUD-29); chamado pendente com contrato inexistente (AUD-45).
8. **Regras duplicadas** entre contextos: UTC, validação monetária, replay de idempotência, auditoria, paginação, mapeamento de erros.
9. **Profundidade:** teste da deleção nas fachadas e nos adaptadores; módulos rasos.
10. **Complexidade:** `radon cc -s -a` e `radon mi` em `src/`, como sinal.
11. **`web/src`** (11 arquivos): organização por contexto, `api.ts`, componentes grandes, duplicação.

**Saída extra:** `PKG\evidencias\mod\MAPA_ACOPLAMENTO.md`, com grafo em Mermaid, tabela de arestas (força, distância, volatilidade, equilíbrio) e parecer P0/P1/P2 da `modular-design-principles`.

### F-DAD · Dados, consistência, contratos e migrações

**Recursos:** cópia `iso-dad`, porta `18102`.

**Skills:**

- `archcorp-dados-e-consistencia`;
- `archcorp-contratos-e-migracoes`;
- `ddia-transactions-consensus`;
- `ddia-encoding-evolution`;
- `migration` (só os critérios);
- `ddia-storage-retrieval`.

**Checklist e experimentos:**

1. **Outbox e inbox:**
   - comando e evento na mesma transação;
   - savepoint por consumidor;
   - `SKIP LOCKED`;
   - contagem de falhas e reprocessamento;
   - publicação no broker dentro do savepoint (Q-10: decisão consciente ou defeito?).

   **E-07** (evento venenoso, SQLite): um consumidor que sempre falha chega a `FAILED` depois de `RETRY_LIMIT` sem bloquear o lote?
2. **E-05** (broker sem RabbitMQ): aponte `RABBITMQ_URL` para uma porta local fechada (por exemplo `amqp://guest:guest@127.0.0.1:1/%2F`). Meça o tempo do despacho e os efeitos. Fila cheia e recusa: leia os testes com dublê e o job `rabbitmq` da CI.
3. **Concorrência:**
   - **E-01** (Q-02/AUD-10): inspeção do caminho de ativação (bloqueio, `UPDATE … WHERE`, `rowcount`), script pronto para PostgreSQL e o que o SQLite consegue mostrar;
   - ativar × cancelar;
   - pagamentos simultâneos;
   - resolução simultânea;
   - **E-08:** a mesma `Idempotency-Key` em paralelo (uvicorn na porta `18102` com SQLite e requisições simultâneas; registre o limite do SQLite).
4. **E-02** (Q-03/AUD-04), ordem: aplique `CustomerUpdated.v1` mais novo e depois reprocesse o antigo (SQLite). A projeção fica correta?
5. **Tempo:**
   - UTC preservado após releitura;
   - `date.today()` em horário local no encerramento de contrato;
   - prazo de `ONBOARDING` contado do despacho.
6. **Dinheiro:**
   - `float` na API v1;
   - **E-04** (Q-06/AUD-35/AUD-09): a API recusa `0.001`, `1e12`, `1e15` e frações em todos os campos monetários? Teste em SQLite; o limite do `Numeric(14,2)` no PostgreSQL vai por inspeção e pelo que a CI cobre;
   - `multipleOf` (Q-04/AUD-21).
7. **E-03** (Q-05/AUD-20, AUD-41): valide **todos** os exemplos do OpenAPI (`docs/api/openapi.yaml`) e do AsyncAPI (`docs/events/asyncapi.yaml`) contra os próprios esquemas, com `jsonschema` e `FormatChecker`. Inclua o envelope com `causationId` e os valores 0,07, 19,99 e 1234567,89. Confira também se cada exceção do baseline v1 (`tests/fixtures/api_v1_baseline.json`, `tests/test_api_v1_compatibility.py`) aponta para um ADR.
8. **E-12** (migrações, SQLite):
   - uma única cabeça (`heads`);
   - `upgrade` a partir de cada revisão intermediária, sobre dados;
   - caminhos de volta;
   - política aditiva (ADR-002) e exceção (ADR-003).

   O PostgreSQL fica coberto por `test_migration_convergence.py` no job `postgresql`; leia o teste e o log.
9. **Índices e N+1** nas listagens: clientes com filtros, faturas por contrato, chamados por estado e outbox por status.
10. **Coerência de códigos de erro** entre código, OpenAPI e testes (AUD-40).

### F-QUA · Testes, qualidade, operação e interface

**Recursos:** cópia `iso-qua`, porta `18103`. **Esta frente é a dona das suítes completas.**

**Skills:** `engineering:testing-strategy`, `design:accessibility-review` e `verify-and-stop`.

**Checklist:**

1. **Suítes** (de dentro de `iso-qua`):
   - `PY -m coverage run --branch -m pytest -q -p no:cacheprovider -rs`, seguido de `coverage report` por módulo;
   - repita uma vez o `pytest -q -p no:cacheprovider` para detectar teste instável;
   - compare com a CI (`213/10` no SQLite, `221/2` no PostgreSQL, `20` no RabbitMQ);
   - liste os motivos de cada skip.
2. **`web/`** em `iso-qua\web`: `npm ci`, `npm test` e `npm run build`.
3. **Qualidade dos testes:**
   - tautologias;
   - "concorrência" sequencial;
   - mutação de `settings` global sem restauração (S-07);
   - condições de skip;
   - exceções no baseline v1 sem ADR (teste enfraquecido);
   - asserções só de status HTTP.
4. **Lacunas:**
   - health sem teste próprio (S-09);
   - p95 medido só no health;
   - cobertura do frontend;
   - e2e fora da CI (o PR #54 está aberto);
   - testes de contrato.
5. **Observabilidade conforme o `AGENTS.md`** (seção Observabilidade):
   - campos dos logs estruturados;
   - métricas exigidas: taxa e latência por operação, erros, retentativas, tamanho e idade da fila, mensagens não processadas;
   - health separados;
   - o formatter JSON registra o tipo da exceção (AUD-32)?
6. **Sinais estáticos:** `ruff check src tests scripts tools` (regras padrão) e `mypy src --ignore-missing-imports` (contagem e exemplos).
7. **Interface** (AUD-26, AUD-27): estados de carregamento, erro e vazio; preservação do formulário em erro; chave de idempotência por intenção. Para acessibilidade, siga o checklist WCAG 2.1 AA da skill **por inspeção** do TSX e do CSS: contraste calculado a partir das cores, landmarks, `label`, `role="alert"` e teclado. Não instale navegadores.
8. **Desempenho (E-14):**
   - uvicorn na porta `18103` com SQLite;
   - carregue dados com `scripts/seed_sintetico.py`;
   - meça p50 e p95 das rotas de negócio de F1 a F3 (por exemplo 200 requisições por rota, com `httpx`);
   - registre que SQLite não equivale a PostgreSQL.
9. **CI:** o que cada job de `verify.yml` cobre e o que fica sem cobertura (por exemplo, o job `rabbitmq` roda só dois arquivos).

## 8. Depois do checklist

O coordenador pedirá a cada frente uma **revisão cruzada** dos achados de outra, nesta ordem: CFG revisa SEG, SEG revisa MOD, MOD revisa DAD, DAD revisa QUA, QUA revisa CFG.

Os critérios são os da `archcorp-revisao` (`tmp\archcorp-skills\archcorp-revisao.md`): cada alegação precisa de evidência independente e recebe um veredito (confirmada, parcial ou sem suporte). Achados altos sem reprodução são rebaixados.

A saída da revisão vai para `revisao_cruzada.md`, na pasta de **quem revisa**.
