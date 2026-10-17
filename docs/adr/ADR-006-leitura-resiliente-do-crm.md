# ADR-006 — Leitura resiliente do CRM no F1: retentativa limitada e 503

- Status: Proposto; aguarda aceite do responsável do projeto
- Data: 2026-10-17
- Relaciona-se com ADR-001 e ADR-005

## Contexto

O critério do F1 no plano pede "timeout/retry limitado" na consulta ao CRM. Até
aqui, uma falha do `CustomerReader` virava `500 INTERNAL_ERROR` sem efeito
parcial (pendência T11 registrada no cronograma em 14/10/2026). O `AGENT.md`
exige timeout em chamadas externas e retentativa só para erro transitório, com
atraso exponencial e jitter. O CRM ainda roda no mesmo processo; não há
conector de rede.

Duas respostas foram consideradas para a indisponibilidade do CRM:

1. `503 SERVICE_UNAVAILABLE`, sem gravar nada, para o chamador repetir com a
   mesma `Idempotency-Key`.
2. Reserva ou rascunho em estado `PENDING`, com reconciliação posterior, como o
   chamado em `PENDING_ENTITLEMENT` do F3.

## Decisão

Adotar a opção 1.

- `contracts.adapters.ResilientCustomerReader` envolve a porta pública
  `CustomerReader`. Repete apenas `TimeoutError` e `ConnectionError`; outros
  erros sobem sem nova tentativa.
- O atraso entre tentativas é exponencial (`base * 2^(n-1)`), limitado a um
  teto e multiplicado por um jitter entre 50% e 100%.
- `CRM_READER_TIMEOUT_SECONDS` (padrão 2 s) é o prazo total de tentativas e
  esperas. `CRM_READER_MAX_ATTEMPTS` (padrão 3) e
  `CRM_READER_BASE_DELAY_SECONDS` (padrão 0,1 s) completam a configuração.
- Ao esgotar, o adaptador levanta `CustomerReaderUnavailableError`, declarada
  em `crm.public`. `ContractService.read_customer` a converte em
  `ServiceUnavailableError` (`503`) antes de qualquer gravação. A conversão
  vale para criação de reserva, rascunho direto, rascunho pela reserva e
  revalidação na ativação.
- Cada tentativa falha gera log `WARNING` com `correlationId`, operação
  `crm_customer_read` e resultado `retry`.

## Justificativa

O F1 é uma interação síncrona de venda: quem cria a reserva ou o rascunho
precisa saber na hora se a operação ocorreu. Um rascunho pendente sem dados
cadastrais confirmados criaria um estado intermediário que o domínio de
Contracts ainda não tem, além de outra rotina de reconciliação. O `503` sem
efeito, somado à `Idempotency-Key`, deixa a repetição segura e não amplia o
modelo de estados. O F3 continua diferente porque o atendimento não pode
recusar o chamado do cliente; ali o estado pendente é requisito.

## Consequências e limites

- O prazo limita o tempo total de tentativas e esperas. No processo único, uma
  leitura em andamento não é interrompida. O corte de cada chamada deve ficar
  no cliente HTTP do conector, quando o CRM sair do processo.
- As esperas ocupam a thread da requisição; com os padrões, o pior caso
  adicional é inferior a 1 s.
- O OpenAPI passa a declarar `503` nas quatro rotas afetadas. A mudança é
  aditiva, e a v1 não muda.
- Um teste unitário cobre o atraso, o teto, o jitter, o prazo e os erros não
  transitórios. Testes HTTP cobrem `503` sem efeito, a falha transitória
  absorvida, o erro não transitório sem retentativa e a repetição após o
  retorno do CRM.
