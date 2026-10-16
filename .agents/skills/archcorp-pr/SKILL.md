---
name: archcorp-pr
description: >
  Use ao escrever ou atualizar a descrição de um PR do ArchCorp depois da revisão: intenção,
  evidência adequada ao tipo de tarefa, perigo do merge, SHA revisado e limitações. Não use antes
  de existir parecer para o SHA final.
---

# Descrição de PR no ArchCorp

A descrição representa **o diff final**, não a intenção inicial. Reescreva-a quando o conteúdo
mudar; descrição com SHA ou estado de outro momento é achado de revisão. O utilitário
(`tools/fluxo_archcorp.py`) gera uma versão local a partir dos artefatos da execução; quem publica
é o responsável humano.

## Modelo

```markdown
## Resumo
<uma frase de intenção; visual só se esclarecer>

## Tarefa
<id da execução, issue/achado, registro da tarefa>

## Evidência
| Verificação | Ambiente | Resultado |
|---|---|---|

## Perigo do merge
**Porta:** mão única | mão dupla
**Raio de impacto:** <contextos, consumidores, dados ou fluxos afetados>

## Revisão
Parecer automatizado (archcorp-revisao) para <HEAD_SHA>: <veredito>. Não substitui aceite humano.

## Limitações
- …
```

## Seções

- **Resumo:** comece pela intenção. Acrescente um visual **só quando ele explicar melhor que a
  frase**: árvore de chamadas (fluxo entre contextos), `diff` de árvore de arquivos (refatoração),
  `diff` de máquina de estados (transições) ou Mermaid de sequência (eventos e outbox). Correção
  de texto ou de uma linha não precisa de visual.
- **Evidência** adequada ao tipo:

  | Tipo | Antes/depois |
  |---|---|
  | Correção de bug | Teste de regressão falhando na base e passando no head |
  | Funcionalidade | Teste novo e o comportamento observável |
  | Refatoração | Mesma suíte verde antes e depois |
  | Documentação | Afirmações e links conferidos; sem antes/depois de teste |
  | Interface | Captura de tela quando o ambiente permitir; senão, declare que não foi capturada |

- **Perigo do merge:** mão única = difícil de desfazer (migração que contrai dados, contrato
  publicado alterado, dado apagado). Mão dupla = reverter o commit basta. O raio de impacto
  considera contextos, consumidores do contrato, interface web e os fluxos F1–F3.
- **Revisão:** parecer identificado como automatizado e o SHA a que se refere. Commit posterior
  invalida o parecer.
- **Limitações:** o que não foi executado, sítios irmãos fora do escopo, premissas. Nada de
  "pronto para produção" sem a evidência do gate público (`archcorp-seguranca`, seção 4).

## Acabamento opcional com `humanizer`

Depois de conferir os fatos, a descrição pode passar pela skill externa `humanizer` em **modo
incorporado** (*Embedded mode*: devolve só o texto final). Em seguida, confira de novo contra a
versão anterior: SHAs, números, nomes de testes, ressalvas ("não executado", "não verificado") e
links precisam continuar idênticos. Se a skill não estiver instalada, publique o texto conferido.

Linguagem de domínio do projeto (CRM, reserva, contrato, fatura, chamado, processo), português do
Brasil. Caso que motivou a regra de descrição atualizada:
[`references/historico.md`](references/historico.md).
