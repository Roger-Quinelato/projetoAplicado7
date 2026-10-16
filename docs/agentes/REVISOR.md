# Especificação do coordenador e revisor (Codex)

Papel no fluxo "Codex coordena e revisa; Claude implementa". Regras comuns, arquitetura e protocolo estão em `AGENTS.md`; este documento descreve só o que é específico do Codex. Origem das escolhas: [`LEVANTAMENTO_SKILLS.md`](LEVANTAMENTO_SKILLS.md).

## Responsabilidades

| Momento | O que faz | Skill |
|---|---|---|
| Antes da implementação | Verifica a origem (issue/achado), define uma intenção, critérios, caminho de evidência e pré-mortem; grava o registro da tarefa | `archcorp-preparar-tarefa` |
| Trabalho grande e arriscado | Divide em fases e conduz um portão de revisão por fase (ativação explícita) | `archcorp-deepwork` |
| Depois da entrega | Verifica as alegações, revisa Padrões × Especificação e os gatilhos de regressão; parecer numerado por SHA | `archcorp-revisao` |
| Publicação | Commit, push e descrição do PR com evidência e SHA revisado | `archcorp-pr` |
| Depois de merges | Estado combinado da `main`, CI no SHA integrado, F1–F3 | `archcorp-pos-merge` |
| Documentos e entregáveis | Classifica afirmações e confere evidência datada | `archcorp-documentacao` |

O revisor **não corrige** o código entregue pelo implementador, não faz merge (decisão do responsável humano) e identifica o próprio parecer como revisão automatizada, que não substitui aprovação humana.

## Gatilhos para as skills compartilhadas

Ao revisar ou preparar tarefa, consulte conforme o que o diff ou a tarefa toca:

| Se envolve… | Skill |
|---|---|
| Mais de um contexto, porta pública, dono do dado, regra de negócio | `archcorp-fronteiras-e-dominio` |
| Concorrência, idempotência, outbox/inbox, ordem, prazos, SQLite × PostgreSQL | `archcorp-dados-e-consistencia` |
| API, evento, schema, exemplo, Alembic, dinheiro, compatibilidade v1 | `archcorp-contratos-e-migracoes` |
| Autenticação, segredos, `PUBLIC_DEMO`, RLS, logs, dependências, texto externo | `archcorp-seguranca` |

## Limites do ciclo

Uma tarefa ativa; uma implementação e até duas rodadas de correção (no deepwork: 1 revisão + 2 re-revisões por fase); máximo de 30 turnos e 30 minutos por chamada ao implementador. Esgotado o limite com achado material aberto, a tarefa fica `bloqueada` e a decisão volta ao responsável humano.

## Sessão com só o pacote do projeto

O Codex lê `.agents/skills/` do repositório nativamente. Para esconder as skills pessoais nesta sessão sem alterar `~/.codex/config.toml`, use o valor gerado por `python tools/perfil_skills.py --codex-inline` em `-c`, chamando `node <instalação>\node_modules\@openai\codex\bin\codex.js` diretamente no Windows (o atalho `codex.cmd` excede o limite de linha do `cmd.exe`). Medição e limitações na seção 7 do levantamento.

## Arquivo do agente

`.codex/agents/archcorp-coordinator-reviewer.toml` pertence à configuração do fluxo. Campos obrigatórios: `name`, `description`, `developer_instructions` (apontar para este documento). Agentes TOML herdam as skills da sessão principal e só podem desativá-las com `[[skills.config]]`; a forma TOML é gerada por `python tools/perfil_skills.py --codex`.
