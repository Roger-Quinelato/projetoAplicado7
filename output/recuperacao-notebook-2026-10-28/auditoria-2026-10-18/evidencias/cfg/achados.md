# F-CFG · Achados

Referência: `main` = `44b83254b43bfcc043766d69b9fb6b8970330cbf`. Contagem: crítica 0, alta 0, média 8 (CFG-01, 02, 04, 05, 10, 11, 12, 13), baixa 10 (CFG-03, 06, 07, 08, 09, 14, 15, 16, 17, 19), informativa 1 (CFG-18). Os achados de severidade média com confiança alta foram executados nesta auditoria. CFG-05 tem confiança média: não foi reproduzido, e o motivo é a falta de Docker, conforme a decisão do usuário.

---

### CFG-01 — `Settings` aceita valores fora de faixa e atribuições inválidas; falhas só aparecem em tempo de execução
- Natureza: defeito demonstrado
- Severidade: média
- Confiança: alta
- Esperado: configuração numérica validada na inicialização, com erro cedo para valores que desligam a proteção ou o despacho (fonte: checklist F-CFG item 1 e S-07 do plano de 18/10; `archcorp-seguranca` §2, "validar entrada na fronteira").
- Observado: `RETRY_LIMIT=0` e `-1` são aceitos, e a primeira falha já torna o evento `FAILED` (C05 e C06), contra 3 tentativas no padrão (C07). `CRM_READER_TIMEOUT_SECONDS=-1` é aceito e desliga as retentativas: uma chamada ao CRM e nenhuma espera (A05), contra 3 chamadas no padrão (A06). `CRM_READER_BASE_DELAY_SECONDS=-1` é aceito, e a primeira falha transitória sobe como `ValueError` do `time.sleep`, não como `CustomerReaderUnavailableError` (A07). `RABBITMQ_SOCKET_TIMEOUT_SECONDS`, `RABBITMQ_BLOCKED_TIMEOUT_SECONDS` e `RABBITMQ_HEARTBEAT_SECONDS` negativos são aceitos e só são recusados pelo pika no despacho, com `ValueError` (C02–C04). A atribuição `settings.retry_limit = 'abc'` é aceita e falha no uso com `TypeError` (C08). A validação existe só para tipo (A03) e para `CRM_READER_MAX_ATTEMPTS=0` (A04).
- Localização: `src/archcorp/config.py:9-12, 15-17, 20` (campos sem restrição; `Settings` sem `validate_assignment`); `src/archcorp/integration/service.py:95` (`retry_limit`), `:111-120` (parâmetros do pika); `src/archcorp/contracts/adapters.py:37-40` (`delay`) e `:42-60` (`get`, sem validação de `timeout` e de `base_delay`).
- Reprodução: `PY -I scripts/exp_config.py <ISO> <LOGS>`, casos A01–A07 e C02–C08 (`logs/exp_config.txt`).
- Impacto: uma configuração inválida passa pela subida e só aparece quando o despacho ou a leitura do CRM ocorre. Com o broker configurado, cada evento vira falha de tentativa (ligado a AUD-05). Sem sinal na inicialização, o operador não percebe o problema.
- Evidências: E-CFG-05, E-CFG-07.
- Linha de base: novo (relacionado ao S-07 do plano de 18/10).
- Correção proposta e critério de aceite: validar faixas no `Settings` (`Field(ge=1)` para tentativas e limites, `gt=0` para timeouts, `ge=0` para o que o pika aceita) e ativar `validate_assignment=True`. Aceite: `RETRY_LIMIT=0`, `RETRY_LIMIT=-1`, `CRM_READER_TIMEOUT_SECONDS<=0` e `RABBITMQ_*<0` levam a erro na importação; atribuição inválida gera `ValidationError`; um teste cobre cada caso.
- Skill ou fluxo sugerido: `tdd` (teste de faixa primeiro) e `surgical-patch`; referência `archcorp-seguranca` §2.

### CFG-02 — O modo público inicia com SQLite e a proteção de banco (RLS) é ignorada em silêncio
- Natureza: defeito demonstrado
- Severidade: média
- Confiança: alta
- Esperado: a demonstração pública só sobe com PostgreSQL, porque o gate de publicação exige RLS verificada com papéis `anon`/`authenticated` num banco equivalente. A guarda de inicialização deveria recusar o modo público fora de PostgreSQL (fonte: `archcorp-seguranca` §4; `main.py:69-75` como especificação das guardas).
- Observado: com `PUBLIC_DEMO=true`, token válido e SQLite, a aplicação sobe sem erro (B07; cenário `publico_token_valido` sobe em 8,6 s). `protect_public_demo_tables` retorna sem executar nenhuma instrução quando o dialeto não é `postgresql`. O espião registrou 0 chamadas ao banco.
- Localização: `src/archcorp/main.py:69-75` (lifespan, sem checagem de dialeto); `src/archcorp/infrastructure/db.py:42-44` (retorno silencioso).
- Reprodução: `PY -I scripts/exp_config.py` (caso B07); `PY -I scripts/exp_uvicorn.py` (cenário `publico_token_valido`).
- Impacto: uma implantação com `DATABASE_URL` apontando para SQLite sobe o modo público sem nenhuma das proteções de banco, sem erro e sem aviso. Como o banco não é exposto pela Data API nesse cenário, o risco direto é menor, mas a guarda deveria impedir a subida.
- Evidências: E-CFG-06, E-CFG-08.
- Linha de base: novo; relacionado a AUD-23 e Q-11 (F-SEG, RLS).
- Correção proposta e critério de aceite: no `lifespan`, quando `public_demo` for verdadeiro, exigir dialeto `postgresql` e levantar `RuntimeError` antes das migrações. Manter o teste de RLS com PostgreSQL real no job da CI. Aceite: `PUBLIC_DEMO=true` com SQLite falha na inicialização; o teste cobre o caso.
- Skill ou fluxo sugerido: `archcorp-seguranca` §4; `tdd`; a verificação da RLS é da F-SEG.

### CFG-03 — A guarda do token público aceita 24 caracteres sem entropia e prefixo com maiúscula
- Natureza: risco
- Severidade: baixa
- Confiança: alta
- Esperado: a guarda rejeita credencial fraca e segredo de padrão local (fonte: `main.py:69-70`, a especificação atual). Boa prática geral de segredos: credencial gerada com alta entropia (não há referência específica lida nesta frente; a F-SEG lê as referências de `security-best-practices`).
- Observado: token de 24 caracteres repetidos é aceito (B05). Token com prefixo `Demo-` (maiúscula) passa, porque a comparação do prefixo é sensível a caixa (B04). O token público concede o papel completo (`security.py:29-32`).
- Localização: `src/archcorp/main.py:69-70`; `src/archcorp/security.py:29-32`.
- Reprodução: `PY -I scripts/exp_config.py`, casos B04 e B05.
- Impacto: a guarda não é controle de força da credencial; quem configura a demo pode publicá-la com segredo fraco.
- Evidências: E-CFG-06.
- Linha de base: novo; relacionado a AUD-34 (credencial pública com todos os papéis, F-SEG).
- Correção proposta e critério de aceite: exigir no mínimo 32 caracteres aleatórios (ex.: gerado com `secrets.token_urlsafe(32)` fora do repositório) e checar o prefixo sem distinção de caixa. Aceite: B04 e B05 falham na inicialização; teste cobre.
- Skill ou fluxo sugerido: `archcorp-seguranca` §2; `tdd`.

### CFG-04 — Sem `PUBLIC_DEMO`, o token conhecido `demo-admin` concede acesso administrativo (padrão aberto)
- Natureza: risco (padrão inseguro)
- Severidade: média
- Confiança: alta
- Esperado: o padrão de configuração não deve conceder papel administrativo com credencial pública, e o modo de desenvolvimento deve ser opt-in (fonte: checklist F-CFG item 1, "valores padrão seguros?"; `archcorp-seguranca` §1, onde a credencial compartilhada com todos os papéis é um limite conhecido, não uma decisão de padrão).
- Observado: sem variáveis de demo, `demo-admin` retorna 200 em `/api/v1/demo/state` e em `/metrics` (B09; cenário `dev_padrao`). Sem credencial, esses endpoints retornam 401. `public_demo` tem padrão `False` (`config.py:21`). A imagem sobe com o CMD sem variáveis (`Dockerfile:15`), e o compose publica `127.0.0.1:8000` no mesmo padrão.
- Localização: `src/archcorp/config.py:21`; `src/archcorp/security.py:11-18` (`TOKEN_ROLES`) e `:33-35` (modo de desenvolvimento); `Dockerfile:15`.
- Reprodução: `PY -I scripts/exp_config.py` (caso B09); `PY -I scripts/exp_uvicorn.py` (cenário `dev_padrao`, campos `demo_state_demo_admin` e `metrics_demo_admin`).
- Impacto: qualquer implantação da imagem sem `PUBLIC_DEMO=true` expõe acesso administrativo a quem conhece o token do repositório, que é público (CFG-11). O `render.yaml` define `PUBLIC_DEMO=true` (linhas 8–9), então o caminho atual de implantação não é afetado.
- Evidências: E-CFG-06, E-CFG-08, E-CFG-13.
- Linha de base: relacionado a AUD-34 (F-SEG).
- Correção proposta e critério de aceite: fazer o modo de desenvolvimento exigir opt-in explícito (ex.: `APP_ENV=development`) e recusar `demo-*` sem esse opt-in, ou documentar a decisão em ADR. Aceite: sem variáveis, `demo-admin` retorna 401 e a inicialização falha ou aplica o modo público; um teste cobre.
- Skill ou fluxo sugerido: `create-adr` (decisão de padrão), `tdd`; `archcorp-seguranca` §4.

### CFG-05 — O serviço `api` do Compose publica no RabbitMQ com o usuário `guest`, que o broker recusa fora do loopback
- Natureza: defeito provável (não reproduzido)
- Severidade: média
- Confiança: média (inspeção e consulta externa; execução impossível sem Docker, decisão 2 do briefing). Se for confirmado por execução, sobe para alta, como o ajuste de AUD-05.
- Esperado: o `api` publica no broker com credencial válida a partir da rede do Compose. A documentação oficial do RabbitMQ diz que `guest` só se conecta por loopback por padrão, e que login remoto é recusado com "can only connect via localhost" (E-CFG-12).
- Observado: `docker-compose.yml:6` define `RABBITMQ_URL` do `api` com o usuário padrão (credencial redigida). O serviço `rabbitmq` (`docker-compose.yml:29-37`) não define `RABBITMQ_DEFAULT_USER` nem `RABBITMQ_DEFAULT_PASS`. O `api` conecta ao host `rabbitmq`, outro contêiner, que não é loopback. Pela documentação, a conexão deve ser recusada. Efeito previsto: `_publish_broker` levanta erro de autenticação, o despacho registra falha e o evento vai a `FAILED` após `RETRY_LIMIT` (ligado a AUD-05). O painel em `127.0.0.1:15672` usa as mesmas credenciais; pela inferência, o host aparece para o contêiner como endereço não loopback, mas isso não foi verificado.
- A CI não cobre o caminho: o job rabbitmq usa `localhost` (`verify.yml:45`), que é loopback e aceito. Por isso a CI passa.
- Localização: `docker-compose.yml:6` e `:29-37`; `.github/workflows/verify.yml:45`.
- Reprodução: `scripts/reproduzir_compose_broker_guest.py <CÓPIA_DO_REPO> <LOGS>`. Roteiro pronto, NÃO EXECUTADO nesta auditoria (exige Docker). Critério: `ACCESS_REFUSED` no passo 3 confirma; conexão bem-sucedida refuta.
- Impacto: o caminho local documentado para a demonstração (Compose) não publica no broker; a cópia de integração fica sempre em falha e em retentativa. A declaração do usuário de que a stack Docker funcionou em 17/10 é declaração, e não cobre a publicação no broker.
- Evidências: E-CFG-11, E-CFG-12, E-CFG-14, E-CFG-27.
- Linha de base: novo; relacionado a AUD-05 (F-DAD, broker).
- Correção proposta e critério de aceite: criar usuário dedicado para o Compose com `RABBITMQ_DEFAULT_USER` e `RABBITMQ_DEFAULT_PASS` (valores sintéticos, fora do repositório, ou em `.env` ignorado) e ajustar `RABBITMQ_URL`. A documentação desaconselha liberar `guest` remotamente. Aceite: o roteiro do passo 3 conecta; um teste de despacho via Compose publica a mensagem.
- Skill ou fluxo sugerido: `archcorp-seguranca` §2 (credenciais de desenvolvimento só locais); `surgical-patch`.

### CFG-06 — Compose: o serviço `api` não tem `restart`, `healthcheck` nem limites de recurso
- Natureza: dívida técnica
- Severidade: baixa
- Confiança: alta (YAML analisado por script)
- Esperado: serviços de demonstração com recuperação automática e limites (fonte: checklist F-CFG item 5).
- Observado: `api` tem apenas `build`, `depends_on`, `environment` e `ports`. `postgres` e `rabbitmq` têm `healthcheck`, mas nenhum dos três tem `restart`.
- Localização: `docker-compose.yml:2-13` (api), `:14-28` (postgres), `:29-37` (rabbitmq).
- Reprodução: `PY -I scripts/analise_estatica.py <WT> <ISO>` (seção docker-compose).
- Impacto: falha do processo ou do banco não é recuperada sozinha; sem limites, um processo descontrolado consome a máquina local.
- Evidências: E-CFG-11.
- Linha de base: novo.
- Correção proposta e critério de aceite: `restart: unless-stopped` nos três serviços; `healthcheck` HTTP no `api` (`/health/ready`); limites com `deploy.resources.limits`. Aceite: `docker compose config` mostra as chaves (validar em máquina com Docker).
- Skill ou fluxo sugerido: `surgical-patch`.

### CFG-07 — Dockerfile: contêiner como root, imagens-base sem digest, instalação sem hashes, sem `HEALTHCHECK`, `CMD` em forma de shell
- Natureza: dívida técnica
- Severidade: baixa
- Confiança: média (inspeção do arquivo e do log da CI; build local não feito)
- Esperado: imagem com usuário não-root, imagens fixadas por digest, instalação com hashes e `HEALTHCHECK` (fonte: AUD-49 de 01/10 e checklist F-CFG item 4; `archcorp-seguranca` §1, "Contêiner roda como root").
- Observado: `Dockerfile:1` e `:8` usam `FROM` sem digest (o log da CI mostra os digests resolvidos pelo BuildKit, mas o arquivo não os fixa). Não há `USER` (roda como root). `:11` usa `pip install --no-cache-dir -r requirements.txt` sem `--require-hashes`. Não há `HEALTHCHECK` (o Render usa `healthCheckPath`) nem `EXPOSE`. `:15` usa `CMD ["sh", "-c", "uvicorn ... ${PORT:-8000}"]`. `:5` (`COPY web/ ./`, estágio frontend) copia o diretório inteiro; o `web/` só usa `import.meta.env.DEV` (`web/src/App.tsx:135`), sem variáveis `VITE_*` embutidas no bundle, então a cópia não vaza configuração. Camadas: `requirements.txt` vem antes de `src` (bom para cache), e `npm ci` vem depois dos manifestos; `COPY web/ ./` antes do build invalida o cache a cada alteração do `web/`, inclusive testes (ganho pequeno).
- Não verificado (sem Docker): PID 1 e propagação de sinais pelo `sh -c` (confiança baixa); usuário efetivo do contêiner em execução; tamanho e camadas da imagem. A evidência de que a imagem constrói vem só da CI (job application, `archcorp-demo`).
- Localização: `Dockerfile:1, 5, 8, 11, 15`.
- Reprodução: `PY -I scripts/analise_estatica.py <WT> <ISO>` (seção Dockerfile); `logs/ci_job_application.txt` (build).
- Impacto: um processo que escapar do contêiner tem root dentro dele; builds não são reproduzíveis; restaurar uma versão depende de tag.
- Evidências: E-CFG-10, E-CFG-15, E-CFG-21.
- Linha de base: AUD-49 (parte de imagem, severidade Baixa mantida). Parcial: versões de Node 24 e Python 3.12 estão alinhadas entre Dockerfile, CI e venv.
- Correção proposta e critério de aceite: criar usuário e `USER` não-root; fixar digests; `pip install --require-hashes` com lock (CFG-08); `HEALTHCHECK`; `exec` no comando (ou `tini`) para que o uvicorn receba os sinais. Aceite: `docker run --rm <imagem> id -u` diferente de 0; digest visível no `FROM`; teste em máquina com Docker.
- Skill ou fluxo sugerido: `surgical-patch`; `archcorp-seguranca` §2 (dependência nova).

### CFG-08 — Dependências: 22 transitivas de execução sem pin, 44 de desenvolvimento fora da auditoria da CI, 9 de 10 diretas atrás da última versão
- Natureza: dívida técnica
- Severidade: baixa
- Confiança: alta (pip-audit, npm audit e fechamento calculado com metadados instalados)
- Esperado: dependências de execução fixadas com hashes e auditadas; dependência nova justificada, fixada e aprovada em pip-audit e npm audit (fonte: `archcorp-seguranca` §2; AUD-49 de 01/10: "builds reproduzíveis").
- Observado: os 10 pins diretos estão instalados nas versões exigidas. O fechamento de execução tem 22 transitivos sem pin nem hash neste Windows. `requirements-dev.txt` traz 44 pacotes fora da imagem, e o pip-audit da CI só audita `requirements.txt` (`verify.yml:64`). pip-audit de hoje: sem vulnerabilidades conhecidas. npm audit: 0 vulnerabilidades em 71 dependências. Atrás da última versão do índice (19/10): fastapi, starlette, uvicorn, sqlalchemy, psycopg, pika, pydantic-settings e email-validator. pydantic 2.13.5 é pin intencional (`requirements.txt:6-7`). Front: react 19.3.0 (wanted 19.3.1), vite 7.3.7 (latest 8.3.4), typescript 5.9.3 (latest 7.0.2).
- Localização: `requirements.txt:1-12`; `requirements-dev.txt:1-7`; `.github/workflows/verify.yml:63-64`.
- Reprodução: `PY -I scripts/analise_dependencias.py <WT>`; `pip-audit -r requirements.txt` e `pip list --outdated` (`logs/pip_audit_requirements.json`, `logs/pip_outdated.json`); `npm audit` e `npm outdated` (`logs/npm_audit.json`, `logs/npm_outdated.json`).
- Impacto: builds não são reproduzíveis a partir do repositório (as transitivas mudam); atualização de segurança depende de nova resolução; dependências de desenvolvimento não são auditadas.
- Evidências: E-CFG-16, E-CFG-17, E-CFG-18, E-CFG-19.
- Linha de base: AUD-49 (parte de transitivas, Baixa mantida). AUD-25 (starlette): o pip-audit atual não encontra vulnerabilidade para 1.8.0; o resultado é cedido à F-SEG para reconciliar.
- Correção proposta e critério de aceite: gerar lock com hashes (`pip-compile --generate-hashes` ou `uv lock`) e instalar com `--require-hashes`; rodar pip-audit também em `requirements-dev.txt`; política de atualização das diretas, com regra para pydantic. Aceite: `pip install --require-hashes -r <lock>` passa; a CI audita o lock de desenvolvimento.
- Skill ou fluxo sugerido: `archcorp-seguranca` §2; `engineering:tech-debt`.

### CFG-09 — CI: actions referenciadas por tag, sem `concurrency` nem `timeout-minutes`, gatilho em branch antiga sem execuções recentes
- Natureza: risco
- Severidade: baixa
- Confiança: alta (YAML analisado por script; API do GitHub consultada)
- Esperado: actions fixadas por SHA, jobs com limite de tempo, concorrência controlada e gatilhos só nas branches vigentes (fonte: checklist F-CFG item 7; plano §5, "actions fixadas por tag, não por SHA").
- Observado: 7 de 7 referências de actions por tag (`checkout@v7`, `setup-python@v7`, `setup-node@v7`). GitHub: `sha_pinning_required: false`. Sem `concurrency`, sem `timeout-minutes` em nenhum dos três jobs, sem cache de pip, `pip install` repetido em três jobs. O gatilho `push` inclui `sobe-artefatos-cenario-4` (`verify.yml:5`); a branch existe no remoto (`f482d1d`), mas nenhuma das 30 execuções mais recentes é dela. Permissões de topo corretas (`contents: read`; `GITHUB_TOKEN` padrão `read`).
- Localização: `.github/workflows/verify.yml:5` (gatilho); `:28-29, 47-48, 57-58, 67` (actions); `:12-83` (jobs sem `timeout-minutes` nem `concurrency`).
- Reprodução: `PY -I scripts/analise_estatica.py`; `logs/github_leitura.txt` (execuções).
- Impacto: job travado consome minutos até o limite padrão do GitHub; execuções paralelas da mesma branch se acumulam; uma tag reapontada altera a CI sem mudança no repositório.
- Evidências: E-CFG-14, E-CFG-23.
- Linha de base: novo (S-04 do plano).
- Correção proposta e critério de aceite: fixar actions por SHA (com comentário da tag); `timeout-minutes`; `concurrency: group: ${{ github.workflow }}-${{ github.ref }}`; cache do pip; retirar `sobe-artefatos-cenario-4` do gatilho, salvo decisão em contrário. Aceite: workflow válido; push duplicado cancela a execução anterior.
- Skill ou fluxo sugerido: `surgical-patch`.

### CFG-10 — CI sem lint, checagem de tipos, SAST, varredura de segredos e de imagem
- Natureza: risco
- Severidade: média
- Confiança: alta (busca no arquivo executada; API do GitHub consultada)
- Esperado: pipeline com lint, tipos, SAST, varredura de segredos e de imagem (fonte: plano §5, F-CFG item 7; `security-best-practices`).
- Observado: a CI roda pytest (três jobs), pip-audit de `requirements.txt`, npm audit, npm test, npm run build e docker build. Não há ruff, mypy, bandit, semgrep, detect-secrets, gitleaks, trivy nem CodeQL (todos ausentes do arquivo). Mitigação parcial: secret scanning e push protection habilitados no GitHub, com 0 alertas abertos. O `docker build` passa sem varredura da imagem gerada.
- Localização: `.github/workflows/verify.yml:1-83` (ausência).
- Reprodução: `PY -I scripts/analise_estatica.py` (lista de ferramentas, todas `False`); `logs/github_leitura.txt`.
- Impacto: defeitos de tipo, segredos no código e vulnerabilidades da imagem só seriam detectados por inspeção ou pelo usuário final.
- Evidências: E-CFG-14, E-CFG-23.
- Linha de base: relacionado a AUD-36 (qualidade não verificada, F-QUA); este achado trata dos gates de segurança.
- Correção proposta e critério de aceite: adicionar job `quality` com ruff e mypy (ou o que o projeto adotar), detect-secrets ou gitleaks, `bandit -r src` e trivy da imagem gerada; começar em modo informativo, com baseline documentado. Aceite: jobs verdes ou baseline registrado.
- Skill ou fluxo sugerido: `engineering:testing-strategy`; `security-best-practices`; `surgical-patch`.

### CFG-11 — Repositório público, `main` sem proteção, commit direto sem PR e alertas de vulnerabilidade desabilitados
- Natureza: risco
- Severidade: média
- Confiança: alta (API do GitHub consultada com GET)
- Esperado: branch principal protegida, com PR obrigatório e checagens requeridas, e alertas de vulnerabilidade habilitados (fonte: checklist F-CFG item 13; boa prática de governança do GitHub).
- Observado: `visibility: public`. `main` com `protected: false`; `branches/main/protection` retorna 404 "Branch not protected"; `rulesets` vazio. `vulnerability-alerts` 404 ("disabled"); Dependabot alerts desabilitados; security updates do Dependabot desabilitados; code scanning sem análise. Commit `eaad233` ("Atualizar o nome AGENT.md", 16/10) está em `main` sem número de PR e sem ser merge de PR. `delete_branch_on_merge: false`. Deployments: 0.
- Localização: GitHub, repositório `Roger-Quinelato/projetoAplicado7` (E-CFG-23, E-CFG-24).
- Reprodução: `PY -I scripts/github_leitura.py <LOGS>` (somente GET); `PY -I scripts/governanca_detalhes.py <WT> <LOGS>`.
- Impacto: alterações diretas na `main` sem revisão nem CI obrigatória; vulnerabilidades de dependências não notificadas; repositório público torna exposto qualquer segredo commitado (ver F-SEG).
- Evidências: E-CFG-23, E-CFG-24.
- Linha de base: novo (AUD-44 e AUD-50 tratam de governança de branch, mas AUD-44 está fora do escopo).
- Correção proposta e critério de aceite: ruleset na `main` (PR obrigatório, checagens `verify` requeridas, sem force push); habilitar Dependabot alerts e security updates; `delete_branch_on_merge: true`. Aceite: `GET branches/main/protection` retorna `required_status_checks`; push direto é rejeitado.
- Skill ou fluxo sugerido: `git-guardrails-claude-code`; fluxo de PR do coordenador.

### CFG-12 — Governança de refs: branch local sem remota com 20 commits (análogo de AUD-50) e 30 branches remotas com commits fora da `main`
- Natureza: risco
- Severidade: média
- Confiança: alta (git executado)
- Esperado: trabalho em andamento deve estar publicado ou descartado com registro (fonte: AUD-50 de 01/10 e a regra do cronograma citada no registro, "código local isolado não comprova").
- Observado: `feat/fluxo-coordenado` (6901e02; worktree `q01-workflow-dueat`) tem 20 commits fora da `main`, sem upstream, e nenhuma remota contém o SHA. Remotas: 30 branches com commits fora da `main` por ancestralidade (superestimado por causa de squash-merge). Destas, 4 não têm PR associado: `ccr-1c5dff06-gdznnu`, `chore/ai-memory`, `feat/t12-financeiro` e `feat/t15-atendimento`. Worktrees: 8 (um travado por sessão). `delete_branch_on_merge: false`.
- Localização: refs locais e remotas (`git for-each-ref`); `git worktree list`.
- Reprodução: `PY -I scripts/refs_governanca.py` (coleta anterior, `logs/refs_governanca.txt`); `PY -I scripts/governanca_detalhes.py` (`logs/governanca_detalhes.txt`).
- Impacto: perda de trabalho se o worktree ou a branch local for removido; incerteza sobre o que está na `main`.
- Evidências: E-CFG-03, E-CFG-24.
- Linha de base: AUD-50 (análogo novo; a ref declarada de 01/10 continua ausente, ver linha de base).
- Correção proposta e critério de aceite: decidir por ref: publicar (branch e PR) ou registrar o descarte; ligar `delete_branch_on_merge`; limpar refs já mescladas. Aceite: `git ls-remote` contém cada ref de trabalho ou há registro de descarte.
- Skill ou fluxo sugerido: fluxo de PR do coordenador; `git-guardrails-claude-code`.

### CFG-13 — O pacote de agentes `archcorp-*`, `tools/perfil_skills.py` e `docs/agentes/` só existe em branches empilhadas (S-01)
- Natureza: divergência entre código e configuração
- Severidade: média
- Confiança: alta (merge-base e ls-tree executados)
- Esperado: a configuração de agentes que o plano trata como vigente deve estar na branch principal, ou ter uma decisão registrada (fonte: plano §5 F-CFG item 10 e S-01; decisão D2 pendente).
- Observado: os PRs #45–#49 não são ancestrais de `origin/main` (exit 1 nos cinco). A `main` não contém `.agents/`, `tools/perfil_skills.py`, `docs/agentes/IMPLEMENTADOR.md` nem `REVISOR.md`, nem `.claude/skills/archcorp-*`. `origin/feat/skills-revisor` (45694c7) tem 10 `SKILL.md` `archcorp-*` em `.agents/skills`, 4 em `.claude/skills`, o script e os dois documentos. A validação do pacote (`tools/perfil_skills.py --check`) está só na CI da branch `feat/perfil-mcp`.
- Localização: `origin/feat/skills-revisor:.agents/skills/archcorp-*`; `origin/feat/perfil-mcp:.github/workflows/verify.yml` (etapa "Validate project skill pack").
- Reprodução: `PY -I scripts/verificar_s01_s02.py <WT> <LOGS>` (`logs/s01_s02_verificacoes.txt`).
- Impacto: o fluxo de agentes descrito pelo plano não funciona a partir da `main`, e a validação do pacote não roda na branch principal.
- Evidências: E-CFG-04, E-CFG-03.
- Linha de base: novo (S-01 do plano; decisão D2).
- Correção proposta e critério de aceite: decidir D2, promovendo a pilha #45–#49 por PR único ou registrando o abandono em ADR. Depois, validar com `tools/perfil_skills.py --check` na CI da `main`. Aceite: `git merge-base --is-ancestor <tip> origin/main` verdadeiro, ou decisão registrada.
- Skill ou fluxo sugerido: fluxo do coordenador (D2); `create-adr` se houver abandono.

### CFG-14 — `.claude/worktrees/` fora do `.gitignore` (S-02)
- Natureza: risco
- Severidade: baixa
- Confiança: alta (`git check-ignore` executado)
- Esperado: worktrees aninhados e estado local do agente fora do versionamento (fonte: plano §5 F-CFG item 10, S-02).
- Observado: `git check-ignore --no-index .claude/worktrees/x/y.txt` retorna exit 1 (não ignorado). `.claude/settings.local.json` só é ignorado pela configuração global do usuário (`**/.claude/settings.local.json`), não pelo repositório. O `.gitignore` do repositório não tem entradas para `.claude/`.
- Localização: `.gitignore` (ausência de `.claude/worktrees/` e de `.claude/`).
- Reprodução: `PY -I scripts/verificar_s01_s02.py` (seção S-02); `PY -I scripts/analise_estatica.py` (seção `.gitignore`).
- Impacto: um `git add -A` em outra máquina, sem a configuração global, versiona worktrees inteiros e estado local.
- Evidências: E-CFG-04, E-CFG-20.
- Linha de base: novo (S-02).
- Correção proposta e critério de aceite: acrescentar `.claude/worktrees/` e `.claude/settings.local.json` ao `.gitignore`. Aceite: `git check-ignore -v .claude/worktrees/x` retorna a regra.
- Skill ou fluxo sugerido: `git-guardrails-claude-code`.

### CFG-15 — `.dockerignore` não exclui `.env`; não há `.env.example`; credenciais de desenvolvimento no Compose
- Natureza: risco
- Severidade: baixa
- Confiança: alta (arquivos inspecionados por script; `git ls-files` executado)
- Esperado: `.dockerignore` exclui `.env`; há arquivo de exemplo sem valores reais para o desenvolvedor; credenciais de desenvolvimento são claramente sintéticas e só locais (fonte: checklist F-CFG item 3; plano §5 F-CFG item 3, que cita AGENTS.md como critério, sem avaliar a redação).
- Observado: `.gitignore` exclui `.env` (linha 151) e `.envrc` (linha 152). `.dockerignore` (12 entradas) não exclui `.env`. `git ls-files` não tem nenhum `.env*` nem `*.example`. O Compose define credencial de banco de desenvolvimento cuja senha é igual ao nome de usuário, e usuário padrão do RabbitMQ (valores `<REDACTED>`). O workflow usa credencial marcada como sintética (`synthetic-ci-only`, só na CI). O estágio frontend copia `web/` inteiro; um `web/.env` local iria para esse estágio intermediário, não para a imagem final.
- Localização: `.dockerignore:1-12`; `.gitignore:151-152`; `docker-compose.yml:4-6, 18-21, 29-31` (valores não registrados); `.github/workflows/verify.yml:18-26, 45`.
- Reprodução: `PY -I scripts/analise_estatica.py` (seções `.dockerignore`, `.gitignore` e docker-compose); `git ls-files`.
- Impacto: um `.env` local com segredos entra no contexto de build e no estágio intermediário; não há modelo de configuração para o desenvolvedor.
- Evidências: E-CFG-10, E-CFG-11, E-CFG-14, E-CFG-20, E-CFG-28.
- Linha de base: novo.
- Correção proposta e critério de aceite: incluir `.env` (e `*.env`) em `.dockerignore`; criar `.env.example` com valores sintéticos e citá-lo na documentação de execução; manter as credenciais do Compose marcadas como sintéticas. Aceite: `.dockerignore` contém `.env`; `.env.example` existe sem valores reais.
- Skill ou fluxo sugerido: `archcorp-seguranca` §2 (segredos e exemplos).

### CFG-16 — Logs rotulam horário local como UTC (`Z`)
- Natureza: defeito demonstrado
- Severidade: baixa
- Confiança: alta (executado neste host)
- Esperado: timestamps em UTC com sufixo `Z`, como a própria string do formato indica (fonte: critério citado em AUD-41 de 01/10, "ISO 8601 UTC").
- Observado: `JsonFormatter` grava `...%SZ`, mas `formatTime` usa `time.localtime` por padrão. Neste host (UTC-3), o log mostra `08:03:01Z` quando a hora UTC era 11:03. `localtime` e `gmtime` diferem em 3 horas (`logs/fuso_host.txt`).
- Localização: `src/archcorp/observability.py:19`.
- Reprodução: `logs/fuso_host.txt`; linhas de stderr em `logs/exp_config.txt`.
- Impacto: correlação de eventos entre máquinas fica errada (o Render roda em UTC e não sofre o problema); diagnóstico com horário deslocado.
- Evidências: E-CFG-09, E-CFG-05.
- Linha de base: relacionado a AUD-41 (F-DAD) e à observabilidade (F-QUA).
- Correção proposta e critério de aceite: `formatter.converter = time.gmtime` ou formatar com `time.gmtime(record.created)`. Aceite: com `TZ=America/Sao_Paulo`, o timestamp do log é igual à hora UTC do sistema.
- Skill ou fluxo sugerido: `surgical-patch`; `tdd`.

### CFG-17 — Configuração do `web/`: sem `engines`, testes fora do `tsconfig`, proxy de desenvolvimento fixo
- Natureza: dívida técnica
- Severidade: baixa
- Confiança: alta (arquivos lidos por script; `npm ci` executado)
- Esperado: versões de runtime declaradas em `engines` e todos os arquivos de teste verificados pelo compilador (fonte: checklist F-CFG item 9).
- Observado: `web/package.json` não tem `engines` nem `packageManager`. O script `test` (`node --test "tests/**/*.test.ts"`) depende de Node com suporte a TypeScript; foi executado só com Node 24.21.0 e não foi verificado em outras versões. `web/tsconfig.json:19` tem `include: ["src"]`, então `web/tests/api.test.ts` fica fora de `tsc -b`. Flags: `strict`, `noUnusedLocals` e `noUnusedParameters` estão corretas; `noFallthroughCasesInSwitch` e `noUncheckedIndexedAccess` não estão definidas. `vite.config.ts:4` faz proxy de `/api` e `/health` fixo em `127.0.0.1:8000`, sem `server.host`. O `npm ci` avisa que o npm 11 não executou o `postinstall` do esbuild.
- Localização: `web/package.json:6-10`; `web/tsconfig.json:19`; `web/vite.config.ts:4`.
- Reprodução: `PY -I scripts/analise_estatica.py` (seção web/); `logs/npm_ci.txt`.
- Impacto: testes do frontend sem checagem de tipos; ambiente com Node diferente pode falhar nos testes sem aviso.
- Evidências: E-CFG-21, E-CFG-18.
- Linha de base: novo.
- Correção proposta e critério de aceite: `engines` (`node >=24`); incluir os testes num `tsconfig` próprio; porta do proxy por variável de ambiente. Aceite: `tsc -p <tsconfig de testes> --noEmit` passa; `engines` presente.
- Skill ou fluxo sugerido: `surgical-patch`.

### CFG-18 — Prontidão de publicação (T20): sem staging, monitoramento nem gatilhos de rollback versionados
- Natureza: meta futura
- Severidade: informativa
- Confiança: alta (YAML analisado; API do GitHub consultada)
- Esperado: checklist de publicação aplicável ao `render.yaml` (fonte: `engineering:deploy-checklist`, aplicado em E-CFG-13) e o gate de `archcorp-seguranca` §4.
- Observado: `render.yaml` define o serviço, `healthCheckPath: /health/ready`, `PUBLIC_DEMO` fixo e `DATABASE_URL`/`DEMO_ACCESS_TOKEN` com `sync: false` (bom). Não há staging, monitoramento ou alerta, nem gatilhos de rollback em artefato versionado. Não declara região, disco, instâncias nem `autoDeploy`. Não há URL pública no repositório (grep sem `onrender.com` em código ou configuração) e no GitHub há 0 deployments e a issue #23 está aberta, sem comentários.
- Localização: `render.yaml:1-13`.
- Reprodução: E-CFG-13; `logs/github_leitura.txt`.
- Impacto: a publicação não tem roteiro de verificação nem de reversão; T20 não está cumprido.
- Evidências: E-CFG-13, E-CFG-23, E-CFG-24.
- Linha de base: AUD-42.
- Correção proposta e critério de aceite: roteiro de smoke versionado (`scripts/demo_f1..f3.py` contra `ARCHCORP_BASE_URL`), gatilhos de rollback e alerta simples em `/health/ready`; depois, o gate de `archcorp-seguranca` §4. Aceite: evidências listadas na linha de base de AUD-42.
- Skill ou fluxo sugerido: `engineering:deploy-checklist` (depois de publicar).

### CFG-19 — Scripts de publicação em GitHub e Jira: credenciais externas, transição com id fixo e links para branch antiga
- Natureza: dívida técnica
- Severidade: baixa
- Confiança: média (inspeção; nenhuma execução, porque escrevem em serviços externos, fora do escopo)
- Esperado: scripts que escrevem em serviços externos leem credenciais de fora do repositório, registram só identificadores e não fixam estado de workflow (fonte: checklist F-CFG item 10, "de onde vêm as credenciais, e o que gravam").
- Observado: `tools/publish_github_issues.py` usa a CLI `gh` (credencial do `gh`, fora do repositório), cria issues, labels e milestones, faz PATCH de issues e grava `docs/GITHUB_ISSUES_SYNC.json` (ignorado). Os corpos das issues apontam para a branch `sobe-artefatos-cenario-4` e para o PR #2 (linhas 87–88). `tools/publish_jira_backlog.py` usa a CLI `twg` (credencial fora do repositório), tem site fixo (linha 16), cria workitems, links e transições, com id de transição fixo `"11"` (linha 87), e grava ledgers ignorados. Nenhum literal de segredo nos scripts. Ambos guardam reexecução: o de Jira recusa rodar sem o ledger.
- Localização: `tools/publish_github_issues.py:20, 26-44, 87-88, 95-99, 151`; `tools/publish_jira_backlog.py:16, 49-56, 62, 74-78, 86-87, 92`.
- Reprodução: leitura estática (E-CFG-25); nenhuma execução.
- Impacto: links das issues apontam para branch antiga; a transição depende de um id que pode mudar no Jira; reexecução sem ledger é recusada, o que limita o risco de duplicação.
- Evidências: E-CFG-25.
- Linha de base: novo (relacionado a AUD-43 e AUD-44, fora do escopo).
- Correção proposta e critério de aceite: parametrizar branch, PR e id de transição por configuração validada. Aceite: nenhum literal de branch ou transição nos scripts.
- Skill ou fluxo sugerido: `surgical-patch`.
