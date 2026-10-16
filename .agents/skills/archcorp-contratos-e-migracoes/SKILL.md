---
name: archcorp-contratos-e-migracoes
description: >
  Use quando a mudança altera API REST (/api/v1), evento (AsyncAPI), schema Pydantic, exemplo de
  contrato, coluna/tabela (Alembic), valor monetário ou formato de data, ou quando é preciso decidir
  se algo quebra a compatibilidade da v1. Não use para mudança interna sem efeito em contrato ou
  esquema.
---

# Contratos e migrações no ArchCorp

Regra-mãe (`AGENTS.md`, "Reservas e contratos de integração"): **mudança compatível é aditiva;
incompatível exige nova versão ou exceção registrada em ADR** (ADR-002, ADR-003, ADR-004).

## 1. A mudança é compatível?

| Mudança | v1 | Observação |
|---|---|---|
| Novo campo **opcional** na resposta ou no evento | Compatível | Atualize exemplos e AsyncAPI/OpenAPI juntos |
| Novo valor de enum na resposta | Compatível com ressalva | Consumidor estrito pode quebrar; registre (ex.: `PARTIALLY_PAID`, ADR-003) |
| Campo novo **obrigatório** na entrada, remoção ou renomeação de campo, mudança de tipo | **Incompatível** | Nova versão ou exceção em ADR |
| Validação mais restrita em entrada antes aceita (ex.: limite monetário, Q-06) | **Incompatível** | Exceção explícita, como ADR-003 fez com valor de mais de duas casas |
| Mudança de `status`/`code` de erro | **Incompatível** | `test_api_v1_compatibility.py` protege o baseline |

O teste `test_contrato_v1_compativel_com_baseline_e_excecoes_explicitas`
(`tests/test_api_v1_compatibility.py`) só aceita diferenças listadas como exceção. Adicionar uma
exceção nele sem ADR é enfraquecer o teste.

## 2. Contratos versionados no repositório

- OpenAPI é **gerado**: `PYTHONPATH=src python tools/export_openapi.py` regenera
  `docs/api/openapi.yaml`; `--check` falha se divergir. Edite o código (schemas, `api_examples.py`),
  nunca o YAML gerado à mão.
- AsyncAPI (`docs/events/asyncapi.yaml`) é mantido à mão; o envelope obrigatório está no
  `AGENTS.md`. Evento novo exige schema, exemplo e consumidor documentado.
- Exemplos precisam **validar contra o schema**, não só existir. Foram achados exemplos que omitem
  campos obrigatórios nulos (`overdueSince`, `contractId`; Q-05). Ao tocar um schema, valide o
  exemplo correspondente.

## 3. Dinheiro e datas

- Valores monetários: duas casas, moeda ISO explícita, limite compatível com `Numeric(14,2)` na
  entrada **e** no resultado calculado (ex.: fatura final que multiplica ciclos). Na v1 eles
  trafegam como `number`; isso é dívida aceita para a v2 (decimal em string), não um padrão.
- Validação de múltiplo monetário com `float` falha para valores válidos (`19.99` rejeitado por
  `multipleOf: 0.01`; Q-04). Use comparação decimal exata no validador; não afrouxe com
  tolerância ampla.
- Datas e horas em ISO 8601 UTC com `Z` (ver `archcorp-dados-e-consistencia`).

## 4. Migrações Alembic

Pasta: `src/archcorp/infrastructure/migrations/versions/`. Histórico publicado **não** é reescrito
nem renumerado (inclusive o merge `0005_merge_finance_support`).

1. Mapear leitores, escritores e dados existentes antes de editar.
2. Expandir → migrar dados → verificar → contrair; contração (remover coluna, trocar unicidade) é
   passo separado e explicitamente autorizado.
3. Definir caminho de volta ou declarar por que não existe; revert de código não garante
   downgrade seguro.
4. Testar sobre dados anteriores (padrão de `test_migracao_0004_preserva_chamados_existentes`) e
   a convergência em PostgreSQL (`tests/test_migration_convergence.py`).
5. Duas migrações paralelas a partir da mesma base geram duas cabeças: ajuste o `down_revision` ou
   crie merge, e rode os testes de migração.

## 5. Checklist de saída

- [ ] OpenAPI exportado e `--check` limpo; AsyncAPI e exemplos atualizados e válidos.
- [ ] Compatibilidade v1 preservada ou exceção em ADR referenciada.
- [ ] Migração testada sobre dados existentes e em PostgreSQL quando a afirmação depender dele.
- [ ] Documentação de estado (`docs/ESTADO_IMPLEMENTACAO.md`) atualizada na mesma mudança.
