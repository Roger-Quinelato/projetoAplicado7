# Auditoria: excesso, não compartilhamento e redundância

Base: branch `viabilidade-e-documentos` @ `f8945f3` (`aceite-integrado` + PR #72), em 20/10/2026. Modo revisão: nenhum código foi alterado. Critério de domínio comum aplicado manualmente: a skill `component-common-domain-detection` só está instalada na máquina local.

**Resumo:** 14 achados. Os dois mais urgentes são do mesmo tipo: falta compartilhar paginação e leitura de clientes (achados 1 e 2). Três envolvem regra de domínio sem dono no backend (3, 7 e 9), e dois exigem ADR (4 e 5). O achado 6 foi corrigido em parte no #72.

| # | Achado | Urg. | Risco ao corrigir | Risco sem corrigir | ROI | Arquivos | Esforço | Recibo |
|---|---|---|---|---|---|---|---|---|
| 1 | Listagens cortadas em 200 sem paginação (só o CRM tem `limit`/`offset`) | Alta | Média | Alta | Bom | ~12 | Médio | `contracts/routes.py:200,252`, `finance/service.py:210`, `finance/routes.py:235`, `support/service.py:246`, `workflow/routes.py:99,114` |
| 2 | `customerName` copiado em 3 telas, a partir de `listCustomers({active:true})` (até 200) | Alta | Baixa | Alta | Excelente | 4 | Pequeno | `Crm.tsx:24-28`, `Contracts.tsx:26-30`, `Support.tsx:63` |
| 3 | Grupo, proteção e categoria só existem como listas na UI; a API aceita texto livre | Alta | Alta (v1) | Média | Bom | 6 | Médio | `Contracts.tsx:12-16`, `Support.tsx:46-47`, `contracts/routes.py:85`, `support/schemas.py:28`, `test_extended_modules.py:11` ("Economico") |
| 4 | `IdempotencyStore`/`audit` transversais dentro de `integration` | Média | Alta | Baixa | Marginal | 8 | Médio | ADR-003; `ESTADO_IMPLEMENTACAO.md` (Financeiro) |
| 5 | UTC e `money` reimplementados; `money` devolve `Decimal` em Finance e `str` em Contracts | Média | Média | Média | Bom | 7 | Pequeno | `finance/domain.py:24-39`, `contracts/service.py:19-35`, `support/domain.py:75`, `workflow/domain.py:24` |
| 6 | Documentos redundantes e desatualizados | Média | Baixa | Média | Bom | ~20 | Médio | Parcial (#72): aviso de 27/09 e `termino1.md`. Continuam as sobreposições PRD/VISÃO/REQUISITOS, TDD/ARQUITETURA/INTEGRAÇÕES e BACKLOG/CRONOGRAMA |
| 7 | A UI recalcula permissões do domínio | Média | Média | Média | Marginal | 4 | Médio | `Finance.tsx:9-11`, `Workflow.tsx:13` |
| 8 | Consultas e serialização nas rotas, não no serviço | Baixa | Média | Baixa | Marginal | 5 | Pequeno | `contracts/routes.py:200`, `workflow/routes.py:99`, `finance/routes.py:235` |
| 9 | Ciclo de cobrança declarado em 4 lugares | Baixa | Baixa | Baixa | Bom | 4 | Trivial | `contracts/schemas.py:14`, `contracts/routes.py:92`, `finance/domain.py:19`, `Contracts.tsx:8` |
| 10 | Shim `archcorp/schemas.py` ainda importado por 7 módulos | Baixa | Baixa | Baixa | Bom | 7 | Pequeno | `main.py`, `errors.py` e 5 routers |
| 11 | `assert_problem` 3×; `ADMIN` e criação de dados repetidos em 3 specs E2E | Baixa | Baixa | Baixa | Bom | 7 | Pequeno | `test_foundation.py:19`, `test_f1…:42`, `test_t15…:113`, `web/e2e/*.spec.ts` |
| 12 | `HTTPException` ao lado de `DomainError` | Baixa | Baixa | Baixa | Bom | 3 | Trivial | `workflow/routes.py:107`, `integration/routes.py:57,82` |
| 13 | `Gate` e `SlaBadge` reimplementam `ErrorPanel` e `Status` | Baixa | Baixa | Baixa | Marginal | 2 | Trivial | `App.tsx`, `Support.tsx` |
| 14 | `output/` versionado (134 arquivos, 6,4 MB) já diverge da fonte | Baixa | Baixa | Média | Bom | 2 | Trivial | O PPTX mostra "211 testes" e "p95 4,22 ms"; `build_presentation.mjs`, 246 e 45,1 ms |

Sem achado:
- confirmação antes de ação destrutiva;
- navegação (sem destino morto);
- `DispatchButton` (repetição intencional, já compartilhado);
- `integration` sem regra de negócio.

## Agrupamentos (`handoff.yaml`)

- **paginacao_compartilhada (1, 2).** `limit`/`offset` em todas as listagens, no padrão do CRM, e a UI busca clientes por id. Mudança aditiva na v1.
- **dominio_comum (3, 7, 9).** O dono do domínio passa a expor catálogos e ações permitidas. Fechar a validação do 3 quebra a v1: precisa de nova versão ou de exceção em ADR.
- **kernel_compartilhado (4, 5).** Precisa de ADR antes de criar `infrastructure/clock.py`, `money.py` e `idempotency.py` (`AGENTS.md`: fronteiras).
- **higiene (6, 8, 10–14).** PRs pequenos e independentes.

## Próxima ação sugerida

Primeiro o grupo `paginacao_compartilhada`: maior risco sem correção, sem ADR e mudança aditiva. Depois, `/workflow-audit:plan` sobre este `handoff.yaml` para quebrar os grupos em tarefas.
