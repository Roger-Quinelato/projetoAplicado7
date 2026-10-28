# Visão de negócio e viabilidade

> O estado atual de execução está no [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e no [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

## Público-alvo

O público interno inclui comercial e canais digitais, reservas e contratos, financeiro e faturamento, atendimento e assistência 24h,
operações e gestão. Essas áreas usam ou acompanham dados e processos que
atravessam os cinco sistemas do Cenário 4. Clientes recebem o benefício indireto
de uma ativação mais previsível e de um atendimento e assistência 24h vinculado ao serviço
contratado.

Os nomes das áreas responsáveis e a distribuição real de usuários são
**Premissa a validar**. O guia confirma os sistemas e os problemas gerais, mas
não informa a estrutura da organização.

## Problema organizacional

O guia confirma duplicidade de informações, lançamentos manuais, comunicação
insuficiente, falta de padronização, dependência de legados e processos
fragmentados. Para a demonstração, o projeto aplica esses problemas à passagem
de dados entre venda, contrato, cobrança, preparação de retirada e atendimento e assistência 24h. Esse fluxo
específico é **Premissa a validar** com a organização.

Sem uma identidade compartilhada e contratos de integração, cada área pode
trabalhar com uma versão diferente do cliente, do contrato ou do SLA. A ausência
de correlação e recuperação uniforme também aumenta o tempo necessário para
localizar e corrigir falhas.

## Proposta de valor

O recorte executável revisado em 28/10/2026 usa dados sintéticos: CRM,
reservas/contratos, faturamento e pagamentos simulados, chamados com SLA e tarefas
operacionais. Não inclui gestão de frota, PSP ou integração real. Grupo de
veículo e proteção ficam na reserva, sem exposição no contrato ou na
elegibilidade. OIDC/OAuth e identidade corporativa são evolução futura;
a autenticação atual usa tokens Bearer de demonstração.

A arquitetura cria uma referência global de cliente e conecta os processos por
APIs e eventos versionados. Cada sistema mantém a propriedade de seus dados, e a
camada de integração registra tradução, entrega, correlação e falhas. A proposta
reduz recadastro e torna ativação, cobrança, preparação de retirada e atendimento e assistência 24h
rastreáveis sem substituir integralmente os cinco sistemas.

## Benefícios e indicadores

Os benefícios esperados precisam ser comparados com uma linha de base da
organização. O guia não fornece essa linha de base; portanto, o projeto não
estima percentuais de ganho ou economia.

| Benefício esperado | Indicador proposto | Dado necessário | O que o protótipo mede hoje |
|---|---|---|---|
| Reduzir recadastro e duplicidade | Percentual de reservas e contratos que exigem novo cadastro do cliente | Quantidade atual de reservas, contratos e recadastros | Nada sobre a organização. Os testes do F1 provam que o contrato referencia o `customerId` global, sem novo cadastro |
| Coordenar ativação da locação, cobrança e preparação de retirada | Tempo entre ativação, primeira cobrança da locação e início do processo | Horários registrados pelos sistemas atuais | Os instantes da ativação, da fatura e do processo ficam registrados (auditoria e `occurredAt`), mas não há linha de base para comparar |
| Aplicar o SLA contratado | Percentual de chamados com SLA incorreto ou não confirmado | Histórico de chamados, reservas e contratos | O SLA vem do contrato (F3) e chamados sem confirmação ficam `PENDING_ENTITLEMENT`. Sem histórico real |
| Evitar efeitos duplicados | Cobranças, processos ou chamados duplicados por reentrega | Ocorrências atuais e registros de integração | Os testes de reentrega por `eventId` e de novo evento do mesmo fato não geram efeito duplicado. A ocorrência atual é desconhecida |
| Acelerar diagnóstico e recuperação | Tempo médio para localizar a causa e reprocessar uma falha | Histórico operacional e tempos de atendimento e assistência 24h | A consulta por correlação e o reprocessamento da outbox existem. O tempo de diagnóstico não é medido |
| Facilitar mudanças | Quantidade de sistemas afetados por alteração de contrato | Histórico de mudanças e dependências atuais | O teste estático de fronteiras e os contratos versionados existem. O efeito sobre mudanças reais não é medido |

Nenhuma linha da tabela comprova ganho para a organização: o protótipo demonstra o mecanismo, e o indicador só tem valor comparado com a linha de base.

## Análise de viabilidade

| Dimensão | Por que a proposta é viável para a primeira entrega | Condição ou risco para adoção organizacional |
|---|---|---|
| Custos | O monólito modular limita a quantidade de unidades de implantação. Simuladores permitem demonstrar os fluxos sem licenças ou ambientes legados. | Descoberta, conectores reais, identidade corporativa, operação e qualidade de dados geram custos ainda não informados. |
| Complexidade | Um processo reúne os módulos, enquanto portas, adaptadores e contratos de integração preservam as fronteiras. | Outbox, inbox, mensageria, idempotência e observabilidade exigem disciplina técnica e suporte operacional. |
| Infraestrutura | Docker Compose reproduz API, PostgreSQL e RabbitMQ para a demonstração. | Produção exige definição de hospedagem, TLS, backup, disponibilidade, monitoramento e capacidade. |
| Equipe | A equipe júnior consegue concentrar a primeira entrega nos três fluxos, nos contratos de integração e nas evidências. | Papéis, disponibilidade, experiência com os produtos legados e suporte após implantação são **Premissa a validar**. |
| Prazo | A priorização P0 limita o trabalho aos requisitos e fluxos necessários para a avaliação. | O guia não define duração para integração real; acesso a ambientes e validação com responsáveis podem alterar o cronograma. |
| Necessidades futuras | Portas e adaptadores permitem integrar novos sistemas; contratos versionados e consumidores idempotentes preservam evolução. | Extração de serviços, particionamento e escala horizontal dependem de métricas e de novo ADR quando houver mudança estrutural. |

## Custos do demonstrador

A gratuidade dos serviços usados não significa custo zero. Os três custos são separados abaixo, e nenhum foi medido em dinheiro.

| Custo | O que inclui | Situação |
|---|---|---|
| Serviços (licenças e hospedagem) | PostgreSQL e RabbitMQ executados localmente por Docker Compose (software livre, sem licença); GitHub para repositório e CI; Render Free e Supabase Free previstos para a publicação (`render.yaml`) | Sem cobrança na configuração atual do protótipo. As condições e os limites dos planos gratuitos não foram reconferidos nesta revisão e devem ser verificados na publicação (#64) |
| Implementação | Esforço humano de análise, código, testes, documentação e revisão | Não medido. As estimativas do plano de conclusão (#58–#66) são previsões, não registro de horas |
| Operação | Manter a demonstração publicada: segredos, migrações, backup, monitoramento, resposta a falhas e acompanhamento dos limites de plano gratuito | Não medido. Fora dos limites gratuitos, ou com disponibilidade e retenção exigidas pela organização, passa a ter custo de serviço. A operação continua exigindo esforço humano mesmo dentro deles |

Para a organização, os custos de descoberta, conectores reais, identidade corporativa, operação e qualidade de dados continuam desconhecidos (ver "Análise de viabilidade").

## Premissas para validação docente

As regras abaixo estão implementadas e testadas, mas os valores são premissas do projeto, não dados da Localiza.

| Premissa | Onde está no código | Teste |
|---|---|---|
| A fatura vence 10 dias após a data UTC do fato (`occurredAt`) | `finance/domain.py` (`PAYMENT_TERM_DAYS`) | `tests/test_finance.py::test_vencimento_usa_data_utc_e_so_vence_depois_do_dia` |
| O encerramento fatura por ciclos iniciados (mensal, trimestral e anual) | `finance/domain.py` (`CYCLE_MONTHS`, `billed_cycles`) | `tests/test_finance.py::test_ciclos_iniciados` |
| O SLA é contado da abertura do chamado, e a prioridade não altera o prazo | `support/domain.py` (`due_at`) | `tests/test_t15_atendimento.py::test_prazo_e_estado_de_sla_sao_deterministicos_com_o_relogio` |
| A preparação de retirada vence 72 h após o evento de ativação, sem extensão por despacho atrasado | `workflow/domain.py` (`PREPARATION_HOURS`) | `tests/test_workflow.py::test_preparacao_vence_72h_apos_a_ativacao_mesmo_com_despacho_atrasado` |

## Conclusão de viabilidade

A proposta é viável para o protótipo acadêmico porque concentra a operação em
um único implantável e demonstra os três fluxos com componentes reproduzíveis. A viabilidade para a
organização permanece condicionada à validação de produtos, interfaces,
volumes, SLAs, segurança, equipe, prazo e custo.

Essa conclusão não pressupõe economia financeira nem capacidade produtiva. A
equipe deve levantar a linha de base, executar uma prova com sistemas reais e
comparar os indicadores antes de aprovar uma implantação organizacional.
