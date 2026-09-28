# Evidências de validação

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Verificação atual em 27/09/2026

- `PYTHONPATH=src .venv/Scripts/python -m pytest -q --tb=short`: **17 testes aprovados**, um aviso de depreciação de Starlette/AnyIO. Inclui reserva → contrato → fatura → pagamento simulado; chamado → resolução → workflow; segredo do modo público; idempotência e reconciliação.
- `cd web && npm run build`: TypeScript e Vite concluídos sem erro, com `web/dist` gerado. Falta testar a interface no serviço HTTPS público.
- Inspeção local em navegador na mesma origem `http://127.0.0.1:8000/`: tela de acesso, painel e formulário CRM renderizaram; cadastro de cliente sintético apareceu na lista após escrita na API. A API respondeu `UP` em `/health/ready`. O teste HTTPS público continua pendente.
- `tools/build_report.py`: DOCX regenerado em 27/09/2026. `tools/build_presentation.mjs`: PPTX regenerado; recibo `.codex-finalizer/Apresentacao_Cenario_4.validation.json` mostra integridade, layout e reimportação aprovados. Revisão editorial final e preenchimento da equipe pendentes.
- Jira `ARCH7`: 22 tarefas T01–T22 criadas, com prioridade, data por semana e vínculos de bloqueio. Trello e Notion criados como índices/documentação; não há sincronização automática. Os respectivos IDs estão em `JIRA_SYNC.json`, `TRELLO_SYNC.json` e `NOTION_SYNC.json`.
- GitHub: [PR #2](https://github.com/Roger-Quinelato/projetoAplicado7/pull/2) atualizado com o commit de implementação; [22 issues T01–T22](https://github.com/Roger-Quinelato/projetoAplicado7/issues) criadas como índice, cada uma com link para o Jira. Sete marcos Q1–Q7 e etiquetas de semana, tipo, prioridade e status foram verificados nas issues T01 e T22. O GitHub Project ainda requer autorização do escopo `project`.
- Render e Supabase exigem autenticação do titular nas respectivas contas. Nenhuma URL pública, banco em nuvem ou persistência após reinício foi verificada até esta data.

As evidências de 13/09 e 14/09 abaixo são históricas e descrevem a versão anterior do protótipo.

## Execução em 13 de setembro de 2026

- Suíte automatizada: 13 testes aprovados em 4,11 segundos.
- Fluxo F1: rascunho criado a partir do UUID do CRM e repetição devolveu o mesmo contrato.
- Fluxo F2: repetição da ativação e novo despacho mantiveram uma cobrança e uma preparação de retirada.
- Fluxo F3: chamado recebeu SLA e iniciou uma instância de resolução.
- Degradação: atendimento e assistência 24h registrou `PENDING_ENTITLEMENT` e reconciliou após retorno de Contracts.
- Segurança: papel de atendimento e assistência 24h recebeu 403 ao tentar criar cliente.
- Falha permanente: evento chegou a `FAILED` após três tentativas, apareceu na consulta e voltou a `PENDING` por reprocessamento auditado.
- Reservas e contratos: o OpenAPI salvo corresponde ao `app.openapi()`, contém esquemas de resposta, exemplos dos três fluxos e UUID nos identificadores globais; o AsyncAPI contém três eventos com o envelope obrigatório, incluindo `causationId`.
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

## Inspeção dos artefatos em 14 de setembro de 2026

- A verificação final da suíte aprovou novamente os 13 testes; a execução completa levou 22,60 segundos e emitiu apenas o aviso de depreciação já registrado.
- Os sete blocos Mermaid de AS-IS, TO-BE, fluxos e planejamento foram renderizados em SVG sem erro pelo Mermaid CLI 11.17.0.
- O relatório técnico foi regenerado, renderizado em 18 páginas e inspecionado integralmente; não foram encontrados cortes, sobreposições, páginas vazias ou tabelas quebradas.
- A apresentação foi regenerada com 15 slides. Os validadores de integridade, geometria, fontes e reimportação aprovaram o pacote, e todos os slides foram inspecionados em PNG.

As imagens e recibos técnicos de verificação permanecem em `tmp/report-render-final/`, `tmp/presentation-build/`, `tmp/mermaid-render/` e `.codex-finalizer/`.
