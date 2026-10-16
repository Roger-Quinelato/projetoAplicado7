# Fluxo automatizado (`tools/fluxo_archcorp.py`)

Operação do ciclo de [`PROTOCOLO.md`](PROTOCOLO.md) por linha de comando: Codex prepara, Claude
implementa, o utilitário cria o commit local, Codex revisa em sessão separada e o ciclo segue por até
duas correções. O resultado é um **ramo local** com commits revisados e uma descrição de PR pronta.
Não há push, PR, merge, deploy nem limpeza automática.

## Pré-requisitos

| Item | Como conferir |
|---|---|
| Git, Node, Codex CLI e Claude Code autenticados | `python tools/fluxo_archcorp.py preflight` (não chama modelos) |
| `requirements-dev.txt` instalado (`jsonschema`, `pyyaml`) | idem |
| Perfil de carga gerado | `python tools/perfil_skills.py` (grava `.claude/perfil-archcorp.json`, ignorado) |
| `.agentes/` ignorado pelo Git | já está no `.gitignore` |

No Windows, o utilitário chama a entrada Node do Codex (`node <npm root -g>\@openai\codex\bin\codex.js`)
porque o `codex.cmd` estoura o limite de linha do `cmd.exe`. Para outro local, defina
`ARCHCORP_CODEX_JS`. Os processos auxiliares não abrem janelas.

## Uso (PowerShell)

```powershell
python tools/fluxo_archcorp.py preflight
python tools/fluxo_archcorp.py run --pedido .\pedido.md --dry-run   # mostra etapas, diretórios e chamadas
python tools/fluxo_archcorp.py run --pedido .\pedido.md             # executa o ciclo
python tools/fluxo_archcorp.py status --execucao <id>
python tools/fluxo_archcorp.py resume --execucao <id>                 # depois de corrigir a causa de uma interrupção
python tools/fluxo_archcorp.py resume --execucao <id> --resposta .\resposta.md
python tools/fluxo_archcorp.py resume --execucao <id> --rodada-extra  # decisão humana após bloqueio
python tools/fluxo_archcorp.py resume --execucao <id> --revisar-novamente  # bloqueio do revisor foi de ambiente
python tools/fluxo_archcorp.py --repo C:\outro\clone status --execucao <id>  # operar outro repositório
```

O pedido é um arquivo UTF-8 em texto livre. Com objetivo e escopo claros, o ciclo segue sozinho;
senão, a execução para em `aguardando_esclarecimento` com as perguntas em
`esclarecimento-<n>.md`. A resposta vira `resposta-<n>.md`, e o registro anterior é preservado.

Códigos de saída: `0` aprovada; `2` aguardando esclarecimento ou bloqueada; `1` interrompida ou erro;
`3` aprovação que não corresponde mais ao ramo (commit alterado depois da revisão).

## O que acontece em cada etapa

| Etapa | Onde | Chamada |
|---|---|---|
| Fixar instruções | `.agentes/execucoes/<id>/instrucoes/` | Cópia de `AGENTS.md`, `docs/agentes/`, skills e perfis no SHA de base, com hash |
| Preparação | worktree `base` (detached na base) | Codex, `--sandbox read-only`, saída `tarefa.schema.json` |
| Implementação | worktree `impl`, ramo `archcorp/<id>` | Claude, `--agent archcorp-implementer` fixado por `--agents`, `--permission-mode acceptEdits`, lista fechada de comandos, saída `entrega.schema.json` |
| Commit | worktree `impl` | Utilitário: confere caminhos proibidos e escopo, `git add -A`, commit com trailer `Archcorp-Tentativa` |
| Verificações do utilitário | worktree `revisao-*` (e `*-prova-base` em correção) | O utilitário executa as `verificacoes_exigidas` do registro que estão na lista fechada (`python -m pytest`, `python tools/export_openapi.py`, leituras do Git; partes separadas por `;`; atribuições só de `PYTHONPATH=src`, `PUBLIC_DEMO` booleano e `TEST_DATABASE_URL` SQLite relativo ao worktree), sem herdar `TEST_DATABASE_URL`/`DATABASE_URL` do ambiente. Em correção, roda também os testes do head sobre o código da base (vermelho esperado). Resultado em `revisao-*.verificacoes.json` |
| Revisão | worktree `base` + worktree `revisao-*` no commit | Codex em sessão nova, `--sandbox workspace-write`, `--add-dir` do commit revisado, recebe as verificações do utilitário como evidência independente, saída `parecer.schema.json` |
| Conferência do parecer | os três worktrees | Rejeita se o revisor alterou arquivos versionados, se `head_revisado` difere do commit ou se o ramo mudou |
| Aprovação | `.agentes/execucoes/<id>/` | `pr.md`, `resumo.md`, pareceres por SHA. Aprovação automatizada, não aceite humano |

No deepwork (`modo: deepwork` no registro), as fases rodam em sequência no mesmo ramo, e cada uma parte
do commit aprovado da anterior. No fim, uma revisão integrada examina a base até o último commit.

## Artefatos de uma execução

| Arquivo | Conteúdo |
|---|---|
| `estado.json` | Estado, fases, rodadas, pareceres, sessões (ids, códigos, permissões negadas), versões das ferramentas, hash do pacote de instruções |
| `pedido.md` | Pedido original |
| `tarefa-v<n>.json/.md` | Registro da tarefa (versionado) e `tarefa-v<n>-f<k>.json` por fase |
| `entrega-f<k>-r<m>.json/.md` | Entrega do implementador (alegação) |
| `parecer-f<k>-t<m>.json/.md`, `parecer-integrado.*` | Pareceres válidos |
| `revisao-*.diff` | Diff entregue ao revisor |
| `*.invalida.json`, `*.rejeitado.json` | Saídas fora do schema ou pareceres rejeitados, para diagnóstico |
| `pr.md`, `resumo.md` | Descrição de PR e resumo, só na aprovação |

Saídas persistidas passam por sanitização: credenciais conhecidas e valores de variáveis de ambiente
sensíveis viram `<REDACTED>`. O ambiente completo e a transcrição das sessões não são copiados.

## Recuperação

| Estado | O que fazer |
|---|---|
| `interrompida` | Leia o motivo (`status`). Corrija a causa (autenticação, dependência, permissão, timeout) e rode `resume`. Interrupção não consome rodada |
| `aguardando_esclarecimento` | Responda num arquivo e rode `resume --resposta` |
| `bloqueada` | Decisão humana: nova execução com escopo ajustado, aceitar o risco fora do ciclo, `resume --rodada-extra` (mais uma correção e revisão) ou, quando o revisor bloqueou por limitação de ambiente, `resume --revisar-novamente` (invalida aquele parecer e revisa o mesmo SHA sem chamar o implementador). Toda decisão fica em `decisoes` |
| Resultado incerto | Se uma implementação caiu deixando alterações sem entrega, ou se o worktree tem commit desconhecido, `resume` recusa e explica. Inspecione o worktree e resolva à mão |

Duas retomadas simultâneas da mesma execução são recusadas por trava (`.trava`). Uma trava de
processo encerrado é retomada automaticamente.

## Publicar e limpar (responsável humano)

```powershell
git push origin archcorp/<id>      # conferir antes: status deve mostrar "corresponde ao ramo"
gh pr create --draft --head archcorp/<id> --body-file .agentes\execucoes\<id>\pr.md
git worktree remove .agentes\worktrees\<id>\impl   # e os demais, quando não forem mais necessários
```

Antes de publicar, preencha em `pr.md` o perigo do merge e o raio de impacto (`archcorp-pr`).

## Testes

`tests_agentes/` testa o utilitário com executáveis falsos (`fake_agente.py`), sem chamadas pagas, sem
PostgreSQL ou RabbitMQ e fora da fixture que limpa o banco da aplicação:

```powershell
python -m pytest tests_agentes -q -p no:cacheprovider
```

Testes simulados não provam a integração real; os ensaios com os agentes reais estão registrados em
[`PILOTOS_FLUXO.md`](PILOTOS_FLUXO.md).

## Limitações conhecidas

- Permissões do implementador: lista fechada em `FERRAMENTAS_CLAUDE` (testes com `python -m pytest`,
  exportação OpenAPI e leitura do Git). Comandos compostos e outros comandos são negados e aparecem
  como limitação na entrega; nos pilotos, o implementador recorreu às ferramentas Read/Grep.
- **Windows, sandbox `elevated` do Codex:** os comandos do revisor rodam como outro usuário, que não
  executa o Python do perfil (`C:\Users\...`). Por isso o utilitário executa ele mesmo as verificações
  exigidas e entrega o resultado ao revisor. Verificação fora da lista fechada continua dependendo do
  sandbox do revisor.
- As verificações do utilitário rodam sob a conta do usuário, como o implementador já roda os
  testes; só comandos da lista fechada, sem metacaracteres de shell.
- O `--json-schema` do Claude Code não é estrito: listas vazias omitidas na entrega são completadas
  (e registradas em `campos_completados`); outros campos ausentes interrompem a etapa.
- Com `--json`, o Codex relata falhas (inclusive limite de uso da conta) como eventos na saída padrão;
  o motivo da interrupção traz esse texto.
- O revisor roda com `workspace-write`. A proteção contra alteração é a conferência posterior dos
  worktrees, que rejeita o parecer.
- O `.venv` usado é o do checkout principal (worktrees não têm o próprio).
