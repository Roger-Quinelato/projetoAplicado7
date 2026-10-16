---
name: archcorp-fronteiras-e-dominio
description: >
  Use ao criar, mover ou revisar código que cruza contextos do ArchCorp (crm, contracts, finance,
  support, workflow, integration), quando um import, consulta ou evento liga dois módulos, e
  sempre que uma regra de negócio ou máquina de estados for criada ou alterada, mesmo num único
  arquivo. Não use para mudança técnica restrita a um arquivo sem regra de negócio nem efeito em
  outro contexto.
---

# Fronteiras e domínio do ArchCorp

Monólito modular com SOA pragmática (ADR-001). As fronteiras valem mesmo com um processo e um
banco. As regras completas estão em `AGENTS.md` (seções "Arquitetura obrigatória" e "Propriedade
dos dados"); esta skill é o roteiro de decisão.

## 1. Quem é o dono

Antes de escrever, responda: **qual contexto é a fonte oficial do dado ou da regra?** Use a tabela
de propriedade do `AGENTS.md`. Atalhos frequentes:

| Pergunta | Dono |
|---|---|
| Cliente pode contratar? | `crm` (via `CustomerReader` em `crm/public.py`) |
| Contrato vigente, SLA, serviço coberto? | `contracts` (via `ContractEntitlementPort` em `contracts/public.py`) |
| Valor devido, saldo, inadimplência? | `finance` (`finance/domain.py`) |
| Prazo e estado do chamado? | `support` (`support/domain.py`) |
| Tarefa, responsável e prazo operacional? | `workflow` |
| Correlação, outbox/inbox, idempotência, IDs legados, auditoria | `integration` (fachada `integration/public.py`) |

Integração **traduz, roteia, correlaciona e orquestra**; ela não decide regra de negócio dos
outros cinco.

## 2. Como um contexto fala com outro

| Necessidade | Forma permitida | Proibido |
|---|---|---|
| Resposta imediata (consulta, validação) | Porta pública do dono (`<contexto>/public.py`), substituível por simulador em teste | Importar `models`, `service` ou repositório de outro contexto; consultar a tabela dele |
| Fato consumado com efeito em outro contexto | Evento pela outbox (`integration.public.enqueue`), consumidor idempotente no destino | Chamar o serviço do destino dentro da transação de origem |
| Infraestrutura transversal | `integration.public` (idempotência, auditoria, eventos, IDs legados) | `integration.service`/`integration.models` diretamente (ADR-005) |

O teste `test_modulos_de_negocio_nao_importam_models_de_outro_contexto`
(`tests/test_contracts_and_architecture.py`) verifica isso por AST, mas cobre principalmente
`from ... import`. Ao revisar, confira também `import` simples, alias e novos subpacotes.

Compromisso vigente (ADR-005): portas e casos de uso recebem `Session` do SQLAlchemy. Não é
hexagonal completa. **Não** crie interfaces de repositório só para satisfazer o rótulo; mudar isso
exige ADR.

## 3. Onde mora a regra

- Estado e transições ficam numa **máquina de estados única** no domínio do dono
  (`contracts/domain.py`, `finance/domain.py`, `support/domain.py`). Rota HTTP valida formato e
  delega; não atribui estado diretamente. Exceções conhecidas em 16/10/2026 estão em
  [`references/historico.md`](references/historico.md); reconfira no SHA atual.
- Alteração de transição, guarda ou regra num único arquivo de domínio também passa por esta
  seção: confira se a regra continua no dono, se outra cópia dela existe em outro contexto e se os
  consumidores do estado (eventos, `web/src/api.ts`) continuam coerentes.
- Valor sem identidade própria (dinheiro com moeda, período, prazo) é tratado como valor; não
  espalhe `float` + `str` soltos.
- Regra semelhante em dois contextos é sinal de dono errado ou de regra vazada para a integração.
  Pare e identifique a fonte oficial antes de duplicar.

## 4. Sinais de alerta (revisão e autorrevisão)

- Um contexto lê dado de outro que poderia mudar sem que ele saiba (cópia sem evento de
  atualização ou sem ordem garantida; ver `archcorp-dados-e-consistencia`).
- Um consumidor de evento recalcula algo que o produtor já publicou (ex.: Workflow recalculando o
  prazo do chamado; ver histórico).
- Uma mudança exige editar quatro contextos por um motivo só: a regra está espalhada.
- Um módulo de negócio passa a importar SDK, HTTP ou broker no domínio.
- "Última escrita vence" aplicada a divergência entre contextos sem decisão explícita.

## 5. Quando precisa de ADR

Novo contexto, mudança de dono de dado, nova forma de comunicação entre contextos, quebra do
compromisso do ADR-005 ou qualquer microsserviço/banco adicional. Registre em `docs/adr/` antes de
implementar; não reescreva ADR aceito.
