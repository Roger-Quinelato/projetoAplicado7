# Resumo — Agente 3 (Qualidade, segurança e operação) — `3a3d8bd`, 2026-10-01 UTC

Tudo foi executado na cópia isolada `$SP/iso`. O manifesto bateu antes e depois das execuções, e o repositório real ficou intacto. Os bancos usados são descartáveis: SQLite em `$A/`, PostgreSQL 16 em `/tmp/a3pg`, com a porta 55432 aberta só em 127.0.0.1. Nenhuma `DATABASE_URL` foi herdada do ambiente.

## Execuções principais
- pytest: **57/57** em Py 3.11.15 e em Py 3.12.3 (SQLite), com 1 DeprecationWarning do anyio. O documento registra 57 na entrada vigente; "13" é a contagem histórica de 13/09.
- pytest em PostgreSQL: **57/57**, mas só depois de alterar o `conftest` numa cópia experimental, porque o `conftest` original força SQLite.
- `export_openapi.py --check`: rc=0 e saída byte a byte idêntica; o `openapi-spec-validator` aprovou a spec.
- `npm ci && npm run build`: OK, com 0 vulnerabilidades no npm. `test:browser`: não aplicável, o script não existe em 3a3d8bd.
- `performance_smoke.py`: p95 de 11,1 a 13,7 ms (SQLite/PG, 3.11/3.12), dentro da meta de 500 ms. O script mede só `/health/ready`. Medição complementar dos fluxos: F1/F2/F3 com p95 entre 39 e 51 ms.
- Migrações em SQLite e PG: banco vazio, banco legado 0001 com dados (dados e unicidades preservados) e downgrade→upgrade passaram. O caso de borda "esquema 0002 sem carimbo" falha em PG.
- Jornada Playwright, com a interface real servida pela API sobre PG: completa, 13 capturas. O axe-core apontou contraste insuficiente (serious) em todas as telas.
- CI do commit 3a3d8bd (run 36660119780): success, incluindo `docker build`. Docker local indisponível; compose e imagem não foram executados.

## Achados mais graves (nenhum crítico)
- **A3-01 (alta, demonstrado):** um erro de banco num consumidor deixa a sessão sem `rollback`. Resultado: 500 em todo despacho, evento parado em `PENDING`/`attempts=0` para sempre, a outbox inteira trava e `/failures` fica vazio.
- **A3-02 (média):** dois despachos simultâneos em PG dão `[200,500]` em 15 de 15 rodadas; falta `FOR UPDATE SKIP LOCKED`.
- **A3-03 (média):** ativação concorrente, ou duplo clique em "Ativar" na interface, gera **dois `ContractActivated.v1`** para o mesmo contrato. Cobrança e processo não duplicam, graças às restrições únicas.
- **A3-04 (média):** com o broker "opcional" fora do ar, o evento vai a FAILED com motivo vazio, embora a fatura e o processo já tenham sido criados.
- **A3-05 (média):** `alembic_version` e as sequências ficam sem REVOKE para `anon`. Com os privilégios padrão do Supabase simulados, `anon` apagou a linha e a aplicação deixou de iniciar.
- **A3-06 (média):** `amount` ≥ 10^12 provoca 500 em PG; o SQLite aceita, então os testes não pegam.
- **A3-07 (média):** `/metrics` é público e usa o caminho bruto como rótulo. 300 requisições anônimas geraram 600 séries; a memória cresce sem limite e IDs ficam expostos.
- **A3-08 (média):** o formatter JSON descarta `exc_info`, então os erros 500 aparecem sem causa.
- **A3-09 (média):** starlette 0.47.3 (transitiva) tem 7 advisories, entre eles o CVE-2025-62727 (Range). Com 8000 intervalos, uma requisição levou 7,6 s e a latência de `/health/live` subiu.
- **A3-10, A3-11 (média):** na interface, a chave de idempotência muda a cada clique, o formulário é apagado mesmo quando dá erro e o painel só abre com o perfil admin. Há também falhas de contraste.
- **A3-12, A3-13 (média):** a credencial pública recebe todos os papéis. O CI não usa PG, não testa concorrência, acessibilidade nem desempenho, e o teste de RLS usa conexão falsa.
- Baixas: A3-14 (borda de migração), A3-15 (cabeçalhos de segurança), A3-16 (e-mail no log de acesso), A3-17 (409 em vez de replay), A3-18 (lock/root/digest), A3-19 (divergência documental: "OIDC simulado", retentativa sem backoff).

## Pontos positivos comprovados
- O segredo do modo público é imposto na inicialização, e os tokens `demo-*` são rejeitados.
- `compare_digest` é usado; não há token nos logs nem segredo no histórico.
- RLS/REVOKE é efetivo nas 16 tabelas do modelo em PG local.
- Não há duplicidade de cobrança ou processo sob concorrência.
- Os dados persistem após reinício com PG local.
- O contrato OpenAPI está sincronizado.

## Conclusão por tarefa
- **T17:** parcial. Segredo OK; papéis, logs, falhas recuperáveis e RLS ainda com defeitos (A3-01/04/05/07/08/12).
- **T18:** parcial. Testes, contrato e desempenho existem e passam; acessibilidade, PG/concorrência e medição de F1–F3 não são validados pelo projeto.
- **T20:** não atendido. Não há URL, HTTPS nem persistência remota; a issue #23 está aberta e "planejado". Só houve equivalente local.

## Limitações
- OSV.dev e GitHub Advisory bloqueados pelo proxy (403); usei pip-audit com a fonte PyPI.
- Supabase e Render não foram acessados.
- Docker indisponível.
- RabbitMQ ausente; simulei com porta fechada.
- Concorrência testada com 1 processo uvicorn.
- O evento "venenoso" de A3-01 foi injetado diretamente na tabela; a mesma causa raiz aparece sem injeção no despacho concorrente (A3-02).
- Fontes do Google bloqueadas, então o contraste foi avaliado com a fonte de fallback.
- A branch `3fdb533` não é auditável (L-01).
