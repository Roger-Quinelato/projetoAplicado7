---
name: archcorp-pr
description: >
  Use ao escrever ou atualizar a descrição de um PR do ArchCorp (pelo coordenador, depois da
  revisão): resumo visual mínimo, evidência antes/depois, perigo do merge, SHA revisado e limitações.
---

# Descrição de PR no ArchCorp

A descrição representa **o diff final**, não a intenção inicial. Reescreva-a quando o conteúdo
mudar; descrição antiga com SHA ou estado de outro momento é achado de revisão (Q-13).

## Modelo

```markdown
## Resumo
<uma frase de intenção + o menor visual que mostre a mudança>

## Tarefa
<id, issue/achado, registro da tarefa>

## Evidência
- **Antes:** <teste falhando na base / saída> 
  **Depois:** <mesmo teste passando / saída>
| Verificação | Ambiente | Resultado |
|---|---|---|

## Perigo do merge
**Porta:** mão única | mão dupla
**Raio de impacto:** <uma palavra> — <consumidores, dados ou fluxos afetados>

## Revisão
Parecer automatizado (archcorp-revisao) para <HEAD_SHA>: <veredito>. Não substitui aceite humano.

## Limitações
- …

🤖 Generated with [Claude Code](https://claude.com/claude-code)  ← só quando aplicável
```

## Seções

- **Resumo:** escolha uma só forma visual, a menor que torna o ponto claro: árvore de chamadas
  (fluxo entre contextos), `diff` de árvore de arquivos (refatoração), `diff` de máquina de estados
  (transições), diagrama Mermaid de sequência (eventos e outbox). Sem preâmbulo.
- **Evidência:** execução vale mais que descrição. Mostre o teste de regressão falhando na base e
  passando no head. Interface alterada: captura de tela quando o ambiente permitir.
- **Perigo do merge:** porta de mão única = difícil de desfazer (migração que contrai dados,
  mudança de contrato publicado, dado apagado). Porta de mão dupla = reverter o commit basta.
  Raio de impacto considera contextos, consumidores do contrato, interface web e os fluxos F1–F3.
- **Revisão:** identifique o parecer como automatizado e o SHA a que se refere. Commit posterior
  invalida o parecer.
- **Limitações:** o que não foi executado (ex.: PostgreSQL local, navegador), sítios irmãos fora do
  escopo, premissas. Nada de "pronto para produção" sem a evidência do gate público
  (`archcorp-seguranca`, seção 4).

Use a linguagem de domínio do projeto (CRM, reserva, contrato, fatura, chamado, processo) e
português do Brasil.
