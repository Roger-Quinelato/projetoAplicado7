# ArchCorp · Projeto Aplicado 7 · Cenário 4

Protótipo acadêmico conceitual de integração entre CRM, reservas e contratos, financeiro e faturamento, atendimento e gestão de processos. Usa dados sintéticos e não acessa sistemas reais da Localiza. A solução é um monólito modular com REST e outbox; o despacho executa consumidores internos e pode publicar uma cópia no RabbitMQ local.

## Regras para agentes

Antes de trabalhar neste repositório, leia [`AGENT.md`](AGENT.md): suas regras **SEMPRE** são obrigatórias e suas regras **NUNCA** são proibições permanentes. Agentes Claude Code também devem ler [`CLAUDE.md`](CLAUDE.md), que encaminha ao guia completo. Consulte [`docs/ESTADO_IMPLEMENTACAO.md`](docs/ESTADO_IMPLEMENTACAO.md) para distinguir funcionalidades verificadas de metas e pendências. Nunca descreva este protótipo como conectado a sistemas reais da Localiza.

## Execução rápida

Requisitos: Docker Desktop com Docker Compose.

```powershell
docker compose up --build
```

A interface e a API ficam em `http://localhost:8000`, a documentação Swagger em `http://localhost:8000/docs` e o RabbitMQ local em `http://localhost:15672` (`guest`/`guest`). No Compose, o navegador usa a mesma origem da API. O despacho da outbox é explícito pelo botão da interface ou por `POST /api/v1/integration/outbox/dispatch`.

Para executar a demonstração completa:

```powershell
./scripts/demo.ps1
```

## Autenticação da demonstração

No desenvolvimento local, as rotas protegidas aceitam tokens fixos de demonstração (`demo-admin`, `demo-commercial`, `demo-contracts`, `demo-finance`, `demo-support`, `demo-operations`). **Não há OIDC/OAuth implementado.** Com `PUBLIC_DEMO=true`, esses tokens são rejeitados e apenas `DEMO_ACCESS_TOKEN` — segredo aleatório com pelo menos 24 caracteres configurado fora do repositório — funciona. O acesso público usa uma credencial compartilhada, adequada apenas ao protótipo acadêmico. Não inserir dados pessoais reais.

## Frontend e deploy gratuito

Para desenvolver a interface: `cd web`, `npm ci`, `npm run dev`, com a API rodando na porta 8000. `npm run build` gera `web/dist`, servido pelo FastAPI na raiz. O Dockerfile compila a interface e usa a porta definida por `PORT`.

O arquivo `render.yaml` prepara um **Render Free** com `DATABASE_URL` (PostgreSQL do Supabase Free) e `DEMO_ACCESS_TOKEN` definidos no painel, nunca no Git. `PUBLIC_DEMO=true` bloqueia os tokens locais. No PostgreSQL, a inicialização ativa RLS e revoga os privilégios de `anon` e `authenticated` nas tabelas do protótipo, pois o acesso de demonstração passa somente pela API FastAPI; consulte a [orientação de segurança do Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security). A publicação ainda exige vincular as contas Render/Supabase, fornecer os segredos, aplicar o deploy e verificar HTTPS, `/health/ready`, criação/leitura e persistência após reinício. A infraestrutura gratuita pode suspender ou hibernar por inatividade; consulte [Render Free](https://render.com/docs/free) e [Supabase Free](https://supabase.com/docs/guides/platform/free-project-pausing) antes de usar. O banco SQLite local é somente para desenvolvimento.

## Desenvolvimento e testes

```powershell
python -m venv .venv
./.venv/Scripts/pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
./.venv/Scripts/pytest
```

Os artefatos principais estão em:

- `docs/REQUISITOS.md`: requisitos funcionais e não funcionais do cenário;
- `docs/CRONOGRAMA_EXECUCAO.md`: 14 semanas, 22 demandas canônicas, dependências e critérios;
- `docs/arquitetura/`: AS-IS, TO-BE, componentes, implantação e sequências;
- `docs/EXEMPLOS_API.md`: exemplos executáveis de requisição, resposta e erro;
- `docs/api/openapi.yaml`: contrato REST;
- `docs/events/asyncapi.yaml`: contrato dos eventos;
- `docs/MATRIZ_RASTREABILIDADE.md`: requisito, implementação, teste e evidência;
- `docs/ROTEIRO_DEMONSTRACAO.md`: execução dos três fluxos;
- `output/`: relatório técnico e apresentação final.

### Inventário completo de artefatos (Cenário 4)

**Planejamento / rastreabilidade**
- `PLANO_IMPLEMENTACAO_CENARIO_4.md`
- `docs/BACKLOG_TASKS_SUBTASKS.md`
- `docs/CRONOGRAMA_EXECUCAO.md` e `docs/governanca/`
- `docs/MATRIZ_RASTREABILIDADE.md`

**Produto, requisitos e visão de negócio**
- `docs/PRD_LOCALIZA.md`
- `docs/REQUISITOS.md`
- `docs/VISAO_NEGOCIO.md`

**Arquitetura (AS-IS / TO-BE / DDD / TDD)**
- `docs/arquitetura/AS_IS.md`
- `docs/arquitetura/TO_BE.md`
- `docs/arquitetura/FLUXOS_INTEGRACAO.md`
- `docs/adr/ADR-001-integracao-empresa-de-servicos.md`
- `docs/DDD_LOCALIZA.md`
- `docs/TDD_LOCALIZA.md`

**Integrações e APIs**
- `docs/INTEGRACOES.md`
- `docs/EXEMPLOS_API.md`
- `docs/api/openapi.yaml`
- `docs/events/asyncapi.yaml`

**Qualidade e evolução**
- `docs/ATRIBUTOS_QUALIDADE.md`
- `docs/EVOLUCAO_MANUTENCAO.md`

**Validação/demonstração**
- `docs/ROTEIRO_DEMONSTRACAO.md`
- `docs/EVIDENCIAS_VALIDACAO.md`

**Entrega final**
- `output/Relatorio_Tecnico_Cenario_4.docx` — relatório técnico gerado; revisar após cada mudança de escopo e completar integrantes/contribuições.
- `output/Apresentacao_Cenario_4.pptx` — apresentação técnica gerada; revisar antes da submissão.

**Código e testes**
- `src/archcorp/` (implementação/protótipo)
- `tests/` (testes automatizados)
- `docker-compose.yml`, `migrations/`, `scripts/`, `tools/`

**Meta/organização**
- `CLAUDE.md` — instruções iniciais para Claude Code;
- `AGENT.md`, `README.md`, `termino1.md`

### Ordem sugerida para auditoria

A ordem segue a estrutura do `Guia.pdf` (requisitos → arquitetura atual → arquitetura proposta → padrões → integrações → sistemas corporativos → qualidade → evolução → negócio → entrega/demonstração → relatório final):

1. `Guia.pdf` — critérios de entrega;
2. `README.md` e `AGENT.md` — visão geral do repositório;
3. `PLANO_IMPLEMENTACAO_CENARIO_4.md` — plano geral;
4. `docs/PRD_LOCALIZA.md` e `docs/REQUISITOS.md` — produto, requisitos funcionais e não funcionais;
5. `docs/arquitetura/AS_IS.md` — cenário atual;
6. `docs/arquitetura/TO_BE.md` — arquitetura proposta e padrões/estilos;
7. `docs/adr/ADR-001-integracao-empresa-de-servicos.md`, `docs/DDD_LOCALIZA.md` e `docs/TDD_LOCALIZA.md` — domínio, desenho técnico e justificativa das decisões arquiteturais;
8. `docs/arquitetura/FLUXOS_INTEGRACAO.md` e `docs/INTEGRACOES.md` — integrações (mínimo três) e interoperabilidade;
9. `docs/api/openapi.yaml` e `docs/events/asyncapi.yaml` — contratos técnicos das integrações;
10. `docs/EXEMPLOS_API.md` — exemplos de requisição/resposta;
11. `docs/ATRIBUTOS_QUALIDADE.md` — mínimo cinco atributos de qualidade;
12. `docs/EVOLUCAO_MANUTENCAO.md` — escalabilidade, manutenção e evolução;
13. `docs/VISAO_NEGOCIO.md` — eixo transversal de Empreendedorismo;
14. `docs/MATRIZ_RASTREABILIDADE.md` e `docs/BACKLOG_TASKS_SUBTASKS.md` — conferência cruzada de cobertura;
15. `src/archcorp/` e `tests/` — protótipo/implementação sustentando a documentação;
16. `docs/ROTEIRO_DEMONSTRACAO.md` e `docs/EVIDENCIAS_VALIDACAO.md` — validação dos três fluxos integrados;
17. `output/Apresentacao_Cenario_4.pptx` — apresentação técnica final;
18. `output/Relatorio_Tecnico_Cenario_4.docx` — relatório técnico consolidado; conferir paginação e dados da equipe antes da entrega.

## Health checks e operação

- `GET /health/live`: processo vivo;
- `GET /health/ready`: banco acessível;
- `GET /metrics`: contadores e latência no formato Prometheus;
- `GET /api/v1/operations/{correlationId}`: trilha de auditoria de uma operação;
- `GET /api/v1/integration/failures`: mensagens com falha;
- `POST /api/v1/integration/failures/{eventId}/reprocess`: reprocessamento auditável;
- `POST /api/v1/integration/outbox/dispatch`: despacho explícito da outbox no protótipo.

## Limites conhecidos

Produtos e tecnologias dos cinco sistemas existentes não constam no enunciado. O AS-IS é uma hipótese a validar. A demonstração usa módulos e simulações internas; integrações reais exigem confirmação dos sistemas, contratos e responsáveis. O broker RabbitMQ recebe cópias no ambiente local, mas os consumidores deste protótipo são chamados pelo despachante da API. Não há OIDC, tracing distribuído ou escala horizontal verificados. A URL pública e os arquivos finais só serão declarados entregues após conferência.
