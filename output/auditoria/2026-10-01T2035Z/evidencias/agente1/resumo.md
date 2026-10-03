# Resumo — Agente 1 (requisitos, progresso e entregas)

Referência: `main` = `3a3d8bd`. Data: 01/10/2026 (último dia de S4). Consultas externas entre 20:37 e 20:44 UTC, somente leitura. Arquivos: `evidencias.md` (E1-01..E1-36), `achados.md` (A1-01..A1-17), `matriz_parcial.md`, `render/` (PDFs e PNGs gerados de cópias; originais com SHA-256 inalterado).

## Conclusões principais

1. **O enunciado disponível é só o `Guia.pdf`** (ArchCorp, Cenário 4 "Empresa de serviços", sem Localiza). O PDF "Localiza" que o `AGENT.md:39` aponta como fonte nº 1 não existe no repositório e não foi encontrado no Drive nem no Notion (E1-01, E1-03). A Localiza é uma contextualização da equipe; REQUISITOS e AS-IS a marcam como premissa, mas PLANO:52, ADR-001:12, a coluna "Classificacao" do AS-IS e o relatório a apresentam como fato (A1-08).
2. **Fechamento administrativo de T01–T05.** Em 29/09, ao fechar as sprints Jira Q1/Q2, ARCH7-1..5 foram para "Concluído" (sem resolução), minutos depois de comentários que diziam "revisão do professor permanece pendente; não marcado como concluído". GitHub (#4–#8 fechadas) e Trello acompanharam. O repositório continua "Em revisão/Em andamento" (A1-01; E1-29, E1-31).
3. **O relatório técnico é o maior risco acadêmico.** Gerado em 27/09, antes de T06–T09. Afirma que "A Localiza recebeu a tarefa", cita como fonte [1] o plano ArchCorp em vez do guia, diz "simula tokens OIDC" e se contradiz sobre o contador de reprocessamento. Não tem figuras nem integrantes, e a fundamentação está incompleta. Tem 18 páginas Carta, mas só ~2.700 palavras, atingidas com 17 quebras forçadas (A1-02, A1-03, A1-05; E1-21..E1-24).
4. **Matriz de rastreabilidade inflada.** SEC-01 (OIDC), OBS-01 (traces), DOC-01 (figuras) e DOC-03/04 aparecem como "Atendido"; RF-06 não tem teste; a matriz cita "13 testes", enquanto a contagem estática atual é 50 funções e 57 casos (bate com EVIDENCIAS de 29/09). Outros documentos citam 17 e 18 (A1-04, A1-06; E1-04..E1-10).
5. **Documentação desatualizada após `3a3d8bd`.** TO-BE/DDD citam 3 eventos (o AsyncAPI tem 6); CRONOGRAMA e BACKLOG não mudaram; issues T06–T09 abertas apesar do merge do PR #28; ESTADO trata o PR #2 como ativo (A1-05, A1-09).
6. **Auditoria anterior (29/09) não mesclada.** Resolvidos: T-01, T-03, T-11 e parte de C-04/C-05. A maioria dos achados documentais persiste (C-01..C-03, C-06..C-15, C-17) (A1-16; E1-27).
7. **Pontos positivos verificados.** Os 14 testes citados na matriz existem; os RF/RNF têm critérios de aceite; o CI Verify passou em `3a3d8bd` (run #18); Jira, Trello e GitHub têm as 22 tarefas com links cruzados e dependências coerentes; nenhum documento afirma deploy público, OIDC real ou consumo via RabbitMQ como implementados (exceto as formulações "OIDC simulado").

## Conclusão por tarefa

| Tarefa | Classificação | Base |
|---|---|---|
| T01 | Parcial | E1-13, E1-31 (revisão docente sem evidência) |
| T02 | Comprovado (documental) | E1-02, E1-13 |
| T03 | Parcial | E1-05, E1-07, E1-10 |
| T04 | Comprovado (documental) | E1-01, E1-13 |
| T05 | Parcial | E1-11, E1-12, E1-31 (sem aprovação; TO-BE/DDD desatualizados) |
| T14 | Parcial (dentro do prazo) | E1-16 |
| T19 | Não atendido para relatório/slides; parcial para docs técnicos | E1-12, E1-20..E1-25 |
| T21 | Parcial (Jira/Trello/GitHub comprovados; Notion/Drive não verificados; Project pendente) | E1-28..E1-34 |
| T22 | Não atendido (esperado; prazo 10/12) | E1-21, E1-25, E1-30 |

## Achados alta/crítica

- **A1-01** (alta): T01–T05 concluídas nas ferramentas sem o aceite exigido pelo próprio critério.
- **A1-02** (alta): relatório com erros factuais (Localiza/ArchCorp, fonte [1], "OIDC simulado") e contradição sobre o reprocessamento.
- **A1-03** (alta): relatório sem integrantes, figuras, fundamentação completa e densidade de artigo.
- **A1-04** (alta): matriz marca OIDC, traces e figuras inexistentes como "Atendido".

Nenhum achado crítico: não há alegação de integração real com a Localiza nem segredo exposto nos artefatos examinados.

## Limitações

- L-A1-01: enunciado "Localiza" não localizado (repositório, Drive, Notion); comparação feita só com o `Guia.pdf`.
- L-A1-02: os conectores Notion e Drive podem não alcançar as contas citadas na governança (Notion pessoal, Drive universitário); a ausência é limitação de verificação, não prova de inexistência.
- L-A1-03: GitHub Project não verificado (GraphQL indisponível na sessão).
- L-A1-04: changelog do Jira não consultado; horários de transição inferidos do campo `updated` e dos comentários.
- L-A1-05: paginação medida no LibreOffice 24.2 (instalei writer/impress no contêiner); o Word pode diferir.
- L-A1-06: nenhuma URL pública encontrada, então nenhum GET de `/health/*` foi feito.
- L-A1-07: a suíte não foi executada (regra do briefing); contagem estática 50/57.
- L-01 (briefing): a branch `execucao-tarefas-pendentes`/`3fdb533` não pôde ser auditada.
- A1-17 não procede: o diretório `output/auditoria/2026-10-01T2035Z` foi criado pelo coordenador de propósito.
