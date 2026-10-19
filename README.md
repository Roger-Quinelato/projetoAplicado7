# ArchCorp · Projeto Aplicado 7 · Cenário 4

Protótipo acadêmico de integração entre os cinco sistemas do Cenário 4 da Localiza: CRM, reservas e contratos, financeiro e faturamento, atendimento e assistência 24h, e gestão de processos operacionais. O protótipo usa somente dados sintéticos e **não acessa sistemas reais da Localiza**.

A solução é uma SOA pragmática entregue como monólito modular ([ADR-001](docs/adr/ADR-001-integracao-empresa-de-servicos.md)). Os módulos conversam por REST e por eventos gravados numa outbox transacional. O despachante entrega os eventos aos consumidores internos e publica uma cópia no RabbitMQ local.

**Diagrama de contratos:** [ver imagem da arquitetura de Reservas e Contratos](docs/diagramas/arquitetura-contratos.svg) · [abrir documentação do fluxo](docs/ARQUITETURA_CONTRATOS.md).

> **Estado do protótipo:** este README descreve como usar o repositório. Para saber o que está verificado, o que é meta e o que depende de validação externa, consulte [`docs/ESTADO_IMPLEMENTACAO.md`](docs/ESTADO_IMPLEMENTACAO.md).

## Regras para agentes

Antes de trabalhar no repositório, leia [`AGENTS.md`](AGENTS.md). As regras **SEMPRE** são obrigatórias e as regras **NUNCA** são proibições permanentes. Agentes Claude Code também leem [`CLAUDE.md`](CLAUDE.md), que encaminha ao guia completo. A proposta de skills por papel (implementador e revisor) está em [`docs/agentes/LEVANTAMENTO_SKILLS.md`](docs/agentes/LEVANTAMENTO_SKILLS.md) e ainda aguarda aceite.

Nunca descreva o protótipo como conectado a sistemas reais da Localiza.

## O que o protótipo faz

Cada contexto é dono dos próprios dados e expõe uma interface pública. Nenhum módulo acessa tabelas de outro.

| Contexto | Responsabilidade no protótipo |
|---|---|
| `crm` | Clientes, contatos, consentimentos e oportunidades |
| `contracts` | Reservas, rascunhos, ativação e encerramento de contratos, com SLA |
| `finance` | Faturas inicial e final, pagamento simulado e inadimplência por vencimento |
| `support` | Chamados com prioridade, prazo de SLA, atribuição, resolução e reconciliação |
| `workflow` | Processos e tarefas operacionais criados por eventos |
| `integration` | Outbox e inbox, correlação, auditoria, falhas, reprocessamento e IDs legados |

Os três fluxos integrados do plano são:

- **F1. Cliente → reserva → contrato:** o contrato nasce da reserva com o cliente oficial do CRM, sem recadastro. A leitura do CRM é resiliente: repete apenas falhas transitórias, com atraso exponencial e jitter, e devolve `503` sem gravar nada quando o CRM não responde ([ADR-006](docs/adr/ADR-006-leitura-resiliente-do-crm.md), proposto).
- **F2. Ativação → faturamento e preparação de retirada:** `ContractActivated.v1` gera uma única fatura `INITIAL` e um processo `ONBOARDING`, mesmo com despacho repetido.
- **F3. Chamado → processo de resolução → resolução:** o chamado herda o SLA do contrato. O processo `TICKET_RESOLUTION` copia o `dueAt` publicado pelo atendimento, então atraso ou reentrega do despacho não estendem o prazo.

## Execução rápida

Você precisa do Docker Desktop com Docker Compose.

1. Suba a stack local:

   ```powershell
   docker compose up --build
   ```

2. Abra a interface em `http://localhost:8000` e entre com o token `demo-admin`.
3. Opcional: carregue dados sintéticos com `python scripts/seed_sintetico.py --base-url http://localhost:8000 --token demo-admin` (com `PYTHONPATH=src`).

O Compose publica todas as portas somente em `127.0.0.1`:

| Serviço | Endereço | Acesso |
|---|---|---|
| Interface e API | `http://localhost:8000` | Tokens `demo-*` |
| Swagger | `http://localhost:8000/docs` | — |
| Console do RabbitMQ | `http://localhost:15672` | `guest` / `guest` |
| PostgreSQL (pgAdmin, psql) | `localhost:5432` | Banco e usuário `archcorp`; a senha de desenvolvimento está em `POSTGRES_PASSWORD`, no `docker-compose.yml` |

A aplicação executa as migrações Alembic (`upgrade head`) ao iniciar, e os dados ficam no volume `archcorp-data`. Para parar a stack sem perder dados, use `docker compose down`. Não use `down -v`, que apaga o volume.

Para acesso pela rede, use `PUBLIC_DEMO=true` com `DEMO_ACCESS_TOKEN`. Nunca abra as portas com os tokens locais ativos.

## Demonstração dos fluxos

Com a stack no ar, rode a demonstração completa:

```powershell
./scripts/demo.ps1
```

O script cria um cliente, ativa um contrato, abre um chamado, despacha a outbox e mostra o estado consolidado. Rode-o numa base limpa: o e-mail e o ID legado do cliente são fixos, então uma segunda execução no mesmo banco falha no cadastro com `409`.

Para checagens verificáveis de cada fluxo, use os roteiros em Python. Cada execução gera dados novos e pode ser repetida no mesmo banco.

```powershell
$env:PYTHONPATH = "src"
python scripts/demo_f1.py   # F1: 20 checagens, incluindo 401, 403, 409, 422 e correlationId
python scripts/demo_f2.py   # F2: faturamento e onboarding sem duplicidade
python scripts/demo_f3.py   # F3: SLA, resolução e trilha por correlação
```

Os roteiros aceitam `--base-url`, `--token` e `--forbidden-token`, ou as variáveis `ARCHCORP_BASE_URL` e `ARCHCORP_TOKEN`. Eles saem com `0` quando tudo passa, `1` quando alguma checagem falha e `2` quando a API está inacessível. No modo público, use `--forbidden-token ""` para pular a checagem de `403`.

O passo a passo para a banca, incluindo a indisponibilidade simulada de Contracts com `CONTRACT_ADAPTER_AVAILABLE=false`, está em [`docs/ROTEIRO_DEMONSTRACAO.md`](docs/ROTEIRO_DEMONSTRACAO.md).

## Autenticação da demonstração

**Não há OIDC/OAuth implementado.** No ambiente local, as rotas protegidas aceitam tokens fixos:

| Token | Papéis |
|---|---|
| `demo-admin` | Todos |
| `demo-commercial` | `commercial` |
| `demo-contracts` | `contracts` |
| `demo-finance` | `finance` |
| `demo-support` | `support` |
| `demo-operations` | `operations` |

Com `PUBLIC_DEMO=true`, a API rejeita os tokens `demo-*` e aceita apenas `DEMO_ACCESS_TOKEN`: um segredo aleatório com pelo menos 24 caracteres, configurado fora do repositório. Essa credencial é compartilhada e concede todos os papéis, adequada apenas ao protótipo acadêmico.

A interface guarda o token no `sessionStorage` da aba e o apaga ao fechar a aba ou ao usar **Sair**. Nunca use credenciais pessoais ou dados reais.

## Configuração

A aplicação lê a configuração de variáveis de ambiente:

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./archcorp.db` | Banco da aplicação; o Compose aponta para o PostgreSQL |
| `RABBITMQ_URL` | vazio | Habilita a cópia dos eventos no RabbitMQ |
| `PUBLIC_DEMO` | `false` | Ativa o modo público |
| `DEMO_ACCESS_TOKEN` | vazio | Credencial do modo público; obrigatória com `PUBLIC_DEMO=true` |
| `CRM_READER_TIMEOUT_SECONDS` | `2.0` | Prazo total da leitura resiliente do CRM |
| `CRM_READER_MAX_ATTEMPTS` | `3` | Tentativas da leitura do CRM |
| `CRM_READER_BASE_DELAY_SECONDS` | `0.1` | Atraso base da retentativa exponencial |
| `CONTRACT_ADAPTER_AVAILABLE` | `true` | Use `false` para simular a indisponibilidade de Contracts no atendimento |
| `RETRY_LIMIT` | `3` | Tentativas de despacho antes de o evento ir para falhas |
| `FINANCE_ALLOW_FUTURE_AS_OF` | `false` | Permite data futura na verificação de vencimento; recusada com `PUBLIC_DEMO=true` |
| `PORT` | `8000` | Porta do contêiner da imagem Docker |

## Desenvolvimento e testes

Siga estes passos para preparar o ambiente Python:

1. Crie o ambiente e instale as dependências:

   ```powershell
   python -m venv .venv
   ./.venv/Scripts/pip install -r requirements-dev.txt
   ```

2. Rode a suíte com SQLite:

   ```powershell
   $env:PYTHONPATH = "src"
   ./.venv/Scripts/pytest
   ```

Sem serviços reais, a suíte ignora os testes de PostgreSQL e RabbitMQ. Para incluí-los, defina:

- `TEST_DATABASE_URL`: uma URL `postgresql+psycopg://` para **um banco exclusivo de testes**. O `conftest.py` apaga e recria todas as tabelas desse banco. Nunca aponte para o banco `archcorp` da demonstração.
- `TEST_RABBITMQ_URL`: uma URL `amqp://` de um broker de testes. O teste apaga a fila `archcorp.events.all`.

Para a interface, entre em `web/` e use `npm ci`, `npm run dev` (Vite só em `localhost`, com a API na porta 8000), `npm test` (testes de `web/tests` com `node:test`) e `npm run build` (gera `web/dist`, que o FastAPI serve na raiz). Os roteiros de navegador (`npm run test:e2e`) e o perfil Playwright MCP estão em [`docs/TESTES_E2E.md`](docs/TESTES_E2E.md).

Outras tarefas de desenvolvimento:

- **Contrato REST:** depois de alterar rotas ou schemas, rode `python tools/export_openapi.py`. Com `--check`, o comando só compara e falha se o OpenAPI estiver desatualizado.
- **Migrações:** o esquema é versionado com Alembic, e as migrações são aditivas ([ADR-002](docs/adr/ADR-002-migracoes-aditivas.md)).
- **Dados sintéticos:** `scripts/seed_sintetico.py` é idempotente e segue as [regras de dados sintéticos](docs/DADOS_SINTETICOS.md).
- **Desempenho:** `scripts/performance_smoke.py` mede a latência de `/health/ready` num banco SQLite temporário.
- **Erros:** todas as respostas de erro seguem `application/problem+json` (RFC 9457), com `code` e `correlationId`. Os erros `422` não ecoam a entrada recebida. Consulte o [contrato de erro](docs/INTEGRACOES.md#contrato-de-erro).

### Integração contínua

O workflow `Verify` roda em cada PR:

- **`application`:** `pip-audit`, `pytest`, `npm audit --audit-level=moderate`, `npm test`, `npm run build` e o build da imagem Docker.
- **`e2e`:** build do frontend, Chromium e roteiros Playwright contra a API real com SQLite novo; a varredura axe roda como informativa.
- **`postgresql`:** a suíte completa contra PostgreSQL 16, incluindo concorrência e convergência de migrações.
- **`rabbitmq`:** a publicação confirmada contra um RabbitMQ real.

## Operação

| Rota | Função |
|---|---|
| `GET /health/live` | Processo vivo |
| `GET /health/ready` | Banco acessível |
| `GET /metrics` | Contadores e latência no formato Prometheus, rotulados pelo template da rota; exige `operations` ou `admin` |
| `GET /api/v1/operations/{correlationId}` | Trilha de auditoria de uma operação |
| `POST /api/v1/integration/outbox/dispatch` | Despacho explícito da outbox, também disponível na interface |
| `GET /api/v1/integration/failures` | Eventos com falha permanente |
| `POST /api/v1/integration/failures/{eventId}/reprocess` | Reprocessamento auditável, sem duplicar efeitos |
| `GET /api/v1/integration/legacy-ids/{sourceSystem}/{legacyId}` | UUID global de um identificador legado |

Toda requisição aceita `X-Correlation-ID` (UUID). Sem ele, a API gera um. O valor aparece na resposta, nos logs, nos eventos e na auditoria. Uma falha num consumidor desfaz os efeitos parciais, registra a tentativa sem guardar dados da exceção e não bloqueia os demais eventos.

## Publicação gratuita

O `render.yaml` prepara um serviço **Render Free** com PostgreSQL do **Supabase Free**. Configure `DATABASE_URL` e `DEMO_ACCESS_TOKEN` no painel do provedor, nunca no Git. Com PostgreSQL, a inicialização ativa RLS e revoga os privilégios de `anon` e `authenticated` nas tabelas do protótipo, pois o acesso passa somente pela API ([orientação de segurança do Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security)).

**A publicação ainda não foi verificada.** Antes de declará-la pronta, vincule as contas, forneça os segredos e confirme a URL HTTPS, `/health/ready`, a criação e a leitura de dados e a persistência após reinício. A camada gratuita pode suspender ou hibernar por inatividade; consulte [Render Free](https://render.com/docs/free) e [pausa de projetos do Supabase Free](https://supabase.com/docs/guides/platform/free-project-pausing).

## Documentação

Comece por estes documentos:

- [`docs/ESTADO_IMPLEMENTACAO.md`](docs/ESTADO_IMPLEMENTACAO.md): o que está verificado e os limites de cada área;
- [`docs/CRONOGRAMA_EXECUCAO.md`](docs/CRONOGRAMA_EXECUCAO.md): 14 semanas, 22 demandas canônicas, dependências e critérios;
- [`docs/ROTEIRO_DEMONSTRACAO.md`](docs/ROTEIRO_DEMONSTRACAO.md) e [`docs/EVIDENCIAS_VALIDACAO.md`](docs/EVIDENCIAS_VALIDACAO.md): execução e evidências dos três fluxos;
- [`docs/MATRIZ_RASTREABILIDADE.md`](docs/MATRIZ_RASTREABILIDADE.md): requisito, implementação, teste e evidência.

### Decisões arquiteturais

| ADR | Decisão | Status |
|---|---|---|
| [ADR-001](docs/adr/ADR-001-integracao-empresa-de-servicos.md) | SOA pragmática com APIs, eventos e monólito modular | Aceito |
| [ADR-002](docs/adr/ADR-002-migracoes-aditivas.md) | Migrações versionadas e aditivas com Alembic | Aceito |
| [ADR-003](docs/adr/ADR-003-financeiro-fatura-final-e-excecao-aditiva.md) | Fatura final, vencimento por evento e exceção à regra aditiva | Aceito |
| [ADR-004](docs/adr/ADR-004-estabilizacao-v1-e-convergencia.md) | Compatibilidade v1, privacidade e convergência T12/T15 | Aceito |
| [ADR-005](docs/adr/ADR-005-fronteiras-http-e-integracao-publica.md) | Rotas e schemas por módulo; fachada pública de integração | Aceito |
| [ADR-006](docs/adr/ADR-006-leitura-resiliente-do-crm.md) | Leitura resiliente do CRM no F1: retentativa limitada e `503` | Proposto |

### Inventário de artefatos

**Planejamento e rastreabilidade**
- [`PLANO_IMPLEMENTACAO_CENARIO_4.md`](PLANO_IMPLEMENTACAO_CENARIO_4.md)
- [`docs/BACKLOG_TASKS_SUBTASKS.md`](docs/BACKLOG_TASKS_SUBTASKS.md)
- [`docs/CRONOGRAMA_EXECUCAO.md`](docs/CRONOGRAMA_EXECUCAO.md) e [`docs/governanca/`](docs/governanca/)
- [`docs/MATRIZ_RASTREABILIDADE.md`](docs/MATRIZ_RASTREABILIDADE.md)

**Produto, requisitos e negócio**
- [`docs/PRD_LOCALIZA.md`](docs/PRD_LOCALIZA.md)
- [`docs/REQUISITOS.md`](docs/REQUISITOS.md)
- [`docs/DADOS_SINTETICOS.md`](docs/DADOS_SINTETICOS.md)
- [`docs/VISAO_NEGOCIO.md`](docs/VISAO_NEGOCIO.md)

**Arquitetura**
- [`docs/arquitetura/AS_IS.md`](docs/arquitetura/AS_IS.md), [`docs/arquitetura/TO_BE.md`](docs/arquitetura/TO_BE.md) e [`docs/arquitetura/FLUXOS_INTEGRACAO.md`](docs/arquitetura/FLUXOS_INTEGRACAO.md)
- [`docs/DDD_LOCALIZA.md`](docs/DDD_LOCALIZA.md) e [`docs/TDD_LOCALIZA.md`](docs/TDD_LOCALIZA.md)
- [`docs/adr/`](docs/adr/): decisões arquiteturais

**Integrações e APIs**
- [`docs/INTEGRACOES.md`](docs/INTEGRACOES.md)
- [`docs/EXEMPLOS_API.md`](docs/EXEMPLOS_API.md): exemplos de requisição, resposta e erro
- [`docs/api/openapi.yaml`](docs/api/openapi.yaml): contrato REST
- [`docs/events/asyncapi.yaml`](docs/events/asyncapi.yaml): contrato dos eventos

**Qualidade e evolução**
- [`docs/ATRIBUTOS_QUALIDADE.md`](docs/ATRIBUTOS_QUALIDADE.md)
- [`docs/EVOLUCAO_MANUTENCAO.md`](docs/EVOLUCAO_MANUTENCAO.md)

**Entrega final**
- `output/Relatorio_Tecnico_Cenario_4.docx`: relatório técnico na estrutura do Guia, gerado por `tools/build_report.py`. Complete a tabela de participantes antes da entrega.
- `output/Apresentacao_Cenario_4.pptx`: apresentação de 18 slides, gerada por `tools/build_presentation.mjs`.
- `tools/render_diagrams.py`: gera em PNG, com o mermaid-cli, os diagramas usados no relatório e na apresentação.

**Código e testes**
- `src/archcorp/`: implementação, com migrações em `src/archcorp/infrastructure/migrations/`
- `web/`: interface React/TypeScript
- `tests/`: testes automatizados
- `scripts/`: demonstrações, carga sintética e medição de desempenho
- `tools/`: geração de OpenAPI, relatório, apresentação, diagramas e publicação do backlog

**Agentes e organização**
- [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md) e [`docs/agentes/`](docs/agentes/)
- `termino1.md`: registro histórico da rodada de documentação de setembro

### Ordem sugerida para auditoria

A ordem segue a estrutura do `Guia.pdf`:

1. `Guia.pdf`: critérios de entrega;
2. `README.md` e `AGENTS.md`: visão geral do repositório;
3. `PLANO_IMPLEMENTACAO_CENARIO_4.md`: plano geral;
4. `docs/PRD_LOCALIZA.md` e `docs/REQUISITOS.md`: produto e requisitos funcionais e não funcionais;
5. `docs/arquitetura/AS_IS.md`: cenário atual;
6. `docs/arquitetura/TO_BE.md`: arquitetura proposta, padrões e estilos;
7. `docs/adr/`, `docs/DDD_LOCALIZA.md` e `docs/TDD_LOCALIZA.md`: domínio, desenho técnico e decisões;
8. `docs/arquitetura/FLUXOS_INTEGRACAO.md` e `docs/INTEGRACOES.md`: integrações e interoperabilidade;
9. `docs/api/openapi.yaml` e `docs/events/asyncapi.yaml`: contratos técnicos;
10. `docs/EXEMPLOS_API.md`: exemplos de requisição e resposta;
11. `docs/ATRIBUTOS_QUALIDADE.md`: atributos de qualidade;
12. `docs/EVOLUCAO_MANUTENCAO.md`: escalabilidade, manutenção e evolução;
13. `docs/VISAO_NEGOCIO.md`: eixo transversal de Empreendedorismo;
14. `docs/MATRIZ_RASTREABILIDADE.md` e `docs/BACKLOG_TASKS_SUBTASKS.md`: conferência cruzada de cobertura;
15. `src/archcorp/`, `web/` e `tests/`: protótipo que sustenta a documentação;
16. `docs/ROTEIRO_DEMONSTRACAO.md` e `docs/EVIDENCIAS_VALIDACAO.md`: validação dos três fluxos;
17. `output/Apresentacao_Cenario_4.pptx`: apresentação técnica;
18. `output/Relatorio_Tecnico_Cenario_4.docx`: relatório técnico consolidado.

## Limites conhecidos

- O enunciado não informa os produtos dos cinco sistemas existentes. O AS-IS é uma hipótese a validar, e a demonstração usa módulos e simulações internas.
- O RabbitMQ recebe cópias dos eventos, mas os consumidores do protótipo são chamados pelo despachante da API.
- Não há OIDC/OAuth, contas individuais, tracing distribuído nem escala horizontal verificados.
- O ADR-006 ainda aguarda aceite do responsável do projeto.
- A URL pública, o PostgreSQL do Supabase e os arquivos finais só serão declarados entregues após conferência.
