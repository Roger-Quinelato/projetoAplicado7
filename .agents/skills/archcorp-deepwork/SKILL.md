---
name: archcorp-deepwork
description: >
  Use como coordenador só para trabalho grande e arriscado no ArchCorp: várias fases dependentes,
  mudança de fronteira ou de arquitetura, migração que não pode ficar pela metade, ou correção de
  integridade que exige caracterização antes. Não use para correção pontual, documentação ou
  mudança limitada a um contexto.
---

# Deepwork no ArchCorp

O coordenador vira **escalonador**: divide o trabalho em fases, prepara cada fase como tarefa e
conduz cada uma pelo **mesmo ciclo** do protocolo (`docs/agentes/PROTOCOLO.md`): implementação,
entrega, revisão por SHA, até duas correções. Ele **não escreve código**.

## 1. Ativação

Ative só se pelo menos dois forem verdadeiros: fases com dependência real entre si; mudança de
fronteira, contrato ou esquema; risco de integridade que precisa ser caracterizado antes da
correção; entrega parcial perigosa. Caso contrário, tarefa comum (`archcorp-preparar-tarefa`).
Mexer em vários arquivos, sozinho, não justifica deepwork. Exemplos do repositório em
[`references/historico.md`](references/historico.md).

## 2. Planejamento

- Fases pequenas, cada uma com **um resultado válido por si** (um commit que não quebra a `main`),
  em ordem: a fase N parte do commit aprovado da fase N-1.
- Cada fase recebe um registro de tarefa completo, com o próprio caminho de evidência.
- Risco de integridade: a primeira fase **caracteriza** o problema com um teste que o reproduz. Use
  PostgreSQL quando a alegação depender de propriedades dele (bloqueio, `skip_locked`, isolamento,
  limites numéricos, migração); SQLite basta para o resto.
- Pesquisa necessária (biblioteca, comportamento do banco) é registrada **antes** da revisão, com
  fonte primária, para o revisor não repetir a descoberta.

## 3. Execução

Com `tools/fluxo_archcorp.py`, o deepwork é um registro com `modo: deepwork` e a lista de fases; o
utilitário executa as fases em sequência e guarda o progresso em `.agentes/execucoes/<id>/`
(ignorado pelo Git). Sem o utilitário, mantenha o mesmo registro em `.agentes/deepwork/<slug>.md`.

Por fase:

1. Implementador com o registro da fase, num worktree exclusivo; ninguém mais escreve nele.
2. Entrega (`archcorp-entrega`) e commit local criado pelo utilitário.
3. Fase que muda fronteira, direção de dependência ou local de arquivo: revisão consulta
   `archcorp-fronteiras-e-dominio` e os testes de arquitetura.
4. Revisão (`archcorp-revisao`) em sessão separada, declarando `Fase N — tentativa M de 3`.

## 4. Portão por fase

- 1 revisão + até 2 re-revisões. Re-revisão prioriza achados não resolvidos e riscos introduzidos
  pela correção; **não reabre** achados aceitos ou resolvidos.
- Esgotadas as tentativas com achado material aberto: fase **bloqueada**; o responsável humano
  decide entre aceitar o risco, mudar o escopo ou autorizar revisão extra.
- Fase aprovada: só então a próxima.

## 5. Conclusão

Revisão final **integrada** da combinação das fases (base da primeira até o commit da última),
procurando interações entre fases. Ela não é pós-merge: `archcorp-pos-merge` só vale depois de
integração efetiva na `main`. Resumo final: fases, commits, pareceres por SHA, riscos aceitos e o
que ficou fora.
