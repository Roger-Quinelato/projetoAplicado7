# Evidências de validação

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Verificação local em 30/09/2026 (T18)

- Windows, Python 3.12, SQLite local: `PYTHONPATH=src python -m pytest -q tests
  -p no:cacheprovider`: **84 aprovados** em 198,55 s; um aviso de depreciação
  Starlette/AnyIO. Inclui contratos REST/eventos, migrações, papéis, três fluxos,
  reentrega, recuperação SQL, privacidade, centavos e estados finais de workflow.
- `cd web; npm run test:browser`: **11 aprovados** em 30 s; `npm run build`:
  aprovado. Chromium headless; API com respostas sintéticas nos testes da interface.
- Acessibilidade: seis telas de contexto/painel e tela de acesso sem violações
  detectadas pelo axe nos grupos WCAG 2/2.1 A/AA; navegação por Tab/Enter alcança
  o CRM. Antes da correção, seis varreduras falharam por contraste. Ajustados
  rótulos, textos auxiliares, lista vazia, cabeçalho de tabela e rodapé.
- Limite: varredura automática com coleções vazias e um caminho de teclado não
  comprova conformidade WCAG completa, leitores de tela ou todos os estados.
- `scripts/performance_smoke.py`: **200 amostras**, p95 **3,68 ms**, meta local
  500 ms, aprovado. Medição de `/health/ready` em SQLite, sem carga concorrente;
  não extrapolar para APIs de negócio ou serviço publicado.
- Não executado: Docker neste host, PostgreSQL/Supabase real, RabbitMQ,
  HTTPS público, persistência após reinício publicado ou OIDC. T20 continua pendente.
- Cada tarefa e seu aceite estão em `EXECUCAO_TAREFAS.md`. Relatório e slides
  foram atualizados na T19 a partir dessas evidências.

## Revisão documental em 30/09/2026 (T19)

- Relatório regenerado e renderizado: **18 páginas** inspecionadas, sem cortes,
  sobreposições ou tabelas quebradas. Corrigidas as afirmações de OIDC e de
  preservação de tentativas no reprocessamento; incluídos resultados da T18.
- Apresentação regenerada: **15 slides** inspecionados. Validadores aprovaram
  integridade, geometria, fontes Arial e reimportação pelo artifact-tool.
  SHA-256 do PPTX: `c0e255066eb6fe19284e6541059d355b8799a40183c212a1e8c6634ebfba8c8e`.
- **Nove diagramas Mermaid** atuais renderizados sem erro. Matriz, DDD,
  atributos de qualidade e estado da implementação alinhados aos testes.
- Artefatos oficiais em `output/`; imagens e recibos de QA locais em `tmp/`
  e `.codex-finalizer/`. Publicação e vínculos externos pertencem à T21.
- Limites preservados: enunciado específico Localiza ausente, premissas de
  negócio e equipe a validar; sem alegar infraestrutura externa comprovada.

## Verificação histórica em 27/09/2026

- `PYTHONPATH=src .venv/Scripts/python -m pytest -q tests -p no:cacheprovider`: **18 testes aprovados**, um aviso de depreciação de Starlette/AnyIO. Inclui reserva → contrato → fatura → pagamento simulado; chamado → resolução → workflow; segredo do modo público; idempotência, reconciliação e proteção RLS no modo PostgreSQL.
- `cd web && npm run build`: TypeScript e Vite concluídos sem erro, com `web/dist` gerado. Falta testar a interface no serviço HTTPS público.
- Inspeção local em navegador na mesma origem `http://127.0.0.1:8000/`: tela de acesso, painel e formulário CRM renderizaram; cadastro de cliente sintético apareceu na lista após escrita na API. A API respondeu `UP` em `/health/ready`. O teste HTTPS público continua pendente.
- `tools/build_report.py`: DOCX regenerado em 27/09/2026. `tools/build_presentation.mjs`: PPTX regenerado; recibo `.codex-finalizer/Apresentacao_Cenario_4.validation.json` mostra integridade, layout e reimportação aprovados. Revisão editorial final e preenchimento da equipe pendentes.
- Jira `ARCH7`: 22 tarefas T01–T22 criadas, com prioridade, data por semana e vínculos de bloqueio. Trello e Notion criados como índices/documentação; não há sincronização automática. Os respectivos IDs estão em `JIRA_SYNC.json`, `TRELLO_SYNC.json` e `NOTION_SYNC.json`.
- GitHub: [PR #2](https://github.com/Roger-Quinelato/projetoAplicado7/pull/2) atualizado com o commit de implementação; [22 issues T01–T22](https://github.com/Roger-Quinelato/projetoAplicado7/issues) criadas como índice, cada uma com link para o Jira. Sete marcos Q1–Q7 e etiquetas de semana, tipo, prioridade e status foram verificados nas issues T01 e T22. O GitHub Project ainda requer autorização do escopo `project`.
- Render e Supabase exigem autenticação do titular nas respectivas contas. Nenhuma URL pública, banco em nuvem ou persistência após reinício foi verificada até esta data.
- O modo público inclui RLS e revogação de acesso Data API `anon`/`authenticated` às tabelas em PostgreSQL. Essa proteção é definida no código e continua pendente de verificação em um projeto Supabase real.
- O [GitHub Actions Verify do PR #2](https://github.com/Roger-Quinelato/projetoAplicado7/actions/runs/36366105937) concluiu com sucesso em checkout limpo: suíte Python, instalação e build do frontend, e build da imagem Docker. Isso valida a construção, sem substituir o teste do serviço publicado.

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

## Execução da sprint Q3 em 29 de setembro de 2026 (T06–T09)

Ambiente: contêiner Linux, Python 3.11.15, SQLite local e Node para o build da interface. Estes resultados acrescentam evidências às execuções anteriores, sem substituí-las.

- Suíte automatizada: 57 testes aprovados com `PYTHONPATH=src python -m pytest -q tests -p no:cacheprovider`.
- Contratos: `python tools/export_openapi.py --check` confirmou o OpenAPI sincronizado com `app.openapi()`. O OpenAPI 3.1 passou no `openapi-spec-validator`, todas as respostas 2xx JSON têm exemplo e todos os erros usam `application/problem+json`.
- Eventos: o AsyncAPI descreve seis eventos (`CustomerUpdated.v1`, `ContractActivated.v1`, `ContractClosed.v1`, `TicketOpened.v1`, `TicketEntitlementReconciled.v1` e `TicketResolved.v1`). Os exemplos e os envelopes gravados na outbox durante os fluxos foram validados contra os schemas com `jsonschema`.
- Migrações: `upgrade head` em banco vazio não mostrou divergência entre migrações e modelos. O SQL gerado para PostgreSQL foi inspecionado no modo offline do Alembic, sem banco PostgreSQL real.
- Smoke HTTP com `uvicorn` e `curl`: cliente, reserva, rascunho a partir da reserva, ativação, despacho, encerramento e novo despacho; `GET /api/v1/operations/{correlationId}` mostrou `ContractActivated.v1` e `ContractClosed.v1` publicados e a auditoria de cada etapa; e-mail duplicado retornou `409` em `application/problem+json` com o mesmo `correlationId`.
- Desempenho local: `scripts/performance_smoke.py` mediu p95 de 5,74 ms em 200 consultas de prontidão.
- Interface: `npm run build` concluído.
- Não executado neste ambiente: `docker build` (sem daemon Docker no contêiner; o GitHub Actions executa o build) e qualquer verificação no Render/Supabase.
