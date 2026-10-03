# Revisão cruzada (Onda 2): Agente 2 sobre A1-01, A1-02 e A1-04

Revisão feita em 2026-10-01, por volta de 20:55 UTC, somente em modo leitura. Nada foi escrito em Jira, GitHub ou Trello. A referência auditada é `3a3d8bd`, na cópia `$SP/iso`. Usei os textos extraídos pelo Agente 1 (`$SP/agente1/relatorio.txt` e `guia.txt`). O SHA-256 do DOCX foi conferido: `740de917…1966`, idêntico ao de E1-21.

---

## A1-01 — T01–T05 marcadas como "Concluído" sem atender ao critério de aceite

**Veredito: CONFIRMADO COM AJUSTE.** Severidade que eu atribuiria: **média** (o Agente 1 atribuiu alta).

### Evidência própria

**Jira.** Consultei via Atlassian Rovo `searchJiraIssuesUsingJql`, site `projetooaplicado6.atlassian.net`, com a JQL `project = ARCH7 AND key in (ARCH7-1..ARCH7-5)` e os campos status, resolution, updated, comment e description.

| Issue | Status | Resolução | Atualizada em | Comentário mais recente |
|---|---|---|---|---|
| ARCH7-1 | "Concluído" (categoria done) | `null` | 29/09 13:39:36 -03 | 13:29:21 -03: "Revisão do professor permanece pendente, conforme o critério da issue; não marcado como concluído." |
| ARCH7-2 | "Concluído" | `null` | 29/09 13:39:37 -03 | 13:29:22 -03: "a issue segue em revisão" |
| ARCH7-3 | "Concluído" | `null` | 29/09 13:44:33 -03 | 13:43:40 -03: "issue preservada em revisão" |
| ARCH7-4 | "Concluído" | `null` | 29/09 13:44:34 -03 | 13:43:42 -03: "issue preservada em revisão" |
| ARCH7-5 | "Concluído" | `null` | 29/09 13:44:57 -03 | 13:43:44 -03: "issue preservada em andamento para revisão/aprovação do conjunto" |

- A descrição de ARCH7-1 diz: "Critério: cinco contextos e exclusões documentados; revisão docente pendente."
- Todos os comentários são da conta do titular do repositório. **Não há nenhum comentário, ata ou link de revisão docente.**

**GitHub.** Consultei via `list_issues` (estado fechado) e `issue_read get_comments`.
- As issues #4–#8 estão fechadas, com o rótulo `status:concluido`, e foram atualizadas em 29/09 entre 16:54:07Z e 16:54:25Z.
- Comentários da #4:
  - 16:50Z: "segue Em andamento no Jira porque a revisão docente continua pendente … fechar a sprint não conclui a revisão pendente".
  - 16:53Z: "o Jira agora mostra ARCH7-1 como Concluído … Sincronizei esta issue para Concluído e fechei-a".
- Comentário da #8, 16:53Z: "Espelho o status Concluído".

**Repositório.**
- `docs/CRONOGRAMA_EXECUCAO.md:40-44` mantém T01–T04 "Em revisão" e T05 "Em andamento".
- A linha 64 do mesmo arquivo diz: "`Concluído` exige link para artefato e verificação".
- `docs/BACKLOG_TASKS_SUBTASKS.md:11` mantém aberta a "Subtask 1.5 Validar premissas com professor".
- `MODELO_COMUM_ARCHCORP.md:20` diz: "Uma tarefa só é concluída com evidência vinculada".

### Confirmações
- As cinco issues estão como "Concluído" sem resolução e contradizem comentários do próprio autor feitos 5 a 10 minutos antes.
- GitHub e Trello (E1-32, não reconsultado por mim) foram fechados "por espelhamento", sem evidência nova.

### Ajustes
1. **A exigência de revisão do professor só é explícita para T01.** O critério de T01 contém "revisão do professor pendente". T05 diz "Aprovar …", mas não diz quem aprova; há aprovação formal só para a parte de arquitetura (ADR-001 "Aceito para o protótipo", decisores = equipe). Os critérios de T02, T03 e T04 não exigem revisão docente. Para essas três, a regra geral ("link para artefato e verificação") está parcialmente atendida: cada issue do Jira tem links para os artefatos e uma verificação documental. A violação é forte para T01 e T05 e mais fraca, de status inconsistente, para T02–T04.
2. **A causa da transição não foi determinada.** O histórico de mudanças do Jira não foi consultado. O comentário GitHub das 16:50Z diz que ARCH7-1 "segue Em andamento", mas o campo `updated` do Jira já é 16:39Z. Não dá para dizer se a mudança foi manual ou efeito colateral do fechamento da sprint. Registro isso como inconclusivo, sem atribuir intenção.
3. **Por que média e não alta.** O efeito é de governança e de rastreabilidade, não de produto. A fonte canônica no repositório (CRONOGRAMA) mantém o status correto, e a correção é trivial (reabrir as issues e espelhar). A regra NUNCA do `AGENT.md` ("marque uma entrega como concluída sem atender aos critérios deste guia") é violada nas ferramentas externas, o que justifica não rebaixar para baixa.

**Divergências com o Agente 1:** a severidade e a generalização da exigência de revisão docente a T02–T04. Os fatos estão corretos.

---

## A1-02 — Relatório técnico com erros factuais e contradições internas

**Veredito: CONFIRMADO.** Severidade: **alta** (concordo).

### Evidência própria
- **§1.1 (`relatorio.txt:11`).** Diz "A Localiza recebeu a tarefa de modernizar uma organização…" e cita [1] = "ARCHCORP. Plano de Execução e Cronograma Detalhado" (`:310`).
  - `guia.txt:26` diz "A ArchCorp contratou vocês como uma equipe júnior…".
  - `guia.txt:77` diz "Cenário 4 – Empresa de serviços", com CRM, Sistema de contratos, Sistema financeiro, Sistema de atendimento e Sistema de gestão de processos.
  - `grep -c Localiza guia.txt` dá 0, e o `Guia.pdf` não aparece nas referências.
  - O texto atribui a demanda a quem não a fez. A adaptação ao domínio Localiza é escolha da equipe (missão em `AGENT.md`), não fato do enunciado.
- **§6.2 (`relatorio.txt:185`).** Diz "O protótipo simula tokens OIDC". Contra isso:
  - `src/archcorp/security.py:11-34` tem apenas um dicionário fixo `TOKEN_ROLES` com tokens `demo-*`, ou um segredo único comparado por `compare_digest` que concede todos os papéis. Não há JWT, emissor, claims nem fluxo OIDC.
  - Contradiz também a §12.3 do próprio relatório (`:307`: "não oferece OIDC") e `ESTADO_IMPLEMENTACAO.md:13`.
  - A mesma frase está em `docs/arquitetura/TO_BE.md` ("O adaptador local simula tokens OIDC") e no gerador `tools/build_report.py:296`. A correção precisa abranger os três lugares.
- **§8 (`relatorio.txt:233`).** Diz "A operação preserva o contador acumulado; uma nova falha retorna imediatamente a FAILED".
  - Isso contradiz a §12.3 (`:307`: "o reprocessamento reinicia o contador de tentativas").
  - O código confirma a §12.3 e refuta a §8: `src/archcorp/main.py:553-554` audita `previousAttempts` e em seguida faz `event.attempts = 0`. Como o despachante só marca `FAILED` com `attempts >= retry_limit` (`integration/service.py:40`), uma nova falha deixa o evento `PENDING` com `attempts = 1`, não `FAILED`.
  - O teste `tests/test_flows.py` (bloco `test_falha_permanente…`) afirma `event.attempts == 0`.
  - Na minha execução E2-12 a auditoria registrou `{'previousAttempts': 3}`.
- **Desatualização.** O DOCX é do commit `6702804` (27/09), anterior a `3a3d8bd` (29/09). Os erros persistem no entregável atual.

### Ajuste e complemento
- O complemento não altera o veredito: a §8 também diverge do ADR-001, regra 12.
- O relatório (`:302`) afirma que "reprocessamento manteve rastreabilidade" e "repetição não duplicou cobrança". Pelos meus achados, isso só vale nos caminhos sequenciais. A2-01, A2-03 e A2-05 mostram cenários de falha e concorrência em que a afirmação geral não se sustenta. Esse ponto é um reforço, não uma divergência.

**Justificativa da severidade alta:** é o entregável principal avaliado, contradiz o enunciado na primeira seção, contradiz o código e se contradiz internamente.

---

## A1-04 — Matriz de rastreabilidade marca como "Atendido" itens inexistentes

**Veredito: CONFIRMADO COM AJUSTE.** Severidade: **média** (o Agente 1 atribuiu alta).

### Evidência própria
A matriz é `docs/MATRIZ_RASTREABILIDADE.md` (último commit `3a3d8bd`, 29/09), sem coluna de data ou commit por linha.

- **SEC-01 (`:35`).** Requisito "OIDC/OAuth 2.0, papéis e privacidade". Estado: "**Atendido no escopo simulado; sem OIDC**".
- **OBS-01 (`:36`).** Requisito "Logs, métricas, traces e health checks". Estado: "**Atendido; trace distribuído representado pela correlação no monólito**".
  - `ESTADO_IMPLEMENTACAO.md:13-14` diz "Sem OIDC/OAuth" e "Sem tracing distribuído". `AGENT.md:3` trata ambos como metas.
- **DOC-01 (`:31`).** "Sete blocos Mermaid renderizados sem erro e figuras do relatório inspecionadas" → "Atendido". Verifiquei por conta própria: `unzip -p output/Relatorio_Tecnico_Cenario_4.docx word/document.xml` tem 0 ocorrências de `<w:drawing>`, `<w:pict>` e `<v:imagedata>`, e há 0 arquivos em `word/media/`. **O relatório não tem figuras.** O PPTX também não tem nenhum arquivo em `media/`.
- **DOC-03/DOC-04 (`:33-34`).** "Atendido; regenerar após revisão Localiza". Os arquivos são do commit `6702804` (27/09), anteriores a T06–T09. O próprio texto admite que é preciso regenerar.

### Ajustes
1. **SEC-01 e OBS-01 não afirmam que OIDC ou tracing existem.** As duas linhas declaram a ausência na mesma célula ("sem OIDC"; tracing "representado pela correlação"). O problema é o rótulo "Atendido" aplicado a um requisito cujo título é OIDC ou traces. Isso superestima a cobertura e conflita com o espírito da regra NUNCA do `AGENT.md`, mas não é uma alegação falsa de implementação. Classifico como divergência documental que induz a erro, não como afirmação falsa.
2. **DOC-01 é o caso mais grave da matriz.** Cita uma verificação ("figuras do relatório inspecionadas") cujo objeto não existe.
3. **Complemento a partir dos meus achados.** Outras linhas "Atendido" também estão superestimadas:
   - **DOC-02 (`:32`)** e **INTEROP-01 (`:22`)**: 11 de 261 exemplos OpenAPI são inválidos contra o próprio schema, e o `Money` do AsyncAPI rejeita 19,99 (A2-08, A2-09).
   - **RF-05 (`:15`)** e **RF-07 (`:17`)**: um reprocessamento sobrescreve a projeção mais nova, e um erro de banco nunca chega a `FAILED` (A2-03, A2-01).
   - **RF-06 (`:16`)**: sem teste automatizado. Confirmo E1-07: `grep "operations/" tests/` só encontra a verificação de presença no OpenAPI.

### Por que média e não alta
A matriz é um artefato de conferência, não o entregável avaliado. O `ESTADO_IMPLEMENTACAO.md`, referenciado no topo da própria matriz, declara corretamente os limites, e SEC-01 e OBS-01 trazem a ressalva no texto. Sobe para alta se a matriz for anexada à entrega sem correção, porque DOC-01 cita uma inspeção inexistente.

**Divergências com o Agente 1:**
- A severidade.
- A leitura de SEC-01 e OBS-01: as linhas não "marcam como atendido itens inexistentes", marcam como atendido com ressalva explícita.
- A lista do Agente 1 deve ser ampliada com DOC-02, INTEROP-01, RF-05 e RF-07.

---

## Resumo

| Achado | Veredito | Severidade do Agente 1 → minha | Motivo do ajuste |
|---|---|---|---|
| A1-01 | Confirmado com ajuste | alta → média | Exigência docente explícita só em T01 (e "aprovação" em T05); T02–T04 têm links e verificação documental; a causa da transição não foi determinada |
| A1-02 | Confirmado | alta → alta | — (o código confirma: `attempts = 0` em `main.py:554`; `security.py` sem OIDC) |
| A1-04 | Confirmado com ajuste | alta → média | SEC-01 e OBS-01 trazem ressalva explícita; DOC-01 sem figuras confirmado; acrescentar DOC-02, INTEROP-01, RF-05, RF-07 e RF-06 |
