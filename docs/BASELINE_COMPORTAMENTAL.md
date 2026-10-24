# Baseline de comportamento do protótipo

Registro de 17/10/2026, sobre o commit
`3fdb53302bfbc9277e40b7a4698c8a6c3c0943dd`.

Esta baseline registra comportamentos que devem ser preservados em mudanças
futuras. Preservar significa manter o resultado observável e os limites de
escopo. A implementação pode evoluir mediante requisito, análise de impacto,
atualização dos contratos afetados e provas de regressão. Mudanças estruturais
exigem ADR, conforme [AGENT.md](../AGENT.md).

Não congelar bugs, estilos visuais ou detalhes internos por causa deste registro.
Os achados da auditoria continuam sendo pendências, mesmo com as suítes verdes.

## Regras a preservar

| Regra consolidada | Resultado que não pode regredir | Evidência automatizada |
|---|---|---|
| Identidade compartilhada e propriedade dos dados | Contratos reutilizam o UUID do cliente do CRM; módulos se comunicam por interfaces públicas | `tests/test_flows.py`, `tests/test_contracts_and_architecture.py` |
| Elegibilidade e consentimento | Cliente sem elegibilidade ou consentimento não gera rascunho; ativação revalida o cliente | `tests/test_contracts.py` |
| Idempotência com comparação do pedido | Repetição equivalente recupera o resultado; mesma chave com outro conteúdo gera conflito | `tests/test_contracts.py`, `tests/test_support.py` |
| Ativação sem efeitos duplicados | Reativação, reentrega do evento e novo evento do mesmo fato mantêm uma fatura e um processo de preparação | `tests/test_flows.py` |
| Valores monetários | Centavos são preservados; frações de centavo, excesso e moeda incompatível são rejeitados; pagamentos são auditados | `tests/test_finance.py` |
| Atendimento e SLA | Elegibilidade determina abertura, prioridade e prazo; indisponibilidade admite estado pendente e reconciliação explícita | `tests/test_flows.py`, `tests/test_extended_modules.py` |
| Workflow e estados finais | Tarefas finais não reabrem; repetição não duplica efeitos; agregado reflete conclusão ou cancelamento | `tests/test_workflow.py` |
| Recuperação transacional | Falha de despacho desfaz efeitos locais e inbox; retentativas e reprocessamento mantêm rastreabilidade | `tests/test_dispatch_recovery.py`, `tests/test_flows.py` |
| Autorização e erros | Rotas protegidas aplicam papéis; erro preserva `application/problem+json` e correlação; modo público rejeita tokens locais | `tests/test_demo_credentials.py`, `tests/test_foundation.py` e testes de papéis dos módulos |
| Contratos publicados | OpenAPI salvo corresponde à aplicação; eventos respeitam envelope e schemas; migrações são aditivas | `tests/test_contracts_and_architecture.py`, `tests/test_foundation.py` |
| Formulários | Envio pendente bloqueia repetição; campos são preservados após rejeição da API e limpos após sucesso | `web/tests/navigation.spec.ts` |
| Transparência acadêmica | Interface e documentação identificam dados sintéticos, pagamentos simulados e ausência de integração com sistemas reais da Localiza | `README.md`, interface e `AGENT.md` |

## Limites que também devem ser preservados na documentação

- O protótipo é um monólito modular. Os consumidores são chamados pelo
  despachante interno. RabbitMQ recebe uma cópia opcional dos eventos.
- Fila de falhas da aplicação não equivale a uma DLQ do RabbitMQ.
- Publicação em broker e commit no banco não formam uma transação distribuída.
- Token local por papel e segredo compartilhado público não equivalem a OIDC
  ou contas individuais.
- Pagamentos são simulados; frota, assinatura, cobrança bancária e emissão
  fiscal reais não estão conectadas.
- Testes locais, inclusive com PostgreSQL e RabbitMQ, não comprovam deploy
  Render/Supabase, HTTPS público, alta disponibilidade ou escala horizontal.
- Axe e navegação por teclado cobrem cenários determinados; não certificam
  conformidade completa com WCAG.

## Verificação antes de alterar estas regras

1. Identifique a regra e o requisito afetados. Consulte os contratos e ADRs.
2. Preserve os testes existentes; para correção, acrescente prova que reproduz
   o defeito antes da alteração.
3. Execute a suíte Python, a compilação e os testes de interface pertinentes.
4. Para mudanças de integração, execute também o fluxo real com API, banco e
   broker, incluindo indisponibilidade, recuperação e repetição.
5. Atualize estado, contratos e rastreabilidade na mesma mudança. Descreva
   explicitamente qualquer comportamento substituído por decisão aprovada.

## Evidências e pendências

As suítes de 17/10/2026 aprovaram 84 testes Python e 11 de navegador, com build
aprovado. Os testes de navegador originais usam API simulada. O roteiro
complementar de teste real e seus resultados estão no
[relatório da auditoria](../output/auditoria/teste-real-2026-10-17/RELATORIO.md).
O relatório distingue problemas da aplicação, preparação do ambiente e limites
de cobertura; esses problemas não fazem parte da baseline aprovada.
