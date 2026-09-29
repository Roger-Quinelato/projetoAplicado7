# Dados sintéticos e identificadores

Estado em 29/09/2026 (T07, ARCH7-7). Este documento define os dados permitidos no
protótipo acadêmico. O protótipo não acessa sistemas reais da Localiza e não deve
receber dados pessoais reais.

## Regras

- Use somente dados inventados. Nomes de empresas e pessoas devem ser fictícios.
- Use e-mails nos domínios reservados para exemplos pela RFC 2606:
  `example.com`, `example.net` e `example.org`, inclusive em subdomínios como
  `frota@aurora-sintetica.example.com`. A API valida e-mails e rejeita domínios
  de uso especial como `.test` e `.invalid`.
- Não informe CPF, CNPJ, RG, placa, endereço, dados bancários ou cartão. O modelo
  do protótipo não possui esses campos.
- Campos de texto livre (`name`, `phone`, `description`, `notes`, `reference`) não
  são inspecionados pela API. Quem opera a demonstração é responsável por não
  inserir dados reais nesses campos. A tela de acesso da interface e o README
  repetem a orientação de usar dados sintéticos.
- Identificadores legados de exemplo usam prefixos como `SINT-`, `CRM-` ou
  `WEB-LOCALIZA-`, que não correspondem a registros reais.
- Logs não registram payloads; erros internos registram somente caminho,
  resultado e `correlationId`.

## Identificadores globais

- Cada entidade usa UUID versão 4 gerado pelo contexto proprietário no momento da
  criação (`customerId`, `contractId`, `reservationId`, `ticketId`, `invoiceId`,
  `processId`).
- Os UUIDs são armazenados como texto de 36 caracteres para manter o mesmo
  esquema em SQLite e PostgreSQL. A API aceita somente UUIDs válidos em caminhos e
  corpos; outro formato recebe `422`.
- Um identificador de sistema de origem fica em `integration_legacy_ids`, com a
  combinação única `sourceSystem` + `legacyId`. Hoje o CRM registra o `legacyId`
  informado na criação do cliente. A consulta
  `GET /api/v1/integration/legacy-ids/{sourceSystem}/{legacyId}` devolve o UUID
  global correspondente.
- Um identificador legado já associado a outro registro recebe `409 CONFLICT`.

## Carga de demonstração

`scripts/seed_sintetico.py` cria três clientes e dois rascunhos de contrato pela
API pública:

```bash
PYTHONPATH=src python scripts/seed_sintetico.py
PYTHONPATH=src python scripts/seed_sintetico.py --base-url http://localhost:8000 --token demo-admin
```

A carga é idempotente: clientes são localizados pelo identificador legado
`SINT-CLI-*` e rascunhos usam `Idempotency-Key` fixa. Executar a carga de novo não
duplica registros; `tests/test_foundation.py` verifica esse comportamento.

| Legado | Cliente | Situação |
|---|---|---|
| `SINT-CLI-001` | Transportes Aurora Sintética Ltda. | Elegível, com rascunho mensal |
| `SINT-CLI-002` | Construtora Horizonte Fictícia S.A. | Elegível, com rascunho trimestral |
| `SINT-CLI-003` | Comércio Sem Consentimento Demo | Sem consentimento; não pode originar contrato |
