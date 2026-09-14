# ArchCorp Cenário 4

Protótipo executável de integração entre CRM, contratos, financeiro, atendimento e gestão de processos. A solução segue o ADR vigente: SOA pragmática entregue como monólito modular, com REST para respostas imediatas e eventos persistidos em outbox para efeitos assíncronos.

## Execução rápida

Requisitos: Docker Desktop com Docker Compose.

```powershell
docker compose up --build
```

A API fica disponível em `http://localhost:8000`, a documentação Swagger em `http://localhost:8000/docs` e o RabbitMQ em `http://localhost:15672` (`guest`/`guest`, apenas no ambiente local).

Para executar a demonstração completa:

```powershell
./scripts/demo.ps1
```

## Autenticação da demonstração

As rotas protegidas aceitam tokens locais que simulam papéis emitidos por um provedor OIDC. Use `Authorization: Bearer demo-admin` no roteiro completo. Também existem `demo-commercial`, `demo-contracts`, `demo-finance`, `demo-support` e `demo-operations`. O simulador existe apenas para execução acadêmica; a arquitetura mantém a porta de autenticação substituível por um provedor OIDC real.

## Desenvolvimento e testes

```powershell
python -m venv .venv
./.venv/Scripts/pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
./.venv/Scripts/pytest
```

Os artefatos principais estão em:

- `docs/arquitetura/`: AS-IS, TO-BE, componentes, implantação e sequências;
- `docs/api/openapi.yaml`: contrato REST;
- `docs/events/asyncapi.yaml`: contrato dos eventos;
- `docs/MATRIZ_RASTREABILIDADE.md`: requisito, implementação, teste e evidência;
- `docs/ROTEIRO_DEMONSTRACAO.md`: execução dos três fluxos;
- `output/`: relatório técnico e apresentação final.

### Inventário completo de artefatos (Cenário 4)

**Planejamento / rastreabilidade**
- `PLANO_IMPLEMENTACAO_CENARIO_4.md`
- `docs/BACKLOG_TASKS_SUBTASKS.md`
- `docs/MATRIZ_RASTREABILIDADE.md`

**Requisitos e visão de negócio**
- `docs/REQUISITOS.md`
- `docs/VISAO_NEGOCIO.md`

**Arquitetura (AS-IS / TO-BE)**
- `docs/arquitetura/AS_IS.md`
- `docs/arquitetura/TO_BE.md`
- `docs/arquitetura/FLUXOS_INTEGRACAO.md`
- `docs/adr/ADR-001-integracao-empresa-de-servicos.md`

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
- `output/Relatorio_Tecnico_Cenario_4.docx` (versões renderizadas em PDF/imagens também em `tmp/report-render-v2` a `v4`)
- Apresentação em slides/imagens em `tmp/presentation-build/` (fonte `.pptx` não localizada — confirmar local)

**Código e testes**
- `src/archcorp/` (implementação/protótipo)
- `tests/` (testes automatizados)
- `docker-compose.yml`, `migrations/`, `scripts/`, `tools/`

**Meta/organização**
- `AGENT.md`, `AGENTS.md`, `README.md`, `termino1.md`

### Ordem sugerida para auditoria

A ordem segue a estrutura do `Guia.pdf` (requisitos → arquitetura atual → arquitetura proposta → padrões → integrações → sistemas corporativos → qualidade → evolução → negócio → entrega/demonstração → relatório final):

1. `Guia.pdf` — critérios de entrega;
2. `README.md` e `AGENT.md` — visão geral do repositório;
3. `PLANO_IMPLEMENTACAO_CENARIO_4.md` — plano geral;
4. `docs/REQUISITOS.md` — requisitos funcionais e não funcionais;
5. `docs/arquitetura/AS_IS.md` — cenário atual;
6. `docs/arquitetura/TO_BE.md` — arquitetura proposta e padrões/estilos;
7. `docs/adr/ADR-001-integracao-empresa-de-servicos.md` — justificativa das decisões arquiteturais;
8. `docs/arquitetura/FLUXOS_INTEGRACAO.md` e `docs/INTEGRACOES.md` — integrações (mínimo três) e interoperabilidade;
9. `docs/api/openapi.yaml` e `docs/events/asyncapi.yaml` — contratos técnicos das integrações;
10. `docs/EXEMPLOS_API.md` — exemplos de requisição/resposta;
11. `docs/ATRIBUTOS_QUALIDADE.md` — mínimo cinco atributos de qualidade;
12. `docs/EVOLUCAO_MANUTENCAO.md` — escalabilidade, manutenção e evolução;
13. `docs/VISAO_NEGOCIO.md` — eixo transversal de Empreendedorismo;
14. `docs/MATRIZ_RASTREABILIDADE.md` e `docs/BACKLOG_TASKS_SUBTASKS.md` — conferência cruzada de cobertura;
15. `src/archcorp/` e `tests/` — protótipo/implementação sustentando a documentação;
16. `docs/ROTEIRO_DEMONSTRACAO.md` e `docs/EVIDENCIAS_VALIDACAO.md` — validação dos três fluxos integrados;
17. Slides em `tmp/presentation-build/` — apresentação técnica final;
18. `output/Relatorio_Tecnico_Cenario_4.docx` — relatório técnico consolidado (15–20 páginas), por último, pois amarra todo o restante.

> Observação: existem múltiplas pastas de render do relatório (`tmp/report-render-v1` a `v4`) além do `.docx` em `output/`. Confirmar qual é a versão oficial antes de tratar as demais como obsoletas.

## Health checks e operação

- `GET /health/live`: processo vivo;
- `GET /health/ready`: banco acessível;
- `GET /metrics`: contadores e latência no formato Prometheus;
- `GET /api/v1/operations/{correlationId}`: trilha de auditoria de uma operação;
- `GET /api/v1/integration/failures`: mensagens com falha;
- `POST /api/v1/integration/failures/{eventId}/reprocess`: reprocessamento auditável;
- `POST /api/v1/integration/outbox/dispatch`: despacho explícito da outbox no protótipo.

## Limites conhecidos

Produtos e tecnologias dos cinco sistemas existentes não constam no enunciado. O projeto trata os detalhes do AS-IS como premissas a validar. A demonstração usa adaptadores internos substituíveis; integrações reais exigem confirmação dos produtos, contratos e responsáveis da organização.
