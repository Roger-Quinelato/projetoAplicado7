# Evidências de validação

## Execução em 13 de setembro de 2026

- Suíte automatizada: 12 testes aprovados em 20,76 segundos.
- Fluxo F1: rascunho criado a partir do UUID do CRM e repetição devolveu o mesmo contrato.
- Fluxo F2: repetição da ativação e novo despacho mantiveram uma cobrança e um onboarding.
- Fluxo F3: chamado recebeu SLA e iniciou uma instância de resolução.
- Degradação: atendimento registrou `PENDING_ENTITLEMENT` e reconciliou após retorno de Contracts.
- Segurança: papel de atendimento recebeu 403 ao tentar criar cliente.
- Falha permanente: evento chegou a `FAILED` após três tentativas, apareceu na consulta e voltou a `PENDING` por reprocessamento auditado.
- Contratos: o OpenAPI salvo corresponde ao `app.openapi()`, contém exemplos dos três fluxos e o AsyncAPI contém três eventos com o envelope obrigatório, incluindo `causationId`.
- Arquitetura: teste estático não encontrou importação de modelos internos entre contextos de negócio.
- Desempenho local: 200 consultas de prontidão tiveram p95 de 6,36 ms, abaixo da meta de 500 ms no ambiente de teste local.

## Ambiente da execução

- Sistema operacional: Microsoft Windows NT 10.0.26200.0.
- Python: 3.12.14.
- Processador informado pelo ambiente: Intel64 Family 6 Model 142 Stepping 10.
- Banco dos testes e da medição: SQLite local.
- Comando da suíte: `python -m pytest -q tests -p no:cacheprovider` com `PYTHONPATH=src`.
- Comando da medição: `python scripts/performance_smoke.py` com `PYTHONPATH=src`.

O aviso de depreciação emitido pelo cliente de teste pertence à compatibilidade interna entre versões de Starlette e AnyIO. Ele não altera o resultado dos testes. A atualização dessas dependências deve ocorrer em uma tarefa de manutenção com nova execução da suíte.

## Limites da evidência

Os testes usam SQLite e adaptadores internos para rapidez. Docker Compose fornece PostgreSQL e RabbitMQ para a demonstração. A validação em infraestrutura externa, TLS, provedor OIDC real e produtos legados depende dos ambientes da organização e fica fora das informações fornecidas pelo enunciado.

Os diagramas Mermaid receberam validação estrutural dos blocos e das ramificações. O ambiente não possui renderizador Mermaid instalado; a renderização visual permanece como verificação documental pendente e não altera as evidências de comportamento do protótipo.
