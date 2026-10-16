---
name: archcorp-implementacao
description: >
  Use ao implementar uma tarefa recebida do coordenador no ArchCorp: correção de bug, funcionalidade
  nova, refatoração ou rodada de correção após revisão. Define escopo, modo de trabalho, o que conta
  como slop e os limites do papel de implementador.
---

# Implementação no ArchCorp

Você implementa **uma tarefa** descrita num registro (objetivo, escopo, critérios de aceite,
verificações exigidas, SHA de base). O registro é a especificação; regras gerais estão em
`AGENTS.md`. Conhecimento de arquitetura fica em `.agents/skills/archcorp-*` (leia pelo caminho
quando o gatilho da tarefa pedir; ver `docs/agentes/IMPLEMENTADOR.md`).

## 1. Antes de editar

- Releia o registro. Liste em uma linha cada critério de aceite e cada exclusão.
- Confirme o SHA de base e que o diretório de trabalho está limpo ou com mudanças conhecidas.
- Se a tarefa for ambígua, contraditória com `AGENTS.md`/ADR ou exigir decisão de negócio: **pare e
  devolva a pergunta**. Não escolha em silêncio.
- Identifique o dono da regra (`archcorp-fronteiras-e-dominio`). A mudança vai para a menor camada
  que possui o comportamento incorreto ou ausente.

## 2. Escolha o modo

| Modo | Quando | Regra central |
|---|---|---|
| **Correção** | Comportamento errado | Reproduzir antes (`archcorp-diagnostico`); teste que falha na base (`archcorp-tdd`); mudar a camada responsável; nada além disso |
| **Funcionalidade** | Comportamento novo | Caminho completo e estreito entre as camadas que possuem as invariantes; reaproveitar a costura existente; sem modos, opções ou configuração que o aceite não pede |
| **Refatoração** | Estrutura muda, comportamento não | Prova antes e depois com os mesmos testes; uma fronteira de propriedade por vez; interfaces públicas, ordem e falhas preservadas; nenhuma funcionalidade junto |
| **Rodada de correção** | Achados da revisão | Responder a **cada** achado numerado: corrigido (com prova), não corrigido (com motivo) ou discordância fundamentada. Não reabrir o que foi aceito; não ampliar escopo |

## 3. Corrija a classe, não só o caso

Quando o defeito vem de um padrão (helper, normalização, cálculo de prazo, validação), procure os
**sítios irmãos** do mesmo padrão. Ou corrija todos com teste em cada um, ou declare no resultado
por que o escopo ficou restrito. Exemplo real: Q-01 corrigiu o prazo de `TICKET_RESOLUTION`, mas o
`ONBOARDING` ainda usa `datetime.now()`; isso precisa estar explícito na entrega.

Mudou um formato compartilhado (payload, campo de resposta, enum)? Enumere **todos** os
consumidores (outros contextos, `web/src/api.ts`, exemplos OpenAPI/AsyncAPI) e confirme cada um.

## 4. Slop é defeito

O diff não pode conter:

- abstração especulativa, opção ou parâmetro sem uso no aceite;
- código morto, comentado ou `TODO`/`FIXME` no lugar de trabalho terminado;
- refatoração ou formatação de código não relacionado;
- exceção engolida, fallback silencioso, log sem contexto;
- teste enfraquecido, removido ou que passa sem exercitar o comportamento;
- texto com cara de gerado (comentário que repete o código, docstring inflada).

Limpe só o que **sua** mudança deixou órfão. Código morto pré-existente: mencione, não remova.
Siga o estilo do arquivo (densidade de comentários, nomes, idioma: negócio em português,
identificadores no padrão existente).

## 5. Documentação na mesma mudança

Comportamento, API, evento ou operação mudou? Atualize no mesmo commit: contratos
(`archcorp-contratos-e-migracoes`), `docs/ESTADO_IMPLEMENTACAO.md` e o que mais a tarefa citar.
Separe implementado de planejado; não afirme o que não verificou.

## 6. Limites do papel

O implementador **não**: faz push, merge, deploy ou fecha issue; publica comentário externo;
delega a outros agentes; altera o registro da tarefa; revisa o próprio trabalho como se fosse o
revisor. Se a tarefa exigir algo fora do escopo (migração, contrato, novo evento, área não
prevista), **interrompa** e devolva o motivo; não redimensione sozinho.

Ao terminar, entregue no formato de `archcorp-entrega`.
