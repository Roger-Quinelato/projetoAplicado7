---
name: archcorp-deepwork
description: >
  Use como coordenador só para trabalho grande e arriscado no ArchCorp: várias fases dependentes,
  mudança de fronteira ou de arquitetura, migração que não pode ficar pela metade, ou correção de
  integridade que exige experimento antes (ex.: Q-02 ativação concorrente, Q-07 política de
  Workflow). Não use para correção pontual, documentação ou mudança limitada a um contexto.
---

# Deepwork no ArchCorp

O coordenador vira **escalonador**: divide o trabalho em fases, prepara cada fase como tarefa,
aciona o implementador, conduz o portão de revisão e registra o progresso. Ele **não escreve
código**.

## 1. Ativação

Ative só se pelo menos dois forem verdadeiros: fases com dependência real entre si; mudança de
fronteira, contrato ou esquema; risco de integridade que precisa ser caracterizado antes da
correção; entrega parcial perigosa. Caso contrário, use uma tarefa comum
(`archcorp-preparar-tarefa`). Mexer em vários arquivos, sozinho, não justifica deepwork.

## 2. Arquivo de progresso

Crie `.agentes/deepwork/<slug>.md` (pasta ignorada pelo Git; confira o `.gitignore` antes). Ele é o
estado de trabalho, não entregável. O resumo revisado de cada fase vai para a descrição do PR.

Conteúdo mínimo:

```markdown
# Deepwork <slug>
Objetivo: …    SHA de base: …    Branch: …
## Fases
| # | Objetivo | Depende de | Estado | Commit | Tentativas de revisão |
## Decisões e pesquisa aceitas
## Riscos abertos
## Registro por fase
### Fase N — <objetivo>
Arquivos alterados · evidência da validação · decisão ou risco a revisar · parecer (SHA) · resultado
```

## 3. Planejamento

- Fases pequenas, cada uma com **um resultado válido por si** (pode virar commit sem quebrar a
  `main`). A primeira fase de um risco de integridade é **caracterizar**: teste que reproduz o
  problema em PostgreSQL antes de qualquer correção.
- Cada fase recebe um registro de tarefa completo (`archcorp-preparar-tarefa`), com o caminho de
  evidência da fase.
- Pesquisa necessária (biblioteca, comportamento do PostgreSQL) é feita e registrada **antes** do
  portão, com fonte primária, para o revisor não repetir a descoberta.

## 4. Execução de uma fase

1. Acionar o implementador (`archcorp-implementer`) com o registro da fase; um implementador por
   fase, num diretório exclusivo; nenhum outro processo escreve nos mesmos arquivos.
2. Receber a entrega (`archcorp-entrega`) e rodar a validação do caminho de evidência.
3. Fase que muda fronteira, direção de dependência ou local de arquivo: conferir
   `archcorp-fronteiras-e-dominio` e os testes de arquitetura antes do portão.
4. Atualizar o arquivo de progresso e passar ao portão.

## 5. Portão de revisão por fase

- Revisão com `archcorp-revisao`, em contexto separado do planejamento da fase.
- Cada pedido de revisão declara a tentativa: `Fase N — revisão, tentativa 2 de 3 (1 restante)`.
- **1 revisão inicial + até 2 re-revisões.** Re-revisão só quando a correção mudou a decisão
  revisada ou quando um achado não pôde ser verificado com evidência focada; não gaste re-revisão em
  ajuste mecânico já provado.
- Na re-revisão: priorizar achados não resolvidos e riscos introduzidos pela correção; **não
  reabrir** achados aceitos ou resolvidos.
- Esgotadas as tentativas com achado material aberto: fase **bloqueada**. Registre o risco e peça
  ao responsável humano uma decisão: aceitar o risco, mudar o escopo ou autorizar revisão extra.
- Aprovada: commit focado da fase (feito pelo coordenador, segundo o protocolo) e só então a
  próxima fase.

## 6. Conclusão

Validação final do conjunto (portão completo da CI, incluindo PostgreSQL quando aplicável),
`archcorp-pos-merge` se várias fases forem integradas, e resumo final no PR: fases, commits,
pareceres por SHA, riscos aceitos e o que ficou fora.
