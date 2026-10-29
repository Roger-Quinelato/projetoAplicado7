---
name: archcorp-insights-operacionais
description: Gera e interpreta o relatório operacional do ArchCorp, que transforma logs, métricas e auditoria em indicadores para decisão, e consolida as evidências de verificação. Use após o ensaio da demonstração, antes de atualizar relatório e slides, ou para decidir prioridades de evolução.
---

# Informação operacional do ArchCorp

O objetivo não é coletar logs, e sim transformar dados já gravados pela API em informação que apoie decisões. Tudo é lido de endpoints públicos; nenhuma tabela é acessada diretamente.

## Fontes

| Fonte | O que oferece |
|---|---|
| `GET /api/v1/integration/insights` (`operations`/`admin`) | Eventos por tipo e estado, retentativas, atraso do despacho por consumidor (p50, p95, máximo), uso por módulo/operação/resultado na auditoria, chaves de idempotência por operação |
| `GET /metrics` (`operations`/`admin`) | Requisições por rota e status; histograma de latência (p95 por operação); erros por `code` do problem+json; repetições recuperadas por `Idempotency-Key` |
| Resumos `contracts/summary`, `finance/invoices/summary`, `support/tickets/summary`, `workflow/processes/summary` | Contagens contadas no servidor |
| Logs JSON | Uma linha por requisição, com o template da rota (sem identificadores), status e `correlationId`, em UTC |

As métricas ficam em memória: valem desde o último reinício da API. Gere o relatório no mesmo processo que executou a demonstração.

## Gerar o relatório

```powershell
$env:PYTHONPATH = "src"
./.venv/Scripts/python scripts/relatorio_operacional.py --base-url http://localhost:8000 --token demo-admin
```

Saída: `output/insights/relatorio_operacional.md` e `.json`. Código `0` com o relatório gerado; `2` com a API inacessível.

## Como interpretar

| Indicador | Pergunta | Regra da decisão sugerida |
|---|---|---|
| Funil F1→F2→F3 | Em que etapa o fluxo trava? | Etapa em que menos de 50% avança |
| Cumprimento de SLA | O SLA herdado é cumprido? | Mais de 20% de `BREACHED` entre os resolvidos → rever premissas de prazo |
| Atraso de despacho | O despacho explícito atrasa os efeitos? | p95 acima de 60 s → avaliar agendador (evolução) |
| Retentativas e falhas | Qual consumidor endurecer? | Qualquer `FAILED` → corrigir a causa e reprocessar |
| Duplicidades evitadas | A idempotência funciona na prática? | Repetições recuperadas sem efeito duplicado |
| Latência e erros | Há gargalo ou erro recorrente? | p95 acima de 500 ms → violação do RNF-07 |
| Uso por módulo | Onde concentrar evolução e testes? | Contexto com mais operações auditadas |

As regras são heurísticas explícitas para a demonstração com dados sintéticos. Não as apresente como metas de produção.

## Evidência de verificação

```powershell
./.venv/Scripts/python tools/consolidar_evidencias.py --com-web
```

Grava `output/evidencias/evidencias.json` com o commit, o resultado do pytest (JUnit), do `export_openapi --check`, do `performance_smoke` (p95) e, com `gh`, da CI do commit. Rode com a árvore limpa: o campo `arvoreLimpa` registra se havia alterações não commitadas. Esse arquivo é a única fonte dos números citados em `docs/EVIDENCIAS_VALIDACAO.md`, no relatório e nos slides.
