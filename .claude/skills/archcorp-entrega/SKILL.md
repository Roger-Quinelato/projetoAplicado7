---
name: archcorp-entrega
description: >
  Use ao concluir, interromper ou bloquear uma rodada de implementação no ArchCorp, para provar os
  critérios de aceite com o menor conjunto suficiente de verificações e devolver ao coordenador a
  entrega no formato do protocolo. Também para tarefas só de verificação.
---

# Entrega ao coordenador

A entrega é uma **alegação** que o revisor vai reproduzir. Contrato:
`docs/agentes/schemas/entrega.schema.json`; quando chamado pelo utilitário, a resposta final é esse
JSON. O commit é criado pelo utilitário depois da entrega: não faça commit.

## 1. Prove e pare

- Converta cada critério de aceite do registro em uma verificação concreta (teste, comando,
  leitura do banco). Uma verificação por alegação; não repita a mesma suíte sem motivo.
- Rode primeiro o foco (teste da tarefa, arquivo do contexto), depois o portão exigido no registro.
  PostgreSQL só quando a alegação depende dele.
- A prova segue o tipo da tarefa (`archcorp-tdd`, seção 2): teste vermelho na base é exigido para
  **correção de bug**; refatoração prova com os mesmos testes antes e depois; documentação, com links
  e afirmações conferidos; verificação, com os comandos executados e nenhum arquivo alterado.
- Classifique cada resultado: `passou`, `falhou`, `nao_executado` (motivo) ou `bloqueado` (o que
  falta). Skip relevante é informado, nunca omitido.
- Com todos os critérios provados, **pare**: sem polimento, limpeza ou testes extras fora do escopo.

## 2. Campos da entrega

| Campo | Conteúdo |
|---|---|
| `estado` | `concluida` (todos os critérios provados, nenhum teste relevante falhando), `parcial` ou `bloqueada` |
| `resumo` | O que mudou e por quê, em 2–4 linhas |
| `arquivos_alterados` | Caminho e motivo de cada arquivo |
| `criterios` | Para cada critério do registro: id, evidência e resultado |
| `comandos` | Comando, ambiente e resultado real (inclui o teste de regressão contra a base, em bug) |
| `resposta_achados` | Só em rodada de correção: cada achado numerado com `corrigido`, `nao_corrigido` ou `discordancia`, e a prova ou o motivo |
| `limitacoes` | Sítios irmãos não corrigidos, skips, premissas, o que não foi verificado, comandos negados por permissão |
| `perguntas` | Decisões de escopo ou negócio; preenchidas quando o estado é `bloqueada` por ambiguidade |

Fora do utilitário, use os mesmos campos como seções Markdown.

## 3. Regras

- Escreva só o que um comando ou arquivo comprova; números de teste vêm da saída real.
- Não cole segredo, token ou dado sensível; use `<REDACTED>`.
- Evidência de outro SHA ou de outra rodada não vale para esta: refaça ou declare.
- Interrompeu por escopo, ambiguidade, permissão negada ou ambiente indisponível: estado
  `bloqueada`, com o motivo e o que destravaria.
