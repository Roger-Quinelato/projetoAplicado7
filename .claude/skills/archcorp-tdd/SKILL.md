---
name: archcorp-tdd
description: >
  Use ao escrever ou ajustar testes no ArchCorp: regressão de bug (teste que falha antes da
  correção), comportamento novo test-first, ou quando é preciso escolher em que costura (seam)
  testar. As seams vêm do registro da tarefa; não pergunte ao usuário.
---

# TDD no ArchCorp

Ciclo vermelho → verde, uma fatia por vez. Teste bom verifica **comportamento por interface
pública** e sobrevive a refatoração; teste ruim verifica implementação.

## 1. Seams (onde o teste observa)

As seams a cobrir estão no registro da tarefa ("verificações exigidas"). Se o registro não as
definir, escolha pela tabela e **declare** a escolha na entrega, com uma linha sobre o que cada seam
pega e o que deixa passar.

| Seam | Quando | Como neste repositório |
|---|---|---|
| Função de domínio pura | Regra, transição de estado, cálculo (prazo, saldo) | Chamar `contracts/domain.py`, `finance/domain.py`, `support/domain.py` sem HTTP nem banco |
| API HTTP | Contrato, validação, autorização, efeitos persistidos | Fixtures `client`, `admin_headers`, `integrated_contract` (`tests/conftest.py`); asserções sobre corpo **e** estado relido do banco |
| Evento e consumidor | Efeito entre contextos | Gravar pela API, despachar com `POST /api/v1/integration/outbox/dispatch` e conferir o efeito no destino; reentrega chamando o consumidor de novo com o mesmo envelope (`OutboxEvent.envelope()`) |
| Porta de outro contexto | Indisponibilidade, resposta inesperada | Simulador da porta (padrão `FakeEntitlementPort` em `tests/test_t15_atendimento.py`) |
| PostgreSQL real | Bloqueio, concorrência, limites numéricos, migração | `tests/test_postgresql_concurrency.py` e similares, com o skip padrão sem `TEST_DATABASE_URL` |

## 2. Regras do ciclo

- **Vermelho antes do verde.** O teste de regressão precisa falhar no código da base **pelo
  motivo do bug**. Rode-o contra a base e registre a mensagem de falha. Falhar por outro motivo
  (relógio real diferente do falso, fixture errada) não conta. Foi o que a revisão do Q-01 pegou.
- Uma seam, um teste, a implementação mínima, repetir. Não escreva todos os testes antes.
- O valor esperado vem de fonte independente (literal conhecido, exemplo da especificação), nunca
  recalculado do jeito que o código calcula.
- Refatoração não faz parte do ciclo; fica para depois do verde, com a mesma prova.

## 3. Tempo, concorrência e reentrega

- Tempo: injete relógio (`FakeClock` com `advance`) em **todos** os serviços envolvidos, inclusive
  o consumidor do evento. Se um serviço lê `datetime.now()` direto, fixe-o por `monkeypatch` para
  provar que o resultado não depende dele.
- Reentrega: o segundo `dispatch` não reexecuta um evento já processado; para testar idempotência
  do consumidor, chame-o diretamente com o mesmo envelope.
- Concorrência: veja `archcorp-dados-e-consistencia`, seção 5. Duas chamadas sequenciais não provam
  concorrência.

## 4. Simular só na fronteira

Simule portas de outros contextos, relógio, broker e serviços externos. Não simule classes do
próprio contexto nem consulte o banco por atalho quando a interface pública mostra o efeito; o
teste quebraria a cada refatoração sem mudança de comportamento.

## 5. Antipadrões que reprovam

- Teste que só confere status HTTP sem conferir o efeito.
- Asserção tautológica (esperado calculado com a mesma fórmula do código).
- Teste removido, marcado como skip ou afrouxado para ficar verde.
- Exceção adicionada ao baseline v1 (`tests/test_api_v1_compatibility.py`) sem ADR.
