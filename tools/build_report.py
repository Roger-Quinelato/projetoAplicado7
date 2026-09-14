from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "Relatorio_Tecnico_Cenario_4.docx"
NAVY = "17365D"
PALE = "EAF1F8"
GRAY = "D9D9D9"


def set_cell_fill(cell, color):
    props = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    props.append(shd)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    props = cell._tc.get_or_add_tcPr()
    margins = props.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        props.append(margins)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = OxmlElement(f"w:{name}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        margins.append(node)


def set_borders(table):
    props = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), GRAY)
        borders.append(el)
    props.append(borders)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Página ")
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])


def para(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p


def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.18)
        p.paragraph_format.space_after = Pt(4)
        p.add_run(f"•  {item}")
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for i, header in enumerate(headers):
        cell = t.rows[0].cells[i]
        set_cell_fill(cell, NAVY)
        run = cell.paragraphs[0].add_run(header)
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, value in enumerate(row):
            cells[ci].text = str(value)
            cells[ci].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cells[ci])
            if ri % 2:
                set_cell_fill(cells[ci], PALE)
            for p in cells[ci].paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for run in p.runs:
                    run.font.size = Pt(9)
    if widths:
        for row in t.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    set_borders(t)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def page(doc, title, level=1):
    heading = doc.add_heading(title, level=level)
    if len(doc.paragraphs) > 2:
        heading.paragraph_format.page_break_before = True
    heading.paragraph_format.space_before = Pt(8)
    heading.paragraph_format.space_after = Pt(12)


doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(0.72)
section.bottom_margin = Inches(0.72)
section.left_margin = Inches(0.8)
section.right_margin = Inches(0.8)

styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"].font.size = Pt(10.5)
styles["Title"].font.name = "Aptos Display"
styles["Title"].font.size = Pt(28)
styles["Title"].font.color.rgb = RGBColor(0, 0, 0)
title_ppr = styles["Title"].element.get_or_add_pPr()
for border in list(title_ppr.findall(qn("w:pBdr"))):
    title_ppr.remove(border)
for name, size in (("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 12)):
    styles[name].font.name = "Aptos Display"
    styles[name].font.size = Pt(size)
    styles[name].font.color.rgb = RGBColor(0, 0, 0)
    styles[name].font.bold = True

add_page_number(section.footer.paragraphs[0])

# Página 1
p = doc.add_paragraph(style="Title")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(115)
p.add_run("Arquitetura de Integração para Empresa de Serviços")
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.add_run("Projeto Aplicado Cenário 4").bold = True
sub.paragraph_format.space_before = Pt(18)
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.paragraph_format.space_before = Pt(150)
meta.add_run("Equipe do Projeto Aplicado\n14 de setembro de 2026\nRelatório técnico")

# Página 2
page(doc, "Resumo")
para(doc, "A organização do Cenário 4 utiliza CRM, sistema de contratos, sistema financeiro, sistema de atendimento e gestão de processos. O enunciado associa o crescimento da organização a duplicidade de dados, lançamentos manuais, integrações frágeis e processos fragmentados. Este trabalho propõe e implementa uma arquitetura orientada a serviços entregue como monólito modular, com APIs REST para interações imediatas e eventos para efeitos desacoplados.")
para(doc, "O método combinou análise do enunciado, levantamento de requisitos, modelagem AS-IS e TO-BE, registro de decisão arquitetural, implementação incremental e verificação automatizada. O protótipo separa os contextos CRM, Contracts, Finance, Support, Workflow e Integration. As fronteiras usam portas públicas; cada contexto controla seus dados e regras. A entrega confiável emprega outbox, inbox, idempotência, correlação e reprocessamento auditado.")
para(doc, "A avaliação executou 13 testes automatizados. Os três fluxos obrigatórios funcionaram do início ao fim: cliente do CRM para rascunho de contrato; ativação para cobrança e onboarding; e chamado com consulta de contrato e SLA. A repetição não duplicou efeitos, a indisponibilidade gerou um estado pendente reconciliável e o controle de papéis bloqueou uma operação indevida. Em 200 consultas locais de prontidão, o p95 foi 6,36 ms, abaixo da meta de 500 ms.")
para(doc, "Palavras-chave: arquitetura de sistemas corporativos; SOA; monólito modular; integração; REST; eventos; interoperabilidade.")

# Página 3
page(doc, "1 Introdução")
doc.add_heading("1.1 Contexto e problema", level=2)
para(doc, "A ArchCorp recebeu a tarefa de modernizar uma organização que acumulou aplicações distintas ao crescer. Para o Cenário 4, o documento define cinco sistemas: CRM, contratos, financeiro, atendimento e gestão de processos [1]. A falta de comunicação adequada cria duplicidade, recadastro, dificuldade de manutenção e baixa capacidade de evolução.")
para(doc, "O problema arquitetural envolve propriedade de dados e coordenação entre sistemas. Uma chamada bem-sucedida não basta quando uma ativação precisa produzir cobrança e onboarding, pois uma falha intermediária pode perder o fato ou repetir efeitos. A solução precisa definir contratos, responsabilidades, consistência e recuperação.")
doc.add_heading("1.2 Objetivos", level=2)
para(doc, "O objetivo geral consiste em demonstrar uma arquitetura executável que integre os cinco sistemas sem substituir suas capacidades completas. Os objetivos específicos abrangem identidade global de cliente, três fluxos integrados, contratos versionados, entrega idempotente, observabilidade, segurança, avaliação de qualidade e uma estratégia de evolução.")
doc.add_heading("1.3 Organização do relatório", level=2)
para(doc, "As seções seguintes apresentam fundamentação, método, análise AS-IS, requisitos, arquitetura TO-BE, integrações, qualidade, evolução, viabilidade, resultados e conclusões. Os anexos do repositório contêm OpenAPI, AsyncAPI, testes e roteiro de demonstração.")

# Página 4
page(doc, "2 Fundamentação teórica")
doc.add_heading("2.1 Arquitetura de sistemas", level=2)
para(doc, "Arquitetura de software organiza estruturas, responsabilidades e relações que condicionam atributos de qualidade. Bass, Clements e Kazman tratam decisões arquiteturais como instrumentos para responder a requisitos de qualidade e riscos [2]. Por isso, a solução não se limita a um diagrama: ela relaciona escolhas a cenários verificáveis.")
doc.add_heading("2.2 SOA e serviços", level=2)
para(doc, "A arquitetura orientada a serviços expõe capacidades por contratos estáveis. No projeto, serviço significa uma fronteira de negócio com interface pública e propriedade de dados. A implantação inicial pode reunir essas fronteiras em um processo sem eliminar sua separação lógica.")
doc.add_heading("2.3 Arquitetura hexagonal", level=2)
para(doc, "Portas definem o que a aplicação precisa ou oferece. Adaptadores conectam HTTP, banco, broker e sistemas externos. Essa direção mantém regras de domínio independentes de detalhes de infraestrutura e permite substituir simuladores por conectores reais.")
doc.add_heading("2.4 Monólito modular", level=2)
para(doc, "O monólito modular reduz a operação inicial e preserva limites internos que podem orientar uma extração futura. Newman recomenda justificar limites e distribuição pelas necessidades do sistema, pois a distribuição adiciona custo de comunicação, dados e operação [4].")

# Página 5
page(doc, "2 Fundamentação teórica continuação")
doc.add_heading("2.5 APIs e eventos", level=2)
para(doc, "HTTP define semântica para requisições e respostas [5]. O projeto usa REST quando o solicitante precisa conhecer o resultado imediato. Eventos representam fatos confirmados e permitem vários consumidores. A OpenAPI descreve as rotas e a AsyncAPI descreve canais, mensagens e payloads [6][7].")
doc.add_heading("2.6 Padrões de integração", level=2)
para(doc, "Hohpe e Woolf organizam mensageria por canais, mensagens, roteamento e transformação [3]. Outbox resolve a lacuna entre a transação de negócio e a publicação. Inbox registra o evento recebido por consumidor. A combinação oferece entrega ao menos uma vez sem repetir o efeito de negócio.")
doc.add_heading("2.7 Interoperabilidade", level=2)
para(doc, "Interoperabilidade exige mais que conectividade. Sistemas precisam concordar sobre identidade, significado, formato, versão, erro e fonte oficial. O modelo canônico deve conter somente os campos compartilhados pelo fluxo para não virar um modelo central rígido.")
doc.add_heading("2.8 Qualidade arquitetural", level=2)
para(doc, "Cenários de qualidade ligam estímulo, ambiente, resposta e medida. Este trabalho avalia interoperabilidade, confiabilidade, segurança, observabilidade, manutenibilidade, disponibilidade, desempenho, escalabilidade e testabilidade.")

# Página 6
page(doc, "3 Metodologia")
doc.add_heading("3.1 Participantes e contribuições", level=2)
para(doc, "A Equipe do Projeto Aplicado conduziu análise, modelagem, implementação, testes e documentação. O backlog organiza essas atividades em tarefas e subtarefas e mantém a relação entre requisito, responsável, resultado e evidência. A identificação nominal e a contribuição individual serão registradas pela equipe na versão de submissão.")
doc.add_heading("3.2 Recursos", level=2)
table(doc, ["Finalidade", "Recurso"], [
    ["Desenvolvimento", "Python, FastAPI e SQLAlchemy"],
    ["Persistência", "PostgreSQL na demonstração e SQLite nos testes"],
    ["Mensageria", "RabbitMQ e outbox persistida"],
    ["Contratos", "OpenAPI 3.1 e AsyncAPI 3.0"],
    ["Execução", "Docker Compose e PowerShell"],
    ["Verificação", "Pytest, testes de arquitetura e medição local"],
], [2.0, 4.7])
doc.add_heading("3.3 Procedimento", level=2)
para(doc, "O trabalho seguiu seis ciclos: descoberta; contratos e fundação; adaptadores; fluxos; qualidade; e entrega. Cada mudança relacionou requisito, decisão, implementação e evidência. A equipe tratou detalhes organizacionais ausentes como premissas e preservou o enunciado como fonte prioritária.")

# Página 7
page(doc, "4 Cenário atual AS IS")
para(doc, "O enunciado confirma os cinco sistemas, mas não identifica produtos, interfaces ou tecnologia. A análise separa essa evidência das premissas usadas para construir a demonstração. Essa distinção evita apresentar como observação uma troca manual que ainda precisa de entrevista.")
table(doc, ["Sistema", "Usuários", "Dados oficiais"], [
    ["CRM", "Comercial", "Cliente, contatos, consentimentos e oportunidade"],
    ["Contratos", "Jurídico e contratos", "Contrato, itens, vigência, plano e SLA"],
    ["Financeiro", "Financeiro", "Cobrança, vencimento, pagamento e inadimplência"],
    ["Atendimento", "Agentes", "Chamado, prioridade, histórico e resolução"],
    ["Gestão de processos", "Operações e gestão", "Instância, tarefa, responsável, prazo e estado"],
], [1.45, 1.65, 3.55])
para(doc, "A primeira hipótese de trabalho considera recadastro entre CRM e contratos. A segunda considera acionamento manual do financeiro e do onboarding após a ativação. A terceira considera que o atendimento consulta contrato e SLA por processo informal. O professor ou representante da organização deve validar essas hipóteses.")

# Página 8
page(doc, "4 Cenário atual AS IS continuação")
doc.add_heading("4.1 Fluxo e dependências", level=2)
table(doc, ["Etapa", "Origem", "Destino", "Risco atual"], [
    ["Venda", "CRM", "Contratos", "Recadastro e identificador divergente"],
    ["Ativação", "Contratos", "Financeiro", "Cobrança tardia ou ausente"],
    ["Onboarding", "Contratos", "Gestão de processos", "Início sem rastreabilidade"],
    ["Suporte", "Atendimento", "Contratos", "SLA incorreto ou indisponível"],
    ["Resolução", "Atendimento", "Gestão de processos", "Processo fragmentado"],
], [0.8, 1.25, 1.65, 2.8])
doc.add_heading("4.2 Necessidades", level=2)
bullets(doc, [
    "Uma identidade global que mantenha relações com identificadores legados.",
    "Contratos versionados para comandos, consultas e eventos.",
    "Entrega confiável com repetição segura e tratamento de falha permanente.",
    "Rastreabilidade por correlação, auditoria, métricas e logs estruturados.",
    "Fronteiras que preservem a fonte oficial e impeçam acesso cruzado ao banco.",
])
para(doc, "A análise AS-IS orienta a solução, mas a arquitetura admite adaptadores diferentes quando a descoberta real identificar APIs, arquivos, webhooks ou bancos legados.")

# Página 9
page(doc, "5 Requisitos")
table(doc, ["ID", "Requisito", "Critério de aceite"], [
    ["RF-01", "Identidade única de cliente", "UUID global e IDs legados associados"],
    ["RF-02", "Criar contrato a partir do CRM", "Rascunho sem recadastro"],
    ["RF-03", "Ativar, faturar e iniciar onboarding", "Efeitos únicos após repetição"],
    ["RF-04", "Abrir chamado com contrato e SLA", "Elegibilidade e prazo registrados"],
    ["RF-05", "Propagar cadastro", "Evento consumido e auditado"],
    ["RF-06", "Consultar operação", "Trilha por correlationId"],
    ["RF-07", "Reprocessar falha", "Motivo consultável e repetição segura"],
], [0.75, 2.35, 3.55])
para(doc, "Os requisitos não funcionais priorizam interoperabilidade, confiabilidade, segurança, observabilidade e manutenibilidade. Disponibilidade orienta a degradação do atendimento. A meta de desempenho fixa p95 inferior a 500 ms para consultas locais. Escalabilidade e testabilidade sustentam a evolução.")

# Página 10
page(doc, "6 Arquitetura proposta TO BE")
para(doc, "A decisão adota SOA pragmática em monólito modular. CRM, Contracts, Finance, Support e Workflow contêm regras e dados próprios. Integration mantém identidade legada, correlação, idempotência, outbox, inbox, auditoria e falhas. A aplicação oferece APIs em /api/v1.")
table(doc, ["Contexto", "Responsabilidade", "Interface"], [
    ["CRM", "Cadastro e elegibilidade", "CustomerReader"],
    ["Contracts", "Contrato, plano e SLA", "ContractEntitlementPort"],
    ["Finance", "Cobranças", "Consumidor de ContractActivated"],
    ["Support", "Chamados e reconciliação", "API de atendimento"],
    ["Workflow", "Onboarding e resolução", "Consumidores de eventos"],
    ["Integration", "Entrega e rastreabilidade", "API operacional"],
], [1.2, 2.55, 2.9])
para(doc, "O banco compartilhado pertence à implantação acadêmica. Prefixos e dependências de código preservam a separação lógica. Um teste de arquitetura rejeita importação direta de modelos internos entre contextos de negócio.")

# Página 11
page(doc, "6 Arquitetura proposta TO BE continuação")
doc.add_heading("6.1 Componentes e implantação", level=2)
para(doc, "Docker Compose inicia a API, PostgreSQL e RabbitMQ. A API atende canais e documentação. PostgreSQL persiste transações e registros de integração. RabbitMQ recebe cópias duráveis dos eventos para observação e integração externa. Os handlers internos demonstram consumidores substituíveis.")
table(doc, ["Camada", "Elementos", "Regra de dependência"], [
    ["Entrada", "Rotas REST, autenticação e validação", "Converte dados e chama casos de uso"],
    ["Aplicação", "Serviços de cada contexto", "Depende de portas públicas"],
    ["Domínio", "Estados e regras", "Não depende de HTTP ou broker"],
    ["Saída", "SQLAlchemy, RabbitMQ e logs", "Implementa adaptadores substituíveis"],
], [1.15, 2.6, 2.9])
doc.add_heading("6.2 Segurança", level=2)
para(doc, "O protótipo simula tokens OIDC e aplica papéis comercial, contratos, financeiro, atendimento, operações e administrador. Validação ocorre na fronteira. Eventos não carregam documentos, dados bancários ou descrição de chamado. O ambiente real deve usar um provedor OIDC e TLS no gateway.")

# Página 12
page(doc, "7 Integração F1 Cliente para contrato")
para(doc, "O comercial cria ou seleciona um cliente no CRM. O endpoint de rascunho recebe o UUID global, serviço, início, cobrança e SLA. Contracts consulta CustomerReader, valida elegibilidade e consentimento e cria o contrato sem copiar manualmente o cadastro.")
table(doc, ["Campo", "Origem", "Destino", "Regra"], [
    ["customerId", "CRM", "Contracts", "UUID global obrigatório"],
    ["serviceCode", "Oportunidade", "Contrato", "Código não vazio"],
    ["startsOn", "Venda", "Contrato", "Data ISO 8601"],
    ["amount", "Venda", "Contrato", "Decimal positivo"],
    ["currency", "Venda", "Contrato", "Três letras maiúsculas"],
    ["Idempotency-Key", "Cliente HTTP", "Integration", "Resposta original por operação"],
], [1.35, 1.45, 1.45, 2.4])
para(doc, "Uma repetição com a mesma chave devolve o mesmo contractId. A auditoria registra operação, resultado e correlação. O teste F1 comprovou o comportamento.")

# Página 13
page(doc, "8 Integração F2 Ativação e onboarding")
para(doc, "Contracts grava a ativação e ContractActivated.v1 na mesma transação. O dispatcher lê a outbox, entrega o evento a Finance e Workflow e registra uma inbox por consumidor. Depois publica o envelope no RabbitMQ quando configurado.")
table(doc, ["Consumidor", "Efeito", "Proteção contra duplicidade"], [
    ["Finance", "Primeira cobrança", "Contrato único na tabela financeira"],
    ["Workflow", "Processo de onboarding", "Tipo e referência únicos"],
    ["Integration", "Publicação e auditoria", "eventId por consumidor na inbox"],
], [1.45, 2.15, 3.05])
para(doc, "Uma falha mantém o evento pendente até nova chamada de despacho. Após três tentativas, o evento passa a FAILED com motivo e correlação. Um operador autorizado pode agendar o reprocessamento. A operação preserva o contador acumulado; uma nova falha retorna imediatamente a FAILED. Inbox e restrições únicas continuam válidas, portanto um efeito já confirmado não se repete.")
para(doc, "O teste F2 repetiu a ativação e o despacho e encontrou uma cobrança e um onboarding. Essa evidência atende ao requisito de demonstração de reentrega.")

# Página 14
page(doc, "9 Integração F3 Chamado com SLA")
para(doc, "Support consulta ContractEntitlementPort com cliente, contrato e serviço. Quando o contrato está ativo, o módulo registra o SLA, calcula o prazo e define prioridade alta para indisponibilidade ou segurança. TicketOpened.v1 inicia a resolução em Workflow.")
table(doc, ["Condição", "Estado do chamado", "Ação"], [
    ["Contrato e serviço válidos", "OPEN", "Registra SLA e publica evento"],
    ["Contrato inválido", "Sem criação", "Retorna erro de negócio 422"],
    ["Consulta indisponível", "PENDING_ENTITLEMENT", "Preserva solicitação"],
    ["Consulta restaurada", "OPEN ou REJECTED_ENTITLEMENT", "Reconcilia com auditoria"],
], [2.1, 2.0, 2.55])
para(doc, "O evento omite a descrição do chamado. Workflow recebe apenas os identificadores, categoria, prioridade, estado e SLA necessários ao processo. O teste de degradação abriu o chamado pendente e o reconciliou depois que Contracts voltou. A implementação atual não recalcula no Workflow o prazo criado enquanto a elegibilidade estava pendente.")

# Página 15
page(doc, "10 Qualidade arquitetural")
table(doc, ["Atributo", "Estratégia", "Evidência"], [
    ["Interoperabilidade", "UUID, formatos e contratos", "OpenAPI e AsyncAPI"],
    ["Confiabilidade", "Outbox, inbox e idempotência", "F2 sem duplicidade"],
    ["Segurança", "RBAC, validação e minimização", "Teste 403"],
    ["Observabilidade", "Correlação, logs, métricas e auditoria", "Consulta da operação"],
    ["Manutenibilidade", "Portas e teste de fronteira", "Zero importação cruzada"],
    ["Disponibilidade", "Estado pendente e reconciliação", "Teste de indisponibilidade"],
    ["Desempenho", "API sem estado e índices", "p95 de 6,36 ms"],
    ["Escalabilidade", "Consumidores idempotentes", "Escala por fila possível"],
    ["Testabilidade", "Suíte e adaptadores", "13 testes aprovados"],
], [1.35, 2.7, 2.6])
para(doc, "As medições representam o ambiente local e não substituem capacidade planejada com volumes reais. A equipe deve registrar hardware e amostra quando repetir o teste na apresentação.")

# Página 16
page(doc, "11 Evolução manutenção e viabilidade")
doc.add_heading("11.1 Evolução", level=2)
para(doc, "Novos módulos entram por portas e adaptadores. Mudanças compatíveis adicionam campos opcionais. Mudanças incompatíveis criam uma nova versão. Uma migração gradual adiciona estrutura antes do código consumidor, acompanha métricas e remove o formato antigo em outra versão.")
doc.add_heading("11.2 Escalabilidade", level=2)
para(doc, "A API sem estado pode receber réplicas. Consumidores idempotentes podem aumentar por fila. Particionamento ou extração de serviços exige métricas de volume, latência, disponibilidade ou cadência de implantação e um novo ADR.")
doc.add_heading("11.3 Valor e viabilidade", level=2)
para(doc, "A proposta reduz recadastro e conecta venda, ativação, cobrança, onboarding e atendimento. O monólito modular limita unidades de implantação, e os simuladores evitam licenças e ambientes legados na demonstração. A adoção organizacional ainda exige descoberta dos produtos, tratamento da qualidade dos dados, identidade corporativa, TLS, operação e capacidade.")
bullets(doc, ["Tempo entre ativação e cobrança", "Contratos com recadastro", "Chamados com SLA incorreto", "Falhas e tempo de diagnóstico"])
para(doc, "Custos, equipe, prazo e infraestrutura de produção não foram informados no enunciado. A viabilidade organizacional depende de levantar essa linha de base e comparar os indicadores antes e depois de uma prova com sistemas reais.")

# Página 17
page(doc, "12 Resultados e considerações finais")
doc.add_heading("12.1 Resultados", level=2)
para(doc, "A entrega implementou a arquitetura e produziu as evidências requeridas. Treze testes passaram. Os três fluxos integrados funcionaram; repetição não duplicou cobrança ou processo; falha de dependência preservou o chamado; e o reprocessamento manteve rastreabilidade. O OpenAPI expõe esquemas e exemplos, o AsyncAPI define o envelope completo e a API rejeita identificadores globais que não sejam UUID. O resultado atende ao propósito do enunciado de “demonstrar como a arquitetura e a integração funcionariam na prática” [1].")
para(doc, "Os componentes permanecem organizados por responsabilidade. REST atende decisões imediatas e eventos desacoplam os efeitos posteriores. O ADR registra por que a equipe evitou microsserviços completos e um ESB com regras centrais. A arquitetura permite evolução porque as portas e contratos continuam válidos quando um adaptador ou módulo muda.")
doc.add_heading("12.2 Desafios e aprendizados", level=2)
para(doc, "Os principais desafios foram preservar fronteiras mesmo com um banco e um processo compartilhados, coordenar efeitos assíncronos sem duplicidade e manter a mesma correlação em HTTP, auditoria e eventos. A implementação mostrou que contratos versionados não bastam sozinhos: outbox, inbox, idempotência, estados de recuperação e evidências precisam ser projetados junto com o fluxo.")
doc.add_heading("12.3 Limitações, riscos e evolução", level=2)
para(doc, "O principal limite decorre dos dados organizacionais ausentes. Produtos, volumes e interfaces reais podem alterar adaptadores, timeout e capacidade. O protótipo também não agenda retentativas com atraso, não oferece OIDC ou TLS reais e não recalcula o prazo do processo de resolução depois da reconciliação do chamado. O contador de tentativas permanece acumulado após o reprocessamento.")
para(doc, "Os próximos passos são validar o AS-IS, conectar identidade e sistemas reais por adaptadores, automatizar retentativas transitórias e sincronizar o prazo do Workflow após a reconciliação. Métricas de escala, disponibilidade ou cadência devem orientar qualquer extração futura. Decisões estruturais adicionais exigem novo ADR.")

# Página 18
page(doc, "Referências")
refs = [
    "[1] ARCHCORP. Projeto Aplicado ArchCorp Arquitetura de Sistemas Corporativos. Enunciado acadêmico fornecido ao projeto, 2026.",
    "[2] BASS, Len; CLEMENTS, Paul; KAZMAN, Rick. Software Architecture in Practice. 4. ed. Boston: Addison-Wesley, 2021.",
    "[3] HOHPE, Gregor; WOOLF, Bobby. Enterprise Integration Patterns. Boston: Addison-Wesley, 2003.",
    "[4] NEWMAN, Sam. Building Microservices. 2. ed. Sebastopol: O'Reilly Media, 2021.",
    "[5] IETF. RFC 9110 HTTP Semantics. Internet Engineering Task Force, 2022.",
    "[6] OPENAPI INITIATIVE. OpenAPI Specification version 3.1.1. 2024.",
    "[7] ASYNCAPI INITIATIVE. AsyncAPI Specification version 3.0.0. 2024.",
    "[8] NYGARD, Michael T. Release It. 2. ed. Raleigh: Pragmatic Bookshelf, 2018.",
]
for ref in refs:
    p = doc.add_paragraph(ref)
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.25)
    p.paragraph_format.space_after = Pt(9)
para(doc, "Documentos complementares do repositório: ADR-001; requisitos; plano de implementação; matriz de rastreabilidade; arquitetura AS-IS, TO-BE e fluxos de integração; exemplos de API; contratos OpenAPI e AsyncAPI; roteiro de demonstração; evidências de validação.")

doc.core_properties.title = "Arquitetura de Integração para Empresa de Serviços"
doc.core_properties.subject = "Projeto Aplicado Cenário 4"
doc.core_properties.author = "Equipe do Projeto Aplicado"
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
