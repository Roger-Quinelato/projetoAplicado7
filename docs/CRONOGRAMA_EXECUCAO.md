# Cronograma executável e catálogo de demandas — ArchCorp

Criado em 27/09/2026 e atualizado em 22/10/2026 com os pacotes C a G do plano de conclusão (#59 a #63) e o redesenho da Visão geral (#67). O projeto é um protótipo acadêmico conceitual para o Cenário 4 (Localiza). A data de início de S1 foi fixada em 04/09/2026 para converter as 14 semanas e 7 quinzenas do cronograma da ArchCorp em datas de trabalho. Essas datas são metas internas, sujeitas à validação com a disciplina. Nenhum item desta tabela atesta operação em sistemas reais da empresa.

## Fontes e responsabilidade

- Cronograma visual enviado: Q1 a Q7, semanas S1 a S14, módulos de escopo, requisitos/AS-IS, TO-BE, APIs, protótipo, empreendedorismo/qualidade, relatório e entrega.
- Plano de Execução e Cronograma Detalhado da ArchCorp: estrutura de 14 semanas e entregáveis acadêmicos.
- `modelo-comum.md`: **tipo**, **prioridade**, **status** e **tempo** são campos independentes. Prioridade não define status.
- Jira é o registro principal das demandas técnicas, dependências e aceite. Notion registra contexto e decisões; Drive guarda arquivos oficiais. Trello e as [22 GitHub Issues](https://github.com/Roger-Quinelato/projetoAplicado7/issues) são índices com link para o Jira. As issues usam sete marcos Q1–Q7 e etiquetas independentes para tipo, prioridade, status e semana. O GitHub Project depende da autorização do escopo `project`. Não há sincronização automática entre eles.
- Sem nome dos integrantes, atribuições permanecem sem responsável. A contribuição individual será registrada antes da submissão.

## Quinzenas e semanas

| Quinzena | Semana | Período | Ênfase da imagem | Resultado verificável |
|---|---|---|---|---|
| Q1 | S1 | 04–10/09 | Definição de escopo | Escopo e premissas documentados |
| Q1 | S2 | 11–17/09 | Definição de escopo | Catálogo inicial e critérios de aceite |
| Q2 | S3 | 18–24/09 | Requisitos e AS-IS | RF/RNF e AS-IS com premissas marcadas |
| Q2 | S4 | 25/09–01/10 | TO-BE inicia | Arquitetura e decisões revisadas |
| Q3 | S5 | 02–08/10 | TO-BE e APIs | Contratos REST/eventos versionados |
| Q3 | S6 | 09–15/10 | APIs e protótipo | Fundação, CRM, reservas e contratos |
| Q4 | S7 | 16–22/10 | Protótipo e mockups | Interface e F1 demonstráveis |
| Q4 | S8 | 23–29/10 | Protótipo; empreendedorismo/qualidade | F2, financeiro e viabilidade |
| Q5 | S9 | 30/10–05/11 | Protótipo; empreendedorismo/qualidade | F3, atendimento e workflow |
| Q5 | S10 | 06–12/11 | Empreendedorismo/qualidade | Segurança, observabilidade e falhas |
| Q6 | S11 | 13–19/11 | Relatório e slides | Testes, evidências e relatório revisados |
| Q6 | S12 | 20–26/11 | Relatório e slides | Demo pública e documentação sincronizada |
| Q7 | S13 | 27/11–03/12 | Entrega final | Revisão técnica/acadêmica e simulação |
| Q7 | S14 | 04–10/12 | Entrega final | Pacote final, integrantes e apresentação |

Semanas transcorridas não significam conclusão: cada demanda abaixo depende de evidência. Trabalho incompleto de S1–S3 foi trazido para S4, preservando a semana de origem.

## Demandas canônicas

Cada linha é uma **tarefa** (tipo), salvo os agrupamentos Q1–Q7, que serão **épicos**. `A confirmar` evita prioridade inventada. O prazo é data de entrega interna, não reserva de agenda.

| ID | Semana | Demanda e critério de aceite | Prioridade | Status | Dependência |
|---|---|---|---|---|---|
| T01 | S1 | Fixar escopo acadêmico, cinco contextos, exclusões e premissas Localiza; revisão do professor pendente | Alta | Concluído ([#4](https://github.com/Roger-Quinelato/projetoAplicado7/issues/4), 29/09/2026) | — |
| T02 | S2 | Mapear atores, dados e fluxos F1–F3; sinalizar hipótese versus fato do enunciado | Alta | Concluído ([#5](https://github.com/Roger-Quinelato/projetoAplicado7/issues/5), 29/09/2026) | T01 |
| T03 | S3 | Consolidar PRD, RF/RNF, aceites mensuráveis e matriz de rastreabilidade | Alta | Concluído ([#6](https://github.com/Roger-Quinelato/projetoAplicado7/issues/6), 29/09/2026) | T02 |
| T04 | S3 | Desenhar AS-IS conceitual com duplicidades e riscos, sem alegar acesso real | Normal | Concluído ([#7](https://github.com/Roger-Quinelato/projetoAplicado7/issues/7), 29/09/2026) | T02 |
| T05 | S4 | Aprovar TO-BE modular, ADR, DDD/TDD, segurança e propriedade de dados | Alta | Concluído ([#8](https://github.com/Roger-Quinelato/projetoAplicado7/issues/8), 29/09/2026) | T03,T04 |
| T06 | S5 | Versionar OpenAPI e AsyncAPI com todos endpoints/eventos e exemplos válidos | Alta | Concluído ([PR #28](https://github.com/Roger-Quinelato/projetoAplicado7/pull/28); [#9](https://github.com/Roger-Quinelato/projetoAplicado7/issues/9) fechada em 17/10/2026) | T05 |
| T07 | S5 | Definir dados sintéticos, identificadores globais, migração aditiva e contrato de erro | Alta | Concluído ([PR #28](https://github.com/Roger-Quinelato/projetoAplicado7/pull/28); [#10](https://github.com/Roger-Quinelato/projetoAplicado7/issues/10) fechada em 17/10/2026) | T05 |
| T08 | S6 | Completar CRM: clientes, contatos e oportunidades, validação e autorização | Alta | Concluído ([PR #28](https://github.com/Roger-Quinelato/projetoAplicado7/pull/28); [#11](https://github.com/Roger-Quinelato/projetoAplicado7/issues/11) fechada em 17/10/2026) | T06,T07 |
| T09 | S6 | Completar reservas/contratos: reserva, rascunho, ativação idempotente e encerramento | Alta | Concluído ([PR #28](https://github.com/Roger-Quinelato/projetoAplicado7/pull/28); [#12](https://github.com/Roger-Quinelato/projetoAplicado7/issues/12) fechada em 17/10/2026) | T06,T07 |
| T10 | S7 | Entregar frontend navegável nos cinco contextos, com estados e feedback de erros | Alta | Concluído ([PR #31](https://github.com/Roger-Quinelato/projetoAplicado7/pull/31); [#13](https://github.com/Roger-Quinelato/projetoAplicado7/issues/13) fechada em 17/10/2026; riscos residuais na [#34](https://github.com/Roger-Quinelato/projetoAplicado7/issues/34)) | T08,T09 |
| T11 | S7 | Demonstrar F1 cliente → reserva → contrato sem recadastro | Alta | Concluído ([PRs #33](https://github.com/Roger-Quinelato/projetoAplicado7/pull/33) e [#50](https://github.com/Roger-Quinelato/projetoAplicado7/pull/50); [#14](https://github.com/Roger-Quinelato/projetoAplicado7/issues/14) fechada em 17/10/2026; ADR-006 aguarda aceite) | T08,T09,T10 |
| T12 | S8 | Completar financeiro: fatura, pagamento simulado e inadimplência por vencimento | Alta | Em revisão (20/10: integridade monetária e encerramento em UTC no pacote D, [#60](https://github.com/Roger-Quinelato/projetoAplicado7/issues/60); cancelamento de fatura pela interface no pacote E, [#61](https://github.com/Roger-Quinelato/projetoAplicado7/issues/61); [#15](https://github.com/Roger-Quinelato/projetoAplicado7/issues/15) aberta) | T09 |
| T13 | S8 | Demonstrar F2 ativação → cobrança + preparação; reentrega sem duplicação | Alta | Em revisão (17/10: `scripts/demo_f2.py` 14/14; 20/10: F2 pela interface com PostgreSQL e RabbitMQ reais no pacote F, [#62](https://github.com/Roger-Quinelato/projetoAplicado7/issues/62); [#16](https://github.com/Roger-Quinelato/projetoAplicado7/issues/16) aberta) | T09,T12 |
| T14 | S8 | Revisar viabilidade e empreendedorismo: custos de serviço, implementação e operação, limites e evolução comercial | Normal | Em revisão (20/10: pacote G, [#63](https://github.com/Roger-Quinelato/projetoAplicado7/issues/63) fechada, [PR #72](https://github.com/Roger-Quinelato/projetoAplicado7/pull/72); premissas aguardam validação docente; [#17](https://github.com/Roger-Quinelato/projetoAplicado7/issues/17) aberta) | T05 |
| T15 | S9 | Completar atendimento: abertura, SLA, responsável, resolução e reconciliação | Alta | Em revisão (14/10; 20/10: replay e histórico preservados no pacote D, [#60](https://github.com/Roger-Quinelato/projetoAplicado7/issues/60); [#18](https://github.com/Roger-Quinelato/projetoAplicado7/issues/18) aberta) | T09 |
| T16 | S9 | Completar workflow: processos, tarefas, prazos, responsáveis e transições; demonstrar F3 | Alta | Em revisão (17/10: `scripts/demo_f3.py` 15/15 e prazo do PR #42; 20/10: estados finais, auditoria e prazo de 72 h pelo `occurredAt` no pacote C, [#59](https://github.com/Roger-Quinelato/projetoAplicado7/issues/59); F3 pela interface no pacote F; [#19](https://github.com/Roger-Quinelato/projetoAplicado7/issues/19) aberta) | T15 |
| T17 | S10 | Endurecer demo pública: segredo, papéis, dados sintéticos, logs e falhas recuperáveis | Alta | Em andamento (20/10: feedback e negativa `403` por papel no pacote E; falha do broker e reprocessamento sem duplicar efeitos no pacote F; falta a demonstração pública da T20) | T10,T16 |
| T18 | S10 | Validar qualidade: testes de integração/contrato, acessibilidade, desempenho e evidências | Alta | Em andamento (20/10: aceite integrado local no pacote F, [PR #71](https://github.com/Roger-Quinelato/projetoAplicado7/pull/71): 246 testes com PostgreSQL e RabbitMQ reais, 22 roteiros de navegador, axe bloqueante, p95 até 45,1 ms; falta a URL pública) | T13,T16,T17 |
| T19 | S11 | Atualizar todos os documentos técnicos, relatório e slides conforme implementação | Alta | Em andamento (pacote I, [#65](https://github.com/Roger-Quinelato/projetoAplicado7/issues/65); 20/10: DOCX regenerado; o PPTX versionado ainda mostra números de 17/10; 22/10: documentos sincronizados com a `main`; faltam nomes da equipe e o resultado da T20) | T18 |
| T20 | S12 | Publicar app/API em Render Free com Supabase Free; testar URL HTTPS e persistência real | Alta | Planejado (pacote H, [#64](https://github.com/Roger-Quinelato/projetoAplicado7/issues/64); depende de contas e segredos do provedor) | T17,T18 |
| T21 | S12 | Criar Jira, Trello, Notion, Drive e GitHub Project; publicar tickets, decisões e arquivos oficiais com links cruzados | Alta | Em andamento (pacote J, [#66](https://github.com/Roger-Quinelato/projetoAplicado7/issues/66)) | T03,T19 |
| T22 | S13–S14 | Revisar entrega com professor, preencher nomes/contribuições, ensaiar e submeter pacote final | Alta | Aguardando (pacote J, [#66](https://github.com/Roger-Quinelato/projetoAplicado7/issues/66); último acompanhamento em 09/11/2026 e apresentação final em 23/11/2026) | T19,T20,T21 |

### Plano de conclusão (pacotes A–J)

Em 19/10/2026, as tarefas restantes foram fatiadas em pacotes executáveis, registrados como issues. Cada pacote é um recorte das tarefas T e não as substitui: a T só muda de status quando a própria issue for aceita.

| Pacote | Issue | Tarefas | Estado em 22/10/2026 |
|---|---|---|---|
| A · Consolidar a base preservando comportamento | [#58](https://github.com/Roger-Quinelato/projetoAplicado7/issues/58) | T05, T07, T18, T19 | Aberta; exige acesso ao checkout local |
| B · Criação ambígua e seleção de clientes | [#34](https://github.com/Roger-Quinelato/projetoAplicado7/issues/34) | T10, T11, T18 | Código na `main` ([PR #57](https://github.com/Roger-Quinelato/projetoAplicado7/pull/57)); issue aberta |
| C · Estados finais, auditoria e prazos do Workflow | [#59](https://github.com/Roger-Quinelato/projetoAplicado7/issues/59) | T16, T18 | Fechada; código na `main` pelo [PR #71](https://github.com/Roger-Quinelato/projetoAplicado7/pull/71) |
| D · Integridade de F2/F3 e convergência de migrações | [#60](https://github.com/Roger-Quinelato/projetoAplicado7/issues/60) | T12, T13, T15, T16, T18 | Fechada; código na `main` pelo PR #71 |
| E · Lacunas da interface e feedback por papel | [#61](https://github.com/Roger-Quinelato/projetoAplicado7/issues/61) | T10, T12, T15, T17, T18 | Fechada; código na `main` pelo PR #71 |
| F · Aceite integrado e operacional local | [#62](https://github.com/Roger-Quinelato/projetoAplicado7/issues/62) | T13, T16, T17, T18 | Fechada ([PR #71](https://github.com/Roger-Quinelato/projetoAplicado7/pull/71)) |
| G · Viabilidade e premissas | [#63](https://github.com/Roger-Quinelato/projetoAplicado7/issues/63) | T14, T22 | Fechada ([PR #72](https://github.com/Roger-Quinelato/projetoAplicado7/pull/72), na `main` pelo PR #71) |
| H · Publicação no Render e no Supabase | [#64](https://github.com/Roger-Quinelato/projetoAplicado7/issues/64) | T20 | Aberta |
| I · Documentos, relatório e slides finais | [#65](https://github.com/Roger-Quinelato/projetoAplicado7/issues/65) | T19 | Aberta; parte entregue no PR #72 |
| J · Vínculos oficiais, ensaio e submissão | [#66](https://github.com/Roger-Quinelato/projetoAplicado7/issues/66) | T21, T22 | Aberta |

O redesenho da Visão geral e a barra global de eventos ([PR #67](https://github.com/Roger-Quinelato/projetoAplicado7/pull/67), 21/10/2026) não pertencem a nenhum pacote; a revisão do PR deixou aberta a [#73](https://github.com/Roger-Quinelato/projetoAplicado7/issues/73) (indicadores contados sobre listagens limitadas a 200 registros), tratada no [PR #74](https://github.com/Roger-Quinelato/projetoAplicado7/pull/74), ainda aberto.

## Pendências registradas

| Origem | Pendência | Gatilho | Escopo |
|---|---|---|---|
| T11 (revisão do CTO em 14/10/2026) | **Tratada em 17/10/2026** (ADR-006, proposto): `ResilientCustomerReader` com prazo total, retentativa limitada a erro transitório, atraso exponencial e jitter; indisponibilidade vira `503` sem efeito | Aceite do ADR-006; conector do CRM fora do processo | Resta o corte por chamada no cliente HTTP quando o conector de rede existir |
| T15 (14/10/2026) | ~~Workflow calcula o prazo de `TICKET_RESOLUTION` com a hora do despacho~~ — corrigido em 16/10/2026 (Q-01 da auditoria de 16/10): processo e tarefa usam o `dueAt` de `TicketOpened.v1`; pendente recebe 24 h provisórias contadas de `openedAt`. Permanece: o responsável atribuído em Support não chega ao processo | T16 | Decidir se a atribuição vira evento (`TicketAssigned.v1`, aditivo) ou consulta |
| T15 (14/10/2026) | Vencimento do SLA só é calculado na leitura; não há alerta nem evento de violação; reconciliação depende de ação do operador | Requisito de alerta ou agendador | Agendador ou consumidor periódico é decisão estrutural (novo processo) e exige ADR |
| T15 (14/10/2026) | ~~Duas migrações `0004` criadas em paralelo a partir de `0003_contract_closing` geram duas cabeças no Alembic~~ — resolvido pela `0005_merge_finance_support`, que converge `0004_finance_lifecycle` e `0004_support_sla_history`; a convergência a partir de banco vazio, da `0003` e de cada `0004` é testada em SQLite e PostgreSQL (pacote D, #60) | — | Não renumerar as migrações |
| PR #67 (21/10/2026) | Indicadores da Visão geral calculados no cliente sobre listagens limitadas a 200 registros | Base com mais de 200 contratos, faturas, chamados ou processos | [#73](https://github.com/Roger-Quinelato/projetoAplicado7/issues/73); proposta de contagem no servidor no [PR #74](https://github.com/Roger-Quinelato/projetoAplicado7/pull/74), aberto |
| Avaliação externa | Pagamento por Mercado Pago Checkout Pro em sandbox | Decisão de ampliar o escopo do financeiro | [#56](https://github.com/Roger-Quinelato/projetoAplicado7/issues/56), aberta; integração externa exige ADR e não é requisito do plano |

## Regras de conclusão

- `Concluído` exige link para artefato e verificação; código local isolado não comprova deploy.
- Serviço externo gratuito só é considerado publicado depois de URL HTTPS aberta, `GET /health/ready` positivo, frontend acessível, teste de escrita/leitura após reinício e revisão de segredos.
- O protótipo não emite cobrança real nem integra frota, PSP, CRM, ERP ou ITSM da Localiza.
- Bloqueios externos conhecidos: validação docente; contas Render/Supabase; GitHub Project depende da permissão da conta; nomes e contribuições da equipe.
- Próxima ação após cada semana: atualizar Jira, conferir links nos índices, registrar evidência no repositório/Drive e ajustar o status sem inferir conclusão pelo calendário.
