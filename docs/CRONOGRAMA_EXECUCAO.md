# Cronograma executável e catálogo de demandas — ArchCorp

Atualizado em 27/09/2026. O projeto é um protótipo acadêmico conceitual para o Cenário 4 (Localiza). A data de início de S1 foi fixada em 04/09/2026 para converter as 14 semanas e 7 quinzenas do cronograma da ArchCorp em datas de trabalho. Essas datas são metas internas, sujeitas à validação com a disciplina. Nenhum item desta tabela atesta operação em sistemas reais da empresa.

## Fontes e responsabilidade

- Cronograma visual enviado: Q1 a Q7, semanas S1 a S14, módulos de escopo, requisitos/AS-IS, TO-BE, APIs, protótipo, empreendedorismo/qualidade, relatório e entrega.
- Plano de Execução e Cronograma Detalhado da ArchCorp: estrutura de 14 semanas e entregáveis acadêmicos.
- `modelo-comum.md`: **tipo**, **prioridade**, **status** e **tempo** são campos independentes. Prioridade não define status.
- Jira é o registro principal das demandas técnicas, dependências e aceite. Notion registra contexto e decisões; Drive guarda arquivos oficiais. Trello e as [22 GitHub Issues](https://github.com/Roger-Quinelato/projetoAplicado7/issues) são índices com link para o Jira. O GitHub Project depende da autorização do escopo `project`. Não há sincronização automática entre eles.
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

| ID | Semana | Demanda e critério de aceite | Prioridade | Status em 27/09 | Dependência |
|---|---|---|---|---|---|
| T01 | S1 | Fixar escopo acadêmico, cinco contextos, exclusões e premissas Localiza; revisão do professor pendente | Alta | Em revisão | — |
| T02 | S2 | Mapear atores, dados e fluxos F1–F3; sinalizar hipótese versus fato do enunciado | Alta | Em revisão | T01 |
| T03 | S3 | Consolidar PRD, RF/RNF, aceites mensuráveis e matriz de rastreabilidade | Alta | Em revisão | T02 |
| T04 | S3 | Desenhar AS-IS conceitual com duplicidades e riscos, sem alegar acesso real | Normal | Em revisão | T02 |
| T05 | S4 | Aprovar TO-BE modular, ADR, DDD/TDD, segurança e propriedade de dados | Alta | Em andamento | T03,T04 |
| T06 | S5 | Versionar OpenAPI e AsyncAPI com todos endpoints/eventos e exemplos válidos | Alta | Em andamento | T05 |
| T07 | S5 | Definir dados sintéticos, identificadores globais, migração aditiva e contrato de erro | Alta | Em andamento | T05 |
| T08 | S6 | Completar CRM: clientes, contatos e oportunidades, validação e autorização | Alta | Em andamento | T06,T07 |
| T09 | S6 | Completar reservas/contratos: reserva, rascunho, ativação idempotente e encerramento | Alta | Em andamento | T06,T07 |
| T10 | S7 | Entregar frontend navegável nos cinco contextos, com estados e feedback de erros | Alta | Em andamento | T08,T09 |
| T11 | S7 | Demonstrar F1 cliente → reserva → contrato sem recadastro | Alta | Em andamento | T08,T09,T10 |
| T12 | S8 | Completar financeiro: fatura, pagamento simulado e inadimplência por vencimento | Alta | Em andamento | T09 |
| T13 | S8 | Demonstrar F2 ativação → cobrança + preparação; reentrega sem duplicação | Alta | Em andamento | T09,T12 |
| T14 | S8 | Revisar viabilidade e empreendedorismo: custos zero, limites e evolução comercial | Normal | Planejado | T05 |
| T15 | S9 | Completar atendimento: abertura, SLA, responsável, resolução e reconciliação | Alta | Em andamento | T09 |
| T16 | S9 | Completar workflow: processos, tarefas, prazos, responsáveis e transições; demonstrar F3 | Alta | Em andamento | T15 |
| T17 | S10 | Endurecer demo pública: segredo, papéis, dados sintéticos, logs e falhas recuperáveis | Alta | Em andamento | T10,T16 |
| T18 | S10 | Validar qualidade: testes de integração/contrato, acessibilidade, desempenho e evidências | Alta | Planejado | T13,T16,T17 |
| T19 | S11 | Atualizar todos os documentos técnicos, relatório e slides conforme implementação | Alta | Em andamento | T18 |
| T20 | S12 | Publicar app/API em Render Free com Supabase Free; testar URL HTTPS e persistência real | Alta | Planejado | T17,T18 |
| T21 | S12 | Criar Jira, Trello, Notion, Drive e GitHub Project; publicar tickets, decisões e arquivos oficiais com links cruzados | Alta | Em andamento | T03,T19 |
| T22 | S13–S14 | Revisar entrega com professor, preencher nomes/contribuições, ensaiar e submeter pacote final | Alta | Aguardando | T19,T20,T21 |

## Regras de conclusão

- `Concluído` exige link para artefato e verificação; código local isolado não comprova deploy.
- Serviço externo gratuito só é considerado publicado depois de URL HTTPS aberta, `GET /health/ready` positivo, frontend acessível, teste de escrita/leitura após reinício e revisão de segredos.
- O protótipo não emite cobrança real nem integra frota, PSP, CRM, ERP ou ITSM da Localiza.
- Bloqueios externos conhecidos: validação docente; contas Render/Supabase; GitHub Project depende da permissão da conta; nomes e contribuições da equipe.
- Próxima ação após cada semana: atualizar Jira, conferir links nos índices, registrar evidência no repositório/Drive e ajustar o status sem inferir conclusão pelo calendário.
