# Levantamento de skills para o fluxo Codex (coordenação e revisão) e Claude (implementação)

Data: 16/10/2026. Autor: Claude Code, a pedido do responsável pelo repositório.

**Natureza deste documento:** insumo para a configuração do fluxo descrito no plano "Codex coordena e revisa; Claude implementa". Nada aqui foi aplicado ao repositório além deste arquivo. As seções 1 e 6 registram fatos verificados; as seções 2 a 5 são **propostas** que dependem de aceite humano e da validação no piloto.

## 1. Fatos verificados que orientam o desenho

| Fato | Fonte | Consequência |
|---|---|---|
| Claude carrega skills de `~/.claude/skills/` (pessoal) e `.claude/skills/` (projeto); com o mesmo nome, **a pessoal vence a do projeto** | [Claude Code: Skills](https://code.claude.com/docs/en/skills) | Uma cópia no repositório com o mesmo nome da pessoal é ignorada na máquina do autor |
| Subagentes do Claude aceitam `skills:` no frontmatter; o **conteúdo completo** é injetado no início, até 32 nomes; skills com `disable-model-invocation: true` não podem ser pré-carregadas; o agente ainda pode invocar outras pelo `Skill` | [Claude Code: Subagents](https://code.claude.com/docs/en/sub-agents) | Pré-carregar só o que vale em toda tarefa; o restante por gatilho |
| A documentação do Claude não menciona `.agents/skills/` | [Claude Code: Skills](https://code.claude.com/docs/en/skills) | Não depender de o Claude descobrir essa pasta sozinho |
| Codex lê skills de `.agents/skills/` (do diretório atual até a raiz do repositório) e de `$HOME/.agents/skills`; skills com o mesmo nome **não se fundem** e ambas aparecem | [Codex: Build skills](https://learn.chatgpt.com/docs/build-skills) | Cópias com nome igual ao das pessoais duplicam o seletor |
| Agentes TOML do Codex (`.codex/agents/`) exigem `name`, `description`, `developer_instructions`; **herdam as skills da sessão principal** e só podem desativá-las com `[[skills.config]] path=... enabled=false` | [Codex: Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) | O perfil do revisor não "anexa" skills; ele desativa as indevidas |
| `agents/openai.yaml` é metadado opcional do Codex (`interface`, `policy.allow_implicit_invocation`, `dependencies.tools`) | [Codex: Build skills](https://learn.chatgpt.com/docs/build-skills) | Pode ser mantido nas cópias; não afeta o Claude |
| Nesta máquina, `~/.claude/skills/<nome>` são *junctions* para `~/.agents/skills/<nome>`; as mesmas ~120 skills estão visíveis para Claude e Codex, inclusive as de implementação | Inspeção local em 16/10/2026 | O revisor do Codex hoje enxerga `implement`, `tdd`, `codenavi` etc. |

**Regra derivada:** toda skill versionada no repositório recebe o prefixo `archcorp-` e é adaptada ao projeto (fonte da especificação, idioma, papéis). Registrar em cada cópia a origem (repositório e caminho) e o autor.

## 2. Estrutura proposta de documentos

| Camada | Arquivo | Leitor | Conteúdo |
|---|---|---|---|
| Documento comum | `AGENTS.md` (renomeado no PR #43) | Codex automaticamente; Claude por `@AGENTS.md` no `CLAUDE.md` | Regras SEMPRE/NUNCA, arquitetura, propriedade dos dados e o **protocolo**: papéis, estados (preparada → implementação → revisão → correção → aprovada; bloqueada), registro da tarefa, critérios de aceite, aprovação válida só para o SHA examinado |
| Especificação do implementador | `docs/agentes/IMPLEMENTADOR.md` | Claude | Responsabilidades e limites, formato da entrega, tabela de gatilhos de skills |
| Especificação do revisor | `docs/agentes/REVISOR.md` | Codex | Eixos da revisão, formato dos achados, critérios de reprovação, tabela de gatilhos |
| Perfil nativo do Claude | `.claude/agents/archcorp-implementer.md` | Claude (`--agent`) | Frontmatter (`tools`, `maxTurns`, `skills:`) e instrução para seguir `IMPLEMENTADOR.md` |
| Perfil nativo do Codex | `.codex/agents/archcorp-reviewer.toml` | Codex | `developer_instructions` curtas apontando para `REVISOR.md` e desativação das skills de implementação |
| Entrada do Claude | `CLAUDE.md` | Toda sessão do Claude | Apenas encaminhamento ao `AGENTS.md`; o papel de implementador fica no perfil, para não se impor fora do fluxo |

Os perfis nativos são finos: o comportamento fica descrito uma única vez, em Markdown legível.

## 3. Onde as skills ficam

| Pasta | Lida por | Conteúdo |
|---|---|---|
| `.claude/skills/archcorp-*` | Claude | Modo de trabalho do implementador, pré-carregado no perfil |
| `.agents/skills/archcorp-*` | Codex | Revisão e conhecimento compartilhado (arquitetura, dados, domínio, segurança) |

O conhecimento compartilhado existe em um só lugar. `IMPLEMENTADOR.md` instrui o Claude a ler `.agents/skills/archcorp-<nome>/SKILL.md` pelo caminho quando o gatilho correspondente ocorrer.

## 4. Implementador (Claude)

### 4.1 Pré-carregadas (modo de trabalho)

| Origem | Cópia proposta | Por quê | Adaptação |
|---|---|---|---|
| `coding-guidelines` | `archcorp-coding-guidelines` | Evita invenção de API, ampliação de escopo e mudanças não pedidas | Nenhuma além do prefixo |
| `surgical-patch` | `archcorp-surgical-patch` | Corrige na camada dona da regra com prova de regressão | Nenhuma |
| `lean-build` | `archcorp-lean-build` | Funcionalidade nova com reaproveitamento, escopo estrito e parada explícita | Nenhuma |
| `migration` | `archcorp-migration` | Alembic, contrato v1 e dados legados com prova de preservação (ADR-002/003) | Citar ADR-002/003 |
| `safe-refactor` | `archcorp-safe-refactor` | Mudança estrutural cercada por verificação | Exigir ADR quando estrutural |
| `investigate-first` | `archcorp-investigate-first` | Hipóteses ranqueadas antes de editar | Nenhuma |
| `verify-and-stop` | `archcorp-verify-and-stop` | Fecha a entrega contra os critérios de aceite | Formato de entrega do protocolo |
| `tdd` | `archcorp-tdd` | Regressão que falha antes da correção | As *seams* vêm do registro da tarefa, não de pergunta ao usuário; `GLOSSARY.md` não existe aqui |

### 4.2 Por gatilho (lidas de `.agents/skills/`)

| Gatilho na tarefa | Skill | Ligação com o projeto |
|---|---|---|
| Fronteira de módulo, porta pública, dono dos dados | `modular-design-principles` | Monólito modular; proibição de acesso a tabelas de outro contexto |
| Regra de negócio, agregado, máquina de estados | `tactical-ddd` | Estados de Contracts/Finance/Support; política de tarefas do Workflow (Q-07) |
| Vocabulário de domínio, decisão estrutural | `domain-modeling`, `create-adr` | Mudança estrutural exige ADR |
| Concorrência, bloqueio, idempotência, ordem de eventos | `ddia-transactions-consensus` | Q-02, Q-03, outbox/inbox |
| Contrato de API/evento, compatibilidade | `ddia-encoding-evolution` | OpenAPI/AsyncAPI v1, Q-04/Q-05 |
| Interface de módulo, *seam* testável | `codebase-design` | Portas que recebem `Session` (ADR-005) |
| Falha difícil ou intermitente | `diagnosing-bugs` | Despacho da outbox |
| Autenticação, segredos, demonstração pública | `security-best-practices` | Q-11, `PUBLIC_DEMO` |
| Edição de `AGENTS.md`/`CLAUDE.md`/skills | `writing-for-agents` | Configuração deste fluxo |

### 4.3 Excluídas do implementador

| Skill | Motivo |
|---|---|
| `implement`, `implement-spec` | Fazem commit e autorrevisão; no plano, revisão e publicação são do Codex. `implement` tem `disable-model-invocation: true` |
| `codenavi` | Grava `.notebook/` no repositório, contrariando "PR contém somente arquivos intencionais" |
| `cavecrew`, `caveman*` | Saída comprimida prejudica o handoff e a documentação em português |
| `code-review`, `caveman-review`, `the-fool` | Papel do revisor; mantê-los fora preserva a independência |
| `tlc-spec-driven`, `to-tickets`, `triage`, `wayfinder` | Planejamento e criação de tickets são papel do coordenador |
| `grilling`, `grill-me` | Entrevistam o usuário, que não participa do ciclo automático |

## 5. Revisor (Codex)

### 5.1 Núcleo do revisor

| Origem | Cópia proposta | Por quê | Adaptação |
|---|---|---|---|
| `code-review` | `archcorp-code-review` | Dois eixos separados: **Standards** (padrões documentados, ADRs, contratos e *smells* de Fowler) e **Spec** (conformidade com o pedido) | Especificação vem do registro da tarefa; remover a exigência de `setup-matt-pocock-skills`/tracker; padrões = `AGENTS.md`, ADRs, OpenAPI/AsyncAPI |
| `caveman-review` | incorporada ao formato de `archcorp-code-review` | Formato de achado com local, severidade (🔴 erro, 🟡 risco, 🔵 detalhe, ❓ pergunta), problema e correção | Achados numerados e em português integral |
| `verify-and-stop` | `archcorp-verify-acceptance` | Portão final: cada critério de aceite ligado a evidência do SHA revisado | Recusar evidência de outro SHA |
| `the-fool` | `archcorp-challenge` | Pré-mortem do plano da tarefa antes de acionar o Claude; detectar teste que passa pelo motivo errado | Restringir a plano de tarefa e evidência |

### 5.2 Por gatilho na revisão

| Gatilho no diff | Skill | Pergunta do revisor |
|---|---|---|
| Fronteira de módulo, import entre contextos | `modular-design-principles` | Algum módulo acessou tabela, classe interna ou repositório de outro? |
| Regra de negócio, estado, agregado | `tactical-ddd` | A regra ficou no módulo proprietário? |
| Regra semelhante em dois módulos | `component-common-domain-detection` | A integração passou a ser dona de regra de negócio? |
| Bloqueio, transação, idempotência, ordem | `ddia-transactions-consensus` | O teste prova concorrência ou só repetição sequencial? |
| OpenAPI/AsyncAPI, schema, migração | `ddia-encoding-evolution` | A v1 continua compatível? A exceção está em ADR? |
| Novas dependências entre módulos | `coupling-analysis` (a mais extensa) | O acoplamento cresceu sem justificativa? |
| Autenticação, segredos, `PUBLIC_DEMO`, RLS | `security-best-practices`, `security-threat-model` | Há exposição de dado sensível ou proteção enfraquecida? |
| Documentação alterada | `docs-writer` | Cada afirmação está ligada a evidência? Há contradição com `ESTADO_IMPLEMENTACAO.md`? |
| `AGENTS.md`/`CLAUDE.md`/skills alterados | `writing-for-agents` | A instrução é ambígua ou duplicada? |
| Redação do corpo do PR (publicação) | `pr` (nova no upstream, não instalada) | A descrição representa o diff final? |

### 5.3 Desativar no perfil do revisor

| Skills | Motivo |
|---|---|
| `implement`, `implement-spec`, `tdd`, `surgical-patch`, `lean-build`, `safe-refactor`, `migration`, `codenavi` | O revisor não corrige o código entregue |
| `cavecrew`, `caveman*` | Compressão prejudica o feedback que o Claude precisa ler |
| `twg-code-review` | Depende do contexto Atlassian TWG e publica no Bitbucket |
| `grilling`, `grill-me`, `triage`, `to-tickets` | Entrevistam o usuário ou dependem do tracker configurado por `setup-matt-pocock-skills`; o registro de tarefa do protocolo os substitui |
| `chief-of-staff` (nova no upstream, não instalada) | Coordena subagentes de forma persistente; a auditoria de 16/10 recomenda não implementar coordenador automatizado permanente |

A desativação usa caminho absoluto (`C:\Users\roger\.agents\skills\<nome>\SKILL.md`). O piloto deve confirmar que o revisor não as enxerga.

## 6. Atualização das skills de Matt Pocock (16/10/2026)

- **Origem:** `mattpocock/skills`, instaladas em 13/09/2026 pelo CLI `skills` (vercel-labs), registradas em `~/.agents/.skill-lock.json`.
- **Backup prévio:** as 37 pastas e o lock em `C:\Users\roger\.agents\skills-backup-mattpocock-20261016`.
- **Comando:** `npx skills update <37 nomes> -g -y`, executado a partir de `$HOME` para não atingir o escopo do projeto.
- **Resultado:** 20 atualizadas; 17 já atualizadas. Por serem *junctions*, a atualização vale para Claude e Codex.
- **Removida no upstream:** `resolving-merge-conflicts`; o CLI a manteve instalada (modo não interativo).
- **Novas no upstream, não instaladas:** `pr` ("Use when writing a PR body") e `chief-of-staff` ("Pursue a long-running goal in a single session by co-ordinating subagents").

Mudanças relevantes para este levantamento (diff contra o backup):

| Skill | Mudança | Efeito no plano |
|---|---|---|
| `code-review` | Busca no repositório todos os arquivos de padrão de código; referência ao tracker ficou genérica; subagentes chamados juntos em primeiro plano | Encontra `AGENTS.md` e ADRs sem adaptação; a dependência de tracker ainda exige ajuste na cópia |
| `tdd` | `CONTEXT.md` → `GLOSSARY.md`; cada *seam* proposta ganha nota do que detecta e do que não detecta | Continua perguntando ao usuário; a adaptação de 4.1 permanece necessária |
| `domain-modeling` | `CONTEXT.md` → `GLOSSARY.md` (`CONTEXT-FORMAT.md` substituído por `GLOSSARY-FORMAT.md`) | Se adotada, o glossário do projeto seria `GLOSSARY.md` |
| `implement` | Busca o ticket no tracker antes de começar; chama `tdd` e `code-review` pelo `Skill` | Reforça a exclusão: continua acoplando implementação e autorrevisão |
| Demais (16) | Ajustes de redação ou de arquivos auxiliares (`wizard/template.sh`, `setup-matt-pocock-skills/*`) | Sem efeito nas recomendações |

## 7. Perfil de carga: só o pacote do projeto (verificado em 16/10/2026)

Implementado por [`tools/perfil_skills.py`](../../tools/perfil_skills.py) a partir de [`pacote-skills.json`](pacote-skills.json); origem e licença das skills de referência em [`ORIGEM_SKILLS.md`](ORIGEM_SKILLS.md).

| Ferramenta | Mecanismo | Evidência |
|---|---|---|
| Claude Code (sessão no repositório) | `python tools/perfil_skills.py` grava `.claude/settings.local.json` (ignorado pelo Git) com `skillOverrides: "off"` para as skills pessoais fora da lista, `syncClaudeAiPlugins`/`syncClaudeAiSkills: false` e `enabledPlugins` restrito | `claude -p` perguntando as skills disponíveis: **282** fora do repositório, **19** dentro (3 do projeto, 4 de `document-skills`, 12 internas do Claude Code). Os plugins sincronizados da conta deixaram de aparecer |
| Claude Code (worktree ou execução automática) | `claude --settings .claude/perfil-archcorp.json`, o mesmo conteúdo gerado | Arquivo gerado pelo mesmo comando; uso pelo utilitário a validar no piloto |
| Codex (por invocação) | `codex exec -c "<saída de --codex-inline>"`, sem alterar `~/.codex/config.toml` | codex-cli 0.163.0, medido sem chamar o modelo com `codex debug prompt-input`: **119 → 15** skills no prompt (7 do projeto + 8 de plugins do Codex: `documents`, `pdf`, `presentations`, `spreadsheets`, `template-creator`, `visualize`, `computer-use`); prompt de 30,5 KB → 13,9 KB |

O Codex varre `~/.agents/skills`, `~/.codex/skills` e `~/.codex/skills/.system` **recursivamente**: sub-skills (ex.: `research/grounded-citations`) e cópias aninhadas também aparecem. O gerador considera isso. Os plugins do Codex não são afetados por `skills.config`.

Limitação no Windows: o valor completo tem cerca de 10,5 mil caracteres. Pelo atalho `codex.cmd`, o `cmd.exe` recusa com "Linha de comando muito longa" (limite de 8.191). Chamar `node <instalação>\node_modules\@openai\codex\bin\codex.js` diretamente funciona. O utilitário deve usar essa forma, com argumentos em lista e sem shell.

Ainda não verificado: a configuração de projeto `.codex/config.toml` (o projeto *trusted* no Codex é `C:\ProjetoAplicado7`, não este clone) e o `[[skills.config]]` dentro de `.codex/agents/*.toml`.

## 8. Pontos para validação no piloto

1. O Claude reconhece `archcorp-implementer` e as skills pré-carregadas (verificar o aviso de skill ausente no log de debug).
2. O revisor do Codex não enxerga as skills desativadas.
3. Nenhuma skill `archcorp-*` colide com nome pessoal.
4. A leitura por caminho das skills de `.agents/skills/` pelo Claude funciona no diretório de trabalho da tarefa.
