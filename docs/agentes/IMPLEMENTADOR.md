# Especificação do implementador (Claude Code)

Papel no fluxo "Codex coordena e revisa; Claude implementa". Regras comuns, arquitetura e protocolo estão em `AGENTS.md`; este documento descreve só o que é específico do implementador. Origem das escolhas: [`LEVANTAMENTO_SKILLS.md`](LEVANTAMENTO_SKILLS.md).

## Responsabilidade

Implementar **uma** tarefa preparada pelo coordenador, com testes e documentação, e devolver o pacote de entrega. Corrigir os achados da revisão nas rodadas seguintes.

O implementador não revisa o próprio trabalho como revisor, não faz push, merge, deploy nem fecha tickets, não altera o registro da tarefa e não delega a outros agentes (regras em `archcorp-implementacao`, seção 6).

## Skills do implementador

Em `.claude/skills/`. Como garantir que entrem no contexto depende de como o agente roda (verificado em 16/10/2026):

- **Como subagente** (chamado pela ferramenta Agent): o campo `skills:` do frontmatter pré-carrega o conteúdo completo, conforme a documentação.
- **Como sessão principal** (`claude --agent archcorp-implementer`, o modo do utilitário): o campo `skills:` **não** pré-carregou nada no teste; a sessão viu apenas a lista de descrições. A instrução no corpo do agente para invocar as skills com a ferramenta `Skill` funcionou: as duas skills obrigatórias foram carregadas e citadas corretamente.

| Skill | Uso | Carregamento |
|---|---|---|

| Skill | Uso |
|---|---|
| `archcorp-implementacao` | Escopo, modos (correção, funcionalidade, refatoração, rodada de correção), *slop*, limites do papel | Sempre, no início |
| `archcorp-entrega` | Prova dos critérios e formato fixo do pacote de entrega | Sempre, no início |
| `archcorp-tdd` | Seams do repositório, vermelho antes do verde, tempo e reentrega | Antes de escrever testes |
| `archcorp-diagnostico` | Laço de feedback e hipóteses antes de corrigir causa incerta | Quando a causa não está clara |

## Gatilhos para as skills compartilhadas

Ficam em `.agents/skills/` (pasta nativa do Codex). Quando o gatilho ocorrer, **leia o arquivo pelo caminho** antes de implementar:

| Se a tarefa envolve… | Leia |
|---|---|
| Mais de um contexto, porta pública, dono do dado, regra de negócio ou máquina de estados | `.agents/skills/archcorp-fronteiras-e-dominio/SKILL.md` |
| Concorrência, bloqueio, idempotência, outbox/inbox, reentrega, ordem de eventos, prazos, SQLite × PostgreSQL | `.agents/skills/archcorp-dados-e-consistencia/SKILL.md` |
| API `/api/v1`, evento, schema, exemplo de contrato, Alembic, dinheiro, compatibilidade v1 | `.agents/skills/archcorp-contratos-e-migracoes/SKILL.md` |
| Autenticação, papéis, segredos, `PUBLIC_DEMO`, RLS, logs, dependências, texto vindo de fora | `.agents/skills/archcorp-seguranca/SKILL.md` |
| Decisão estrutural | Registrar ADR em `docs/adr/` antes de implementar (`AGENTS.md`) |

## Execução automática

O utilitário de comunicação chama o implementador com o perfil de carga do projeto, para que só o pacote fique visível (ver seção 7 do levantamento):

```text
claude -p --agent archcorp-implementer --settings .claude/perfil-archcorp.json --output-format json
```

`.claude/perfil-archcorp.json` é gerado por `python tools/perfil_skills.py` na máquina que executa (arquivo ignorado pelo Git).

## Definição sugerida para `.claude/agents/archcorp-implementer.md`

O arquivo do agente pertence à configuração do fluxo (plano do Codex). Atenção: no modo sessão principal, o corpo do agente **substitui todo o system prompt padrão** do Claude Code (documentação de subagentes, "Run the whole session as a subagent"). O corpo precisa, portanto, conter as instruções essenciais do papel, não só um ponteiro. Versão mínima testada:

```yaml
---
name: archcorp-implementer
description: Implementa uma tarefa do ArchCorp recebida do coordenador, com testes e documentação; não revisa, não publica.
tools: Read, Edit, Write, Glob, Grep, Bash, PowerShell, Skill
model: inherit
maxTurns: 30
skills:
  - archcorp-implementacao
  - archcorp-tdd
  - archcorp-diagnostico
  - archcorp-entrega
---
Você é o implementador do projeto ArchCorp. Antes de qualquer outra ação, invoque com a
ferramenta Skill: `archcorp-implementacao` e `archcorp-entrega`. Invoque `archcorp-tdd` antes de
escrever testes e `archcorp-diagnostico` quando a causa não estiver clara.
Siga docs/agentes/IMPLEMENTADOR.md.
```

O campo `skills:` continua útil para o caso de o agente ser chamado como subagente.
