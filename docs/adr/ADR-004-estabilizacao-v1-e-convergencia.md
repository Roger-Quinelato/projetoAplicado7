# ADR-004 — Compatibilidade v1, privacidade e convergência T12/T15

- Status: Aceito para execução do planejamento autorizado pelo responsável do projeto
- Data: 2026-10-15
- Relaciona-se com ADR-001, ADR-002 e ADR-003

A revisão de estabilização preserva `409 CONFLICT` em resolução/atribuição inválida
e `409 INVALID_STATE` em reconciliação inválida. Sem chave, repetição continua
conflito. Com `Idempotency-Key` opcional em resolve/reconcile, a resposta original
é persistida atomicamente com histórico, auditoria e outbox. A impressão digital
inclui chamado e comando; a chave é compartilhada entre esses dois comandos para
rejeitar reutilização cruzada. Mudanças posteriores de estado ou relógio não mudam
a resposta recuperada. A abertura mantém sua chave obrigatória e comparação do
pedido completo. Atribuição, resolução e reconciliação bloqueiam a mesma linha de
Ticket; histórico e efeitos são confirmados juntos. SQLite não comprova esses
bloqueios; testes concorrentes próprios exigem PostgreSQL.

A regex adicionada na T15 não constitui proteção suficiente e rejeita texto válido
(SEI e ISO 8601). As novas rejeições de descrição e responsável foram retiradas da
v1, preservando validações de tamanho/tipo. Só dados sintéticos são permitidos no
protótipo. Descrição permanece fora de eventos, auditoria e logs. Erros 422 mantêm
listas `detail`/`errors`, tipo/localização/código/status/correlação, mas deixam de
ecoar `input`, `ctx` e mensagens interpoladas. Essa é uma exceção contratual de
segurança deliberada; clientes não devem depender do texto de mensagens nem de
dados rejeitados. Não se afirma que regex detecta ou elimina dados pessoais.

As revisões `0004_finance_lifecycle` e `0004_support_sla_history` já estão publicadas.
Não há evidência de quais bancos persistentes as aplicaram. Por isso o plano de
renumerar Support para 0005 foi ajustado: ambas as revisões permanecem intactas e
`0005_merge_finance_support` converge seus caminhos numa única head. As expansões
atuam em tabelas diferentes. Upgrade pode partir da 0003 ou de qualquer uma das
duas revisões. O downgrade financeiro mantém a proteção FINAL antes de alterações;
a revisão de convergência não altera esquema nem dados. O histórico registra a
bifurcação em vez de fingir que ela nunca existiu. Testes verificam dados legados,
convergência, ausência de drift e bloqueio de downgrade com preservação de dados.

CI passa a executar também PostgreSQL 16 dedicado com credenciais sintéticas
efêmeras, sem conectar Supabase/Render ou sistemas reais. Resultado configurado
não é resultado executado: as evidências distinguem execução local e CI.
