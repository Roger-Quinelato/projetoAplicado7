# Visão de negócio e viabilidade

> Estado de execução em 27/09/2026: consulte [Estado da implementação](ESTADO_IMPLEMENTACAO.md) e [Cronograma executável](CRONOGRAMA_EXECUCAO.md). As seções de desenho abaixo incluem metas futuras e premissas acadêmicas; o código e os testes são a evidência do comportamento atual.

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

Sem uma identidade compartilhada e reservas e contratos de integração, cada área pode
trabalhar com uma versão diferente do cliente, do contrato ou do SLA. A ausência
de correlação e recuperação uniforme também aumenta o tempo necessário para
localizar e corrigir falhas.

## Proposta de valor

A arquitetura cria uma referência global de cliente e conecta os processos por
APIs e eventos versionados. Cada sistema mantém a propriedade de seus dados, e a
camada de integração registra tradução, entrega, correlação e falhas. A proposta
reduz recadastro e torna ativação, cobrança, preparação de retirada e atendimento e assistência 24h
rastreáveis sem substituir integralmente os cinco sistemas.

## Benefícios e indicadores

Os benefícios esperados precisam ser comparados com uma linha de base da
organização. O guia não fornece essa linha de base; portanto, o projeto não
estima percentuais de ganho ou economia.

| Benefício esperado | Indicador proposto | Dado necessário |
|---|---|---|
| Reduzir recadastro e duplicidade | Percentual de reservas e contratos que exigem novo cadastro do cliente | Quantidade atual de reservas e contratos e recadastros |
| Coordenar ativação da locação, cobrança e preparação de retirada | Tempo entre ativação, primeira cobrança da locação e início do processo | Horários registrados pelos sistemas atuais |
| Aplicar o SLA contratado | Percentual de chamados com SLA incorreto ou não confirmado | Histórico de chamados e reservas e contratos |
| Evitar efeitos duplicados | Cobranças, processos ou chamados duplicados por reentrega | Ocorrências atuais e registros de integração |
| Acelerar diagnóstico e recuperação | Tempo médio para localizar a causa e reprocessar uma falha | Histórico operacional e tempos de atendimento e assistência 24h |
| Facilitar mudanças | Quantidade de sistemas afetados por alteração de contrato | Histórico de mudanças e dependências atuais |

## Análise de viabilidade

| Dimensão | Por que a proposta é viável para a primeira entrega | Condição ou risco para adoção organizacional |
|---|---|---|
| Custos | O monólito modular limita a quantidade de unidades de implantação. Simuladores permitem demonstrar os fluxos sem licenças ou ambientes legados. | Descoberta, conectores reais, identidade corporativa, operação e qualidade de dados geram custos ainda não informados. |
| Complexidade | Um processo reúne os módulos, enquanto portas, adaptadores e reservas e contratos preservam as fronteiras. | Outbox, inbox, mensageria, idempotência e observabilidade exigem disciplina técnica e suporte operacional. |
| Infraestrutura | Docker Compose reproduz API, PostgreSQL e RabbitMQ para a demonstração. | Produção exige definição de hospedagem, TLS, backup, disponibilidade, monitoramento e capacidade. |
| Equipe | A equipe júnior consegue concentrar a primeira entrega nos três fluxos, reservas e contratos e evidências. | Papéis, disponibilidade, experiência com os produtos legados e suporte após implantação são **Premissa a validar**. |
| Prazo | A priorização P0 limita o trabalho aos requisitos e fluxos necessários para a avaliação. | O guia não define duração para integração real; acesso a ambientes e validação com responsáveis podem alterar o cronograma. |
| Necessidades futuras | Portas e adaptadores permitem integrar novos sistemas; contratos versionados e consumidores idempotentes preservam evolução. | Extração de serviços, particionamento e escala horizontal dependem de métricas e de novo ADR quando houver mudança estrutural. |

## Conclusão de viabilidade

A proposta é viável para o protótipo acadêmico porque reduz a carga operacional
e demonstra os três fluxos com componentes reproduzíveis. A viabilidade para a
organização permanece condicionada à validação de produtos, interfaces,
volumes, SLAs, segurança, equipe, prazo e custo.

Essa conclusão não pressupõe economia financeira nem capacidade produtiva. A
equipe deve levantar a linha de base, executar uma prova com sistemas reais e
comparar os indicadores antes de aprovar uma implantação organizacional.
