---
name: archcorp-entrega
description: >
  Use ao concluir (ou interromper) uma tarefa de implementação no ArchCorp, para provar os critérios
  de aceite com o menor conjunto suficiente de verificações e devolver ao coordenador o pacote de
  entrega no formato do protocolo. Também para tarefas só de verificação.
---

# Entrega ao coordenador

## 1. Prove e pare

- Converta cada critério de aceite do registro em uma verificação concreta (teste, comando,
  leitura do banco). Uma verificação por alegação; não repita a mesma suíte sem motivo.
- Rode primeiro o foco (teste da tarefa, arquivo do contexto), depois o portão exigido no registro
  (ex.: suíte completa em SQLite; PostgreSQL só se a afirmação depender dele).
- Classifique cada resultado com precisão: **passou**, **falhou**, **não executado** (motivo) ou
  **bloqueado** (o que falta). Skip relevante é informado, nunca omitido.
- Quando todos os critérios estiverem provados, **pare**: sem polimento, limpeza ou testes extras
  fora do escopo.

## 2. Pacote de entrega (formato fixo)

```markdown
## Entrega — <id da tarefa>

Estado: concluída | parcial | bloqueada
SHA de base: <sha>   Commit entregue: <sha ou "não commitado">

### Resumo
<o que mudou e por quê, em 2–4 linhas>

### Arquivos alterados
- caminho — motivo

### Critérios de aceite
| Critério | Evidência | Resultado |
|---|---|---|

### Comandos executados
| Comando | Ambiente | Resultado |
|---|---|---|
(incluir a execução do teste de regressão contra a base, com a mensagem de falha)

### Resposta aos achados  (só em rodada de correção)
| # | Achado | Ação | Prova ou motivo |
|---|---|---|---|

### Limitações e riscos
- sítios irmãos não corrigidos, skips, premissas, o que não foi verificado

### Perguntas ao coordenador
- decisões que dependem de escopo ou de negócio
```

## 3. Regras do pacote

- O pacote é uma **alegação** para o revisor, que vai reproduzi-la. Escreva só o que um comando ou
  arquivo comprova; números de teste vêm da saída real, não de estimativa.
- Não cole segredo, token ou dado sensível em comando ou saída; use `<REDACTED>`.
- Evidência de outro SHA não vale para este: refaça ou declare.
- Estado "concluída" só com todos os critérios provados e nenhum teste relevante falhando.
- Interrompeu por escopo, ambiguidade ou ambiente indisponível? Estado "bloqueada", com o motivo e
  o que destravaria.
