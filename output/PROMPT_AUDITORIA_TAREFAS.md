# Prompt para auditoria independente — Projeto Aplicado 7

Atue como auditor independente do projeto em `C:\ProjetoAplicado7`, repositório
`Roger-Quinelato/projetoAplicado7`. Audite cada demanda abaixo e a execução
registrada na branch `execucao-tarefas-pendentes`.

O objetivo é identificar o que existe, onde está, quais critérios são verificáveis
e quais dependem de outras evidências. Não parta da conclusão de que as tarefas
estão corretas, incorretas, completas ou incompletas. Não use mensagens de commit,
nomes de testes, este prompt ou declarações de aceite como prova do comportamento.
Apresente as conclusões somente após examinar evidências reproduzíveis.

## Referências e limites da auditoria

- Base da execução: `3a3d8bd3e059f47e1e2c3201f115b8629cb0a427`, incorporada pelo
  [PR #28](https://github.com/Roger-Quinelato/projetoAplicado7/pull/28).
- Último commit desta execução: `3fdb533`. Confirme o HEAD antes de auditar.
- [PR #29](https://github.com/Roger-Quinelato/projetoAplicado7/pull/29) é uma frente
  separada; confira seu estado e não atribua suas alterações à branch auditada.
- Os 13 commits da execução ainda eram locais no momento deste inventário.
  Confirme o estado atual sem realizar push, merge ou alteração de tickets.
- Jira é o registro principal dos critérios: projeto ARCH7 em
  `https://projetooaplicado6.atlassian.net`. Cada tarefa Tnn corresponde a ARCH7-nn.
- [Trello](https://trello.com/b/dL5CIIpM/archcorp-projeto-aplicado-7-s1-s14) e
  [GitHub Issues](https://github.com/Roger-Quinelato/projetoAplicado7/issues) são
  índices. Compare seus estados com o Jira, sem presumir sincronização.
- Leia `AGENT.md`, `CLAUDE.md`, `PLANO_IMPLEMENTACAO_CENARIO_4.md`,
  `docs/CRONOGRAMA_EXECUCAO.md`, `docs/EXECUCAO_TAREFAS.md`,
  `docs/ESTADO_IMPLEMENTACAO.md` e `docs/MATRIZ_RASTREABILIDADE.md`.
- Trate os registros de execução e evidências como declarações a conferir.
- O projeto é um protótipo acadêmico com dados sintéticos. Diferencie código
  implementado, desenho proposto, integração externa e publicação real.
- `Guia.pdf` está no repositório; o enunciado específico Localiza não foi
  localizado nesta execução. Registre o que isso permite ou impede verificar.
- A auditoria é somente de leitura. Não corrija código, não comite, não publique,
  não altere credenciais e não encerre issues. Se uma ferramenta estiver
  inacessível, registre a limitação sem inventar seu conteúdo.
- Preserve `.claude/worktrees/`, `docs/BENCHMARK_BANCOS_SEMESTRE.md` e
  `docs/PESQUISA_BANCOS_FONTES.md`, preexistentes à execução. O arquivo
  `docs/PUBLICACAO_ENTREGAVEIS.md` pertence ao trabalho ainda sem commit da T21.

## Inventário das issues e locais a examinar

Os caminhos são pontos de entrada para investigação, não prova de atendimento.
Consulte o diff de cada commit para obter a lista integral dos arquivos alterados.
Em toda linha, compare os critérios da issue com a implementação efetiva.

| Tarefa / Jira / GitHub | Assunto | Commit da execução | Onde examinar |
|---|---|---|---|
| T01 / ARCH7-1 / [#4](https://github.com/Roger-Quinelato/projetoAplicado7/issues/4) | Escopo e premissas | Sem commit específico nesta sequência | `PLANO_IMPLEMENTACAO_CENARIO_4.md`, `docs/PRD_LOCALIZA.md`, `docs/REQUISITOS.md`, `Guia.pdf` |
| T02 / ARCH7-2 / [#5](https://github.com/Roger-Quinelato/projetoAplicado7/issues/5) | Atores, dados e fluxos | Sem commit específico nesta sequência | `docs/DDD_LOCALIZA.md`, `docs/arquitetura/AS_IS.md`, `docs/arquitetura/FLUXOS_INTEGRACAO.md` |
| T03 / ARCH7-3 / [#6](https://github.com/Roger-Quinelato/projetoAplicado7/issues/6) | PRD, requisitos e rastreabilidade | Sem commit específico nesta sequência | `docs/PRD_LOCALIZA.md`, `docs/REQUISITOS.md`, `docs/MATRIZ_RASTREABILIDADE.md` |
| T04 / ARCH7-4 / [#7](https://github.com/Roger-Quinelato/projetoAplicado7/issues/7) | AS-IS conceitual | Sem commit específico nesta sequência | `docs/arquitetura/AS_IS.md`, fontes acadêmicas e classificação das premissas |
| T05 / ARCH7-5 / [#8](https://github.com/Roger-Quinelato/projetoAplicado7/issues/8) | TO-BE, ADR, DDD/TDD | Sem commit específico nesta sequência | `docs/arquitetura/TO_BE.md`, `docs/adr/ADR-001-integracao-empresa-de-servicos.md`, `docs/DDD_LOCALIZA.md`, `docs/TDD_LOCALIZA.md`, fronteiras em `src/archcorp/` |
| T06 / ARCH7-6 / [#9](https://github.com/Roger-Quinelato/projetoAplicado7/issues/9) | REST e eventos | `0e98cc5` — alterações documentais | `docs/CRONOGRAMA_EXECUCAO.md`, `docs/EXECUCAO_TAREFAS.md`; implementação de referência em `docs/api/openapi.yaml`, `docs/events/asyncapi.yaml`, `tools/export_openapi.py`, `tests/test_contracts_and_architecture.py` e composição da API |
| T07 / ARCH7-7 / [#10](https://github.com/Roger-Quinelato/projetoAplicado7/issues/10) | Fundação, migrações e dados | `701c028` — alteração do registro | `docs/EXECUCAO_TAREFAS.md`; implementação de referência em `src/archcorp/infrastructure/`, `src/archcorp/errors.py`, `src/archcorp/integration/`, `scripts/seed_sintetico.py`, `tests/test_foundation.py`, ADR-002 |
| T08 / ARCH7-8 / [#11](https://github.com/Roger-Quinelato/projetoAplicado7/issues/11) | CRM | `3ec0cc6` — alteração do registro | `docs/EXECUCAO_TAREFAS.md`; implementação de referência em `src/archcorp/crm/` e `tests/test_crm.py` |
| T09 / ARCH7-9 / [#12](https://github.com/Roger-Quinelato/projetoAplicado7/issues/12) | Reservas e contratos | `bc1bec9` — alteração do registro | `docs/EXECUCAO_TAREFAS.md`; implementação de referência em `src/archcorp/contracts/`, migração `0003_contract_closing.py`, `tests/test_contracts.py`, consumers de `ContractClosed.v1` |
| T10 / ARCH7-10 / [#13](https://github.com/Roger-Quinelato/projetoAplicado7/issues/13) | Interface | `6dba82b` | `web/src/App.tsx`, `web/tests/navigation.spec.ts`, `web/playwright.config.ts`, `web/package.json`, `.github/workflows/verify.yml`, README e registro de execução |
| T11 / ARCH7-11 / [#14](https://github.com/Roger-Quinelato/projetoAplicado7/issues/14) | Fluxo F1 | `5a97ffe` — alteração do registro | `docs/EXECUCAO_TAREFAS.md`; referência em `tests/test_flows.py`, `tests/test_extended_modules.py`, `src/archcorp/crm/`, `src/archcorp/contracts/` e `docs/ROTEIRO_DEMONSTRACAO.md` |
| T12 / ARCH7-12 / [#15](https://github.com/Roger-Quinelato/projetoAplicado7/issues/15) | Financeiro | `626351d` | `src/archcorp/finance/routes.py`, `src/archcorp/finance/service.py`, `tests/test_finance.py`, OpenAPI, TDD, estado, diagrama e registro |
| T13 / ARCH7-13 / [#16](https://github.com/Roger-Quinelato/projetoAplicado7/issues/16) | Fluxo F2 | `5e71349` | `tests/test_flows.py`, `docs/INTEGRACOES.md`, registro; consumers em Finance/Workflow e dispatcher em Integration |
| T14 / ARCH7-14 / [#17](https://github.com/Roger-Quinelato/projetoAplicado7/issues/17) | Viabilidade e empreendedorismo | Sem commit específico nesta sequência | `docs/VISAO_NEGOCIO.md`, `docs/PRD_LOCALIZA.md`, `docs/EVOLUCAO_MANUTENCAO.md` e critérios externos |
| T15 / ARCH7-15 / [#18](https://github.com/Roger-Quinelato/projetoAplicado7/issues/18) | Atendimento | `e4a8649` | `src/archcorp/support/service.py`, `tests/test_support.py`, `docs/INTEGRACOES.md` e registro; restante do módulo Support e fluxo F3 |
| T16 / ARCH7-16 / [#19](https://github.com/Roger-Quinelato/projetoAplicado7/issues/19) | Workflow e F3 | `9988643` | `src/archcorp/workflow/domain.py`, `routes.py`, `service.py`, `tests/test_workflow.py`, OpenAPI, TDD, estado, diagrama e registro |
| T17 / ARCH7-17 / [#20](https://github.com/Roger-Quinelato/projetoAplicado7/issues/20) | Segurança e recuperação | `f5f84b3` | `src/archcorp/integration/service.py`, `src/archcorp/main.py`, `src/archcorp/observability.py`, `src/archcorp/security.py`, `tests/test_dispatch_recovery.py`, `tests/test_demo_credentials.py`, `tests/test_public_database_security.py` e documentos no diff |
| T18 / ARCH7-18 / [#21](https://github.com/Roger-Quinelato/projetoAplicado7/issues/21) | Testes, acessibilidade e desempenho | `c00a076` | `web/src/style.css`, `web/tests/accessibility.spec.ts`, dependências web, README, `docs/EVIDENCIAS_VALIDACAO.md`, registro, suíte `tests/` e `scripts/performance_smoke.py` |
| T19 / ARCH7-19 / [#22](https://github.com/Roger-Quinelato/projetoAplicado7/issues/22) | Documentação e artefatos | `3fdb533` | `tools/build_report.py`, `tools/build_presentation.mjs`, `output/Relatorio_Tecnico_Cenario_4.docx`, `output/Apresentacao_Cenario_4.pptx`, atributos, DDD, estado, evidências, matriz, TO-BE, fluxos e registro |
| T20 / ARCH7-20 / [#23](https://github.com/Roger-Quinelato/projetoAplicado7/issues/23) | Publicação Render/Supabase | Sem commit específico nesta sequência | `render.yaml`, `Dockerfile`, configuração de banco/modo público e evidências de HTTPS, escrita/leitura e persistência após reinício, se disponíveis |
| T21 / ARCH7-21 / [#24](https://github.com/Roger-Quinelato/projetoAplicado7/issues/24) | Ferramentas e vínculos | Sem commit; alterações locais e externas | `docs/PUBLICACAO_ENTREGAVEIS.md`, registries locais `*_SYNC.json`, Jira/Trello/GitHub, portal Notion e arquivos do Drive indicados abaixo |
| T22 / ARCH7-22 / [#25](https://github.com/Roger-Quinelato/projetoAplicado7/issues/25) | Revisão e submissão | Sem commit específico nesta sequência | Critérios da issue, validação docente, nomes/contribuições, ensaio e comprovante de submissão, se disponíveis |

Sequência dos commits nesta execução: T06, T07, T08, T09, T15, T10, T11,
T16, T12, T13, T17, T18, T19. T18 entrou como dependência de T19.
Para T06–T09 e T11, os commits da sequência alteraram registros documentais;
investigue a implementação presente na base e sua origem antes de atribuí-la.

## Fontes externas da T21

- [Portal Notion](https://app.notion.com/p/3e8f8610276981928291ef07ee75adf0?pvs=204).
- [Pasta Drive](https://drive.google.com/drive/folders/1Ml7Zn8tfBxhQLf5uxBxV86LwQzWvq0og).
- [Relatório](https://docs.google.com/document/d/1G--OtVYyRpK1Ia-arq1WCL9KdidMHyl_/edit).
- [Apresentação](https://docs.google.com/presentation/d/1hbEp-8utYBSqlg-li3nTN5iiYQ3vEaCC/edit).
- [Registro de execução publicado](https://drive.google.com/file/d/15I_H9sXgnMGsUfVmFmEvEbhvE4Ut7mtd/view?usp=drivesdk).
- [Índice de publicação e 22 vínculos](https://drive.google.com/file/d/1GBmA4g6Ef92X5TYw0vZLjkzr8vT1FMrt/view?usp=drivesdk).

O registro da execução declara substituição de 13 arquivos técnicos e dois
artefatos no Drive, criação dos dois índices acima, atualização de 13 páginas
técnicas, duas páginas de entrega e do portal Notion. Examine datas, conteúdo,
IDs, permissões e referências. Nas páginas técnicas, a seção de 27/09 foi
preservada como histórico e a seção de 30/09 aponta para o arquivo vigente.
O GitHub Project não havia sido criado nesta execução por ausência do escopo
de acesso no CLI e de sessão autenticada no navegador. Confira o estado atual.

## Procedimento

1. Obtenha os critérios atuais de cada issue e compare com os documentos locais.
   Identifique divergências de escopo sem escolher silenciosamente uma versão.
2. Examine os diffs individuais e o diff acumulado `3a3d8bd..3fdb533`. Relacione
   cada alteração à issue correspondente, incluindo mudanças posteriores que
   afetaram trabalho anterior. Use `git show --stat <commit>` e
   `git show <commit> -- <arquivo>`; registre arquivo, linha e commit.
3. Confira os testes e as regras que exercitam. Reproduza verificações relevantes
   quando o ambiente permitir. A suíte Python usa `tmp/test-archcorp.db` e
   recria tabelas: execute em cópia isolada e não rode processos pytest paralelos
   sobre esse banco. Use as instruções do README para dependências e execução.
4. Para as mudanças de comportamento, verifique se os testes distinguem a base
   anterior da versão alterada. Diferencie teste HTTP, unitário, navegador com
   API simulada, banco SQLite, SQL PostgreSQL offline e infraestrutura real.
5. Examine idempotência completa e registros antigos em Support; centavos,
   saldo, moeda e concorrência em Finance; estados finais, responsáveis, prazos
   e estado agregado em Workflow; transações, inbox/outbox, reprocessamento,
   auditoria e exposição de dados em Integration/HTTP/logs.
6. Na interface, confira formulários, erro/sucesso, envio pendente e navegação.
   Na acessibilidade e desempenho, registre telas, dados, amostras, endpoint,
   ambiente e alcance da medição.
7. Compare documentação, contratos, diagramas, relatório e slides com o código.
   Examine os artefatos renderizados; não considere a existência de um arquivo
   ou recibo suficiente para confirmar conteúdo e layout.
8. O registro declara 84 testes Python, 11 de navegador, build, p95 de prontidão
   de 3,68 ms em 200 amostras SQLite, nove diagramas, 18 páginas e 15 slides.
   Trate esses números como resultados relatados e indique o que reproduziu.
9. Compare a condição técnica com o status administrativo de cada ferramenta.
   Diferencie commit local, branch remota, PR aberto, merge, deploy e encerramento
   da issue. Nenhum desses estados deve substituir evidência do outro.

## Formato da entrega

Produza uma linha para cada uma das 22 issues, incluindo as sem commit específico:

| Issue/Jira | Critério e fonte | Local/commit | Evidência observada | Reprodução e resultado | Divergência ou evidência ausente |
|---|---|---|---|---|---|

Para cada constatação que precise de detalhamento, informe cenário, comportamento
esperado e sua fonte, comportamento observado, arquivo/linha/commit e comando ou
passos de reprodução. Separe fatos observados, declarações documentais e hipóteses.
Use “não verificado” quando faltar acesso ou execução; isso, sozinho, não demonstra
falha. Se o resultado depender de uma interpretação do requisito, explicite-a.

Não use elogios, reprovações genéricas ou um veredito antecipado. A avaliação de
cada critério deve decorrer das evidências apresentadas. Termine listando apenas
as lacunas de evidência e as decisões necessárias para concluir a auditoria,
sem implementar mudanças nem alterar estados externos.
