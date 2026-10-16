# Especificação do implementador (Claude Code)

Papel no fluxo coordenado. Ciclo, estados, artefatos e limites estão em
[`PROTOCOLO.md`](PROTOCOLO.md); regras do repositório em [`AGENTS.md`](../../AGENTS.md). Este
documento descreve só o que é específico do implementador. Origem das escolhas:
[`LEVANTAMENTO_SKILLS.md`](LEVANTAMENTO_SKILLS.md).

## Responsabilidade

Implementar **uma** tarefa preparada pelo coordenador, com testes e documentação, e devolver a
entrega estruturada (`schemas/entrega.schema.json`). Nas rodadas de correção, responder a cada
achado numerado do parecer.

O implementador não faz commit (o utilitário faz), não revisa o próprio trabalho como revisor, não
faz push, merge, deploy nem fecha tickets, não altera o registro da tarefa e não delega a outros
agentes.

## Perfil

[`.claude/agents/archcorp-implementer.md`](../../.claude/agents/archcorp-implementer.md):
ferramentas permitidas, `maxTurns: 30` e as instruções essenciais do papel. No modo sessão principal
(`claude --agent`), o corpo do agente substitui o system prompt padrão do Claude Code, por isso ele
contém as regras do papel e não só um ponteiro.

Carregamento das skills (verificado em 16/10/2026):

- **Como subagente** (ferramenta Agent): o campo `skills:` pré-carrega o conteúdo completo.
- **Como sessão principal** (`claude --agent`, modo do utilitário): `skills:` não pré-carrega; a
  instrução no corpo do agente faz a sessão invocá-las. Nas execuções automáticas, o utilitário
  indica a pasta de instruções fixadas e as skills são lidas pelo caminho.

## Skills do implementador

Em `.claude/skills/`:

| Skill | Uso | Carregamento |
|---|---|---|
| `archcorp-implementacao` | Escopo, modos (correção, funcionalidade, refatoração, rodada de correção), *slop*, limites do papel | Sempre, no início |
| `archcorp-entrega` | Prova dos critérios e formato da entrega | Sempre, no início |
| `archcorp-tdd` | Seams do repositório, vermelho antes do verde em bug, tempo e reentrega | Ao criar ou modificar testes |
| `archcorp-diagnostico` | Laço de feedback e hipóteses provisórias até a causa ser comprovada | Quando a causa não está estabelecida |

## Gatilhos para as skills compartilhadas

Ficam em `.agents/skills/` (pasta nativa do Codex). Quando o gatilho ocorrer, **leia o arquivo
pelo caminho** antes de implementar:

| Se a tarefa envolve… | Leia |
|---|---|
| Mais de um contexto, porta pública, dono do dado; **ou** regra de negócio ou máquina de estados alterada, mesmo num único arquivo | `.agents/skills/archcorp-fronteiras-e-dominio/SKILL.md` |
| Concorrência, bloqueio, idempotência, outbox/inbox, reentrega, ordem de eventos, prazos, SQLite × PostgreSQL | `.agents/skills/archcorp-dados-e-consistencia/SKILL.md` |
| API `/api/v1`, evento, schema, exemplo de contrato, Alembic, dinheiro, compatibilidade v1 | `.agents/skills/archcorp-contratos-e-migracoes/SKILL.md` |
| Autenticação, papéis, segredos, `PUBLIC_DEMO`, RLS, logs com dados, dependências, CI/Docker | `.agents/skills/archcorp-seguranca/SKILL.md` |
| Mudança em `docs/`, README, ADR ou `output/` | `.agents/skills/archcorp-documentacao/SKILL.md` |
| Decisão estrutural | Registrar ADR em `docs/adr/` antes de implementar (`AGENTS.md`) |

## Execução automática

Quem chama o implementador é `tools/fluxo_archcorp.py` (ver [`FLUXO_AUTOMATIZADO.md`](FLUXO_AUTOMATIZADO.md)),
num worktree exclusivo, com o perfil de carga do projeto (`.claude/perfil-archcorp.json`, gerado por
`python tools/perfil_skills.py`), permissão `acceptEdits` e uma lista fechada de comandos. Comando
fora da lista é negado e deve aparecer na entrega como impedimento. Nenhuma opção de bypass de
permissões é usada.
