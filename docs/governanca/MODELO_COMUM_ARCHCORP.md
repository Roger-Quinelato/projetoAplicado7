# Modelo comum de demandas da ArchCorp

Adaptação do `modelo-comum.md` enviado por Roger. Atualizado em 27/09/2026.

| Dimensão | Valores usados | Aplicação |
|---|---|---|
| Tipo | Épico/quinzena, tarefa, subtarefa, compromisso | As 22 demandas são tarefas. O Jira `ARCH7` não disponibilizou Epic na configuração criada; Q1–Q7 são agrupamentos de planejamento, não épicos Jira fingidos. |
| Prioridade | Crítica, alta, normal, baixa, a confirmar | High e Medium no Jira representam alta e normal. Prioridade não é status. |
| Status | Entrada, planejado, pronto, em andamento, aguardando, em revisão, concluído, cancelado | O Jira disponível tem pendente, em andamento e concluído; revisão e aguardando permanecem descritos no item e no Trello, sem equivalência perfeita. |
| Tempo | Sem prazo, prazo de entrega, evento com início e fim | Cada T01–T22 tem prazo interno por semana. Não foram criados eventos de Calendar. |

## Registro principal e vínculos

- Demanda técnica: Jira `ARCH7-n`, com dependências `blocks` e prazo. O catálogo T01–T22 no repositório mantém a origem e as regras de aceite.
- Contexto e decisões: Notion, páginas filhas da frente ArchCorp.
- Arquivo oficial: pasta ArchCorp no Drive universitário.
- Índice visual: cartões Trello com link Jira. GitHub Project, se habilitado, deve conter os mesmos links, sem tarefa independente.
- Cada índice informa o ID principal e a data da conferência. Sem automação verificada, a atualização é manual.

Uma tarefa atrasada só vira crítica mediante avaliação do impacto e do prazo; não existe urgência automática por estar em S1–S3. Uma tarefa só é concluída com evidência vinculada, inclusive URL HTTPS para o deploy.
