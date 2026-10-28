import fs from "node:fs/promises";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

// Raiz do repositório a partir deste arquivo; o runtime de apresentações pode ser trocado por PRESENTATIONS_SKILL_DIR.
const workspaceDir = (process.env.ARCHCORP_ROOT ?? path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")).replaceAll("\\", "/");
const SKILL_DIR = process.env.PRESENTATIONS_SKILL_DIR ?? "C:/Users/roger/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations";
const IMG_DIR = path.join(workspaceDir, "docs/arquitetura/img");
// Preencha antes da submissão, na mesma ordem do relatório (tools/build_report.py, EQUIPE).
const EQUIPE = [];
const TMP_DIR = path.join(workspaceDir, "tmp/presentation-build");
const FINAL_PPTX = path.join(workspaceDir, "output/Apresentacao_Cenario_4.pptx");
const VALIDATED_PPTX = path.join(TMP_DIR, "Apresentacao_Cenario_4_validada.pptx");
const RUNTIME_PYTHON = "C:/Users/roger/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const utils = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const { resolvePresentationFont, makeNativeBulletParagraphs, finalizePresentation } = utils;

await fs.mkdir(TMP_DIR, { recursive: true });
const family = resolvePresentationFont();
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { navy: "#17365D", ink: "#17212B", teal: "#227C83", rust: "#C65D3A", pale: "#EEF3F7", white: "#FFFFFF", gray: "#657786", green: "#2E7D5B" };

function base(title, section = "Projeto Aplicado Cenário 4", titleSize = 42) {
  const slide = deck.slides.add();
  slide.background.fill = C.white;
  const band = slide.shapes.add({ geometry: "rect", position: { left: 0, top: 0, width: 22, height: 720 }, fill: C.teal, line: { fill: "none", width: 0 } });
  const heading = slide.shapes.add({ geometry: "textbox", position: { left: 70, top: 38, width: 1110, height: 68 }, fill: "none", line: { fill: "none", width: 0 } });
  heading.text = title;
  heading.text.style = { typeface: family, fontSize: titleSize, bold: true, color: C.navy, autoFit: "none" };
  const sectionText = slide.shapes.add({ geometry: "textbox", position: { left: 72, top: 674, width: 1080, height: 24 }, fill: "none", line: { fill: "none", width: 0 } });
  sectionText.text = section;
  sectionText.text.style = { typeface: family, fontSize: 16, color: C.gray, autoFit: "none" };
  return slide;
}

function textbox(slide, text, pos, size = 25, color = C.ink, bold = false) {
  const shape = slide.shapes.add({ geometry: "textbox", position: pos, fill: "none", line: { fill: "none", width: 0 } });
  shape.text = text;
  shape.text.style = { typeface: family, fontSize: size, color, bold, autoFit: "none" };
  return shape;
}

function bullets(slide, items, pos, size = 24) {
  const shape = slide.shapes.add({ geometry: "textbox", position: pos, fill: "none", line: { fill: "none", width: 0 } });
  shape.text = makeNativeBulletParagraphs(items, { marginLeftPoints: 20, hangingPoints: 10, spaceAfterPoints: 10 });
  shape.text.style = { typeface: family, fontSize: size, color: C.ink, autoFit: "none" };
  return shape;
}

function box(slide, text, pos, fill = C.pale, color = C.ink) {
  const shape = slide.shapes.add({ geometry: "roundRect", position: pos, fill, line: { style: "solid", fill: "#CBD6DF", width: 1 }, borderRadius: 14 });
  shape.text = text;
  shape.text.style = { typeface: family, fontSize: 22, bold: true, color, autoFit: "none" };
  return shape;
}

function diagram(slide, name, alt, pos) {
  // Bytes embutidos: a referência por caminho gerava mídia vazia no PPTX.
  const blob = new Uint8Array(readFileSync(path.join(IMG_DIR, `${name}.png`)));
  return slide.images.add({ blob, contentType: "image/png", alt, fit: "contain", position: pos });
}

function notes(slide, text) {
  slide.speakerNotes.textFrame.setText(text);
}

// 1
{
  const slide = deck.slides.add();
  slide.background.fill = C.navy;
  textbox(slide, "Arquitetura de Integração\npara Empresa de Serviços", { left: 90, top: 170, width: 900, height: 190 }, 54, C.white, true);
  textbox(slide, "Projeto Aplicado  |  Cenário 4", { left: 94, top: 390, width: 600, height: 50 }, 27, "#C8DFE2");
  const accent = slide.shapes.add({ geometry: "rect", position: { left: 95, top: 130, width: 180, height: 10 }, fill: C.rust, line: { fill: "none", width: 0 } });
  textbox(slide, `${EQUIPE.length ? EQUIPE.join(" · ") : "Equipe do Projeto Aplicado (nomes a preencher)"}\nOutubro de 2026`, { left: 94, top: 560, width: 1000, height: 70 }, 20, C.white);
  notes(slide, "Fonte principal: Projeto Aplicado ArchCorp, enunciado acadêmico, 2026. Cenário 4 aplicado a uma locadora fictícia inspirada na Localiza, com dados sintéticos.");
}

// 2
{
  const slide = base("Cenário e problema");
  bullets(slide, ["Cinco sistemas corporativos com integrações insuficientes", "Duplicidade e lançamentos manuais entre áreas", "Falhas difíceis de rastrear e processos fragmentados", "Primeira entrega exige arquitetura e três fluxos funcionando"], { left: 80, top: 145, width: 590, height: 390 }, 27);
  box(slide, "CRM", { left: 760, top: 140, width: 180, height: 70 }, C.pale);
  box(slide, "Reservas e contratos", { left: 960, top: 235, width: 190, height: 70 }, C.pale);
  box(slide, "Financeiro e faturamento", { left: 760, top: 330, width: 180, height: 70 }, C.pale);
  box(slide, "Atendimento e assistência 24h", { left: 960, top: 425, width: 190, height: 70 }, C.pale);
  box(slide, "Processos", { left: 760, top: 520, width: 180, height: 70 }, C.pale);
  notes(slide, "Fonte: enunciado acadêmico, páginas 1 a 3. Produtos, tecnologias e fluxos atuais específicos permanecem como premissas a validar.");
}

// 3
{
  const slide = base("Arquitetura atual AS IS");
  textbox(slide, "Premissa de modelagem", { left: 80, top: 120, width: 420, height: 40 }, 24, C.rust, true);
  diagram(slide, "as_is", "Diagrama AS-IS com trocas manuais entre CRM, contratos, financeiro, atendimento e processos", { left: 70, top: 175, width: 1140, height: 255 });
  textbox(slide, "Recadastro, planilhas e lançamentos manuais ligam as áreas. O enunciado confirma os sistemas e os problemas gerais, mas não informa as interfaces atuais.", { left: 110, top: 470, width: 1030, height: 120 }, 25, C.ink);
  notes(slide, "Fonte: docs/arquitetura/AS_IS.md e enunciado acadêmico. A sequência ilustrada é uma hipótese explícita para a demonstração.");
}

// 4
{
  const slide = base("Requisitos prioritários");
  bullets(slide, ["RF 01 a RF 02: identidade global e contrato sem recadastro", "RF 03: ativação cria cobrança e preparação de retirada sem duplicidade", "RF 04: chamado consulta contrato, grupo de veículo e SLA", "RF 05 a RF 07: propagação cadastral, correlação e reprocessamento"], { left: 75, top: 145, width: 700, height: 380 }, 25);
  textbox(slide, "Qualidade", { left: 860, top: 145, width: 250, height: 44 }, 28, C.teal, true);
  bullets(slide, ["Interoperabilidade", "Confiabilidade", "Segurança", "Observabilidade", "Manutenibilidade", "Disponibilidade", "Desempenho"], { left: 840, top: 205, width: 330, height: 360 }, 23);
  notes(slide, "Fonte: PLANO_IMPLEMENTACAO_CENARIO_4.md, seção 5, e docs/MATRIZ_RASTREABILIDADE.md.");
}

// 5
{
  const slide = base("Decisão arquitetural");
  textbox(slide, "SOA pragmática em monólito modular", { left: 110, top: 145, width: 1000, height: 70 }, 36, C.navy, true);
  bullets(slide, ["Portas e adaptadores preservam as fronteiras dos contextos", "REST atende respostas imediatas; eventos representam fatos confirmados", "PostgreSQL e RabbitMQ sustentam a demonstração local", "Extração futura depende de métricas de escala, disponibilidade ou cadência"], { left: 130, top: 255, width: 1000, height: 310 }, 27);
  textbox(slide, "ADR 001 aceito para o protótipo acadêmico", { left: 130, top: 590, width: 800, height: 42 }, 22, C.rust, true);
  notes(slide, "Fonte: docs/adr/ADR-001-integracao-empresa-de-servicos.md. Opções consideradas: REST ponto a ponto, microsserviços completos, ESB central e monólito modular orientado a serviços.");
}

// 6
{
  const slide = base("Arquitetura proposta TO BE");
  diagram(slide, "to_be_componentes", "Diagrama de componentes: API, contextos, outbox, dispatcher, inbox e RabbitMQ", { left: 70, top: 115, width: 470, height: 545 });
  bullets(slide, ["Cinco contextos de negócio com dados próprios", "CustomerReader e ContractEntitlementPort ligam contextos por portas públicas", "Outbox, dispatcher e inbox entregam eventos sem duplicar efeitos", "Auditoria e correlationId atravessam toda a operação"], { left: 600, top: 150, width: 600, height: 380 }, 25);
  textbox(slide, "Um processo, fronteiras preservadas por interfaces públicas", { left: 600, top: 570, width: 600, height: 60 }, 23, C.rust, true);
  notes(slide, "Fonte: docs/arquitetura/TO_BE.md. Os conectores representam dependências por portas e eventos, não acesso direto a tabelas.");
}

// 6b
{
  const slide = base("Sistemas corporativos envolvidos");
  const rows = [
    ["CRM", "CRM operacional", "Fonte oficial do cliente; fornece dados a Contracts"],
    ["Reservas e contratos", "Sistema de contratos", "Reserva, contrato e SLA; publica eventos"],
    ["Financeiro e faturamento", "Módulo financeiro de ERP", "Faturas e pagamentos por eventos de contrato"],
    ["Atendimento 24h", "Sistema de atendimento", "Chamado com SLA consultado em Contracts"],
    ["Gestão de processos", "BPM / workflow", "Retirada e resolução iniciadas por eventos"],
  ];
  rows.forEach(([name, kind, role], i) => {
    const y = 135 + i * 100;
    box(slide, name, { left: 80, top: y, width: 300, height: 76 }, i % 2 ? C.pale : "#E7F2EF");
    textbox(slide, kind, { left: 410, top: y + 18, width: 280, height: 44 }, 23, C.teal, true);
    textbox(slide, role, { left: 700, top: y + 18, width: 500, height: 50 }, 21, C.ink);
  });
  notes(slide, "Fonte: relatório, seção 4.4, e docs/arquitetura/AS_IS.md. Categorias são o papel típico de cada sistema; produtos reais não foram informados.");
}

// 7
{
  const slide = base("Propriedade dos dados");
  const items = [
    ["CRM", "Cliente, contato, consentimento, perfil de locação e oportunidade corporativa"],
    ["Contracts", "Reserva, contrato de locação, grupo de veículo, vigência, proteções e SLA"],
    ["Finance", "Pré-autorização, cobrança, fatura, pagamento, caução, multa e inadimplência"],
    ["Support", "Chamado, assistência, prioridade, histórico e resolução"],
    ["Workflow", "Instância, tarefa, responsável, prazo e estado operacional"],
    ["Integration", "IDs legados, correlação, outbox, inbox e falhas"],
  ];
  items.forEach(([name, data], i) => {
    const y = 130 + i * 82;
    textbox(slide, name, { left: 90, top: y, width: 210, height: 45 }, 25, C.teal, true);
    textbox(slide, data, { left: 330, top: y, width: 820, height: 50 }, 23, C.ink);
  });
  notes(slide, "Fonte: AGENT.md, tabela de propriedade dos dados, e plano de implementação, seção 6.");
}

// 7b
{
  const slide = base("APIs e contratos");
  bullets(slide, [
    "POST /api/v1/contracts/reservations/{id}/draft  ·  F1",
    "POST /api/v1/contracts/{id}/activate  ·  F2",
    "POST /api/v1/support/tickets  ·  F3",
    "POST /api/v1/integration/outbox/dispatch  ·  entrega de eventos",
    "GET /api/v1/operations/{correlationId}  ·  trilha consolidada",
  ], { left: 80, top: 140, width: 760, height: 380 }, 23);
  box(slide, "OpenAPI 3.1\nSwagger em /docs", { left: 900, top: 150, width: 290, height: 120 }, C.navy, C.white);
  box(slide, "AsyncAPI 3.0\n6 eventos v1", { left: 900, top: 300, width: 290, height: 120 }, "#E7F2EF");
  box(slide, "problem+json\ncode e correlationId", { left: 900, top: 450, width: 290, height: 120 }, C.pale);
  textbox(slide, "Comandos repetíveis aceitam Idempotency-Key", { left: 80, top: 560, width: 760, height: 50 }, 24, C.rust, true);
  notes(slide, "Fonte: docs/api/openapi.yaml, docs/events/asyncapi.yaml e docs/EXEMPLOS_API.md.");
}

// 8
{
  const slide = base("Fluxo F1 Cliente para reserva/contrato");
  const crm = box(slide, "CRM\ncliente elegível", { left: 100, top: 245, width: 220, height: 110 }, C.pale);
  const api = box(slide, "POST\n/contracts/drafts", { left: 430, top: 245, width: 250, height: 110 }, C.navy, C.white);
  const ct = box(slide, "Contracts\nrascunho DRAFT", { left: 800, top: 245, width: 250, height: 110 }, "#E7F2EF");
  slide.shapes.connect(crm, api, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(api, ct, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  textbox(slide, "Idempotency Key devolve o mesmo contractId em uma repetição", { left: 220, top: 420, width: 830, height: 55 }, 26, C.rust, true);
  textbox(slide, "CRM fora do ar: retentativa limitada com jitter e 503 sem efeito", { left: 220, top: 490, width: 830, height: 55 }, 24, C.ink);
  textbox(slide, "Roteiro demo_f1.py: 20 de 20 checagens", { left: 350, top: 570, width: 620, height: 50 }, 24, C.green, true);
  notes(slide, "Fonte: docs/INTEGRACOES.md, ADR-006 e scripts/demo_f1.py executado contra a API local em 17/10/2026.");
}

// 9
{
  const slide = base("Fluxo F2 Ativação cobrança e preparação de retirada", "Projeto Aplicado Cenário 4", 36);
  const ct = box(slide, "Contracts\nACTIVE", { left: 80, top: 260, width: 200, height: 100 }, C.pale);
  const outbox = box(slide, "Outbox\nContractActivated", { left: 370, top: 260, width: 260, height: 100 }, C.navy, C.white);
  const finance = box(slide, "Finance\n1 cobrança", { left: 770, top: 180, width: 220, height: 90 }, "#E7F2EF");
  const workflow = box(slide, "Workflow\n1 preparação de retirada", { left: 770, top: 360, width: 220, height: 90 }, "#E7F2EF");
  slide.shapes.connect(ct, outbox, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(outbox, finance, { fromSide: "right", toSide: "left", kind: "elbow", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(outbox, workflow, { fromSide: "right", toSide: "left", kind: "elbow", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  textbox(slide, "Inbox e restrições únicas impedem efeitos duplicados", { left: 280, top: 510, width: 760, height: 55 }, 26, C.rust, true);
  textbox(slide, "Roteiro demo_f2.py: 14 de 14 checagens", { left: 380, top: 580, width: 620, height: 50 }, 24, C.green, true);
  notes(slide, "Fonte: docs/INTEGRACOES.md, teste test_f2_ativacao_cria_uma_cobranca_e_uma_preparacao_de_retirada e scripts/demo_f2.py.");
}

// 10
{
  const slide = base("Fluxo F3 Chamado com SLA");
  const support = box(slide, "Support\nabrir chamado", { left: 80, top: 250, width: 220, height: 100 }, C.pale);
  const contractsBox = box(slide, "Contracts\nelegibilidade e SLA", { left: 410, top: 160, width: 260, height: 100 }, C.navy, C.white);
  const ticket = box(slide, "Ticket\nOPEN ou PENDING", { left: 410, top: 365, width: 260, height: 100 }, "#E7F2EF");
  const workflow = box(slide, "Workflow\nresolução", { left: 820, top: 365, width: 230, height: 100 }, C.pale);
  slide.shapes.connect(support, contractsBox, { fromSide: "right", toSide: "left", kind: "elbow", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(contractsBox, ticket, { fromSide: "bottom", toSide: "top", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(ticket, workflow, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  textbox(slide, "Indisponibilidade preserva a solicitação para reconciliação", { left: 220, top: 520, width: 820, height: 50 }, 25, C.rust, true);
  textbox(slide, "Roteiro demo_f3.py: 15 de 15 checagens", { left: 380, top: 590, width: 620, height: 50 }, 24, C.green, true);
  notes(slide, "Fonte: docs/INTEGRACOES.md, testes de F3 e indisponibilidade e scripts/demo_f3.py.");
}

// 11
{
  const slide = base("Interoperabilidade e reservas e contratos");
  bullets(slide, ["UUID global com identificadores legados associados", "JSON UTF 8, UTC ISO 8601 e moeda explícita", "OpenAPI para REST e AsyncAPI para eventos", "Fonte oficial vence; divergência fica auditada", "Mudança incompatível cria uma nova versão"], { left: 95, top: 145, width: 720, height: 410 }, 26);
  box(slide, "eventId\neventType\neventVersion\noccurredAt\ncorrelationId\ncausationId\nproducer\npayload", { left: 900, top: 140, width: 250, height: 390 }, C.navy, C.white);
  textbox(slide, "Envelope obrigatório", { left: 920, top: 555, width: 250, height: 40 }, 23, C.teal, true);
  notes(slide, "Fonte: docs/events/asyncapi.yaml, docs/api/openapi.yaml e plano de implementação, seção 7.");
}

// 12a
{
  const slide = base("Análise de qualidade arquitetural");
  const head = ["Atributo", "Risco", "Estratégia", "Resultado"];
  const rows = [
    ["Interoperabilidade", "Cliente errado", "UUID global e IDs legados", "Mesma identidade"],
    ["Confiabilidade", "Cobrança dupla", "Outbox, inbox e idempotência", "Um efeito por fato"],
    ["Disponibilidade", "Chamado perdido", "Estado pendente", "Reconciliação"],
    ["Manutenibilidade", "Acoplamento", "Portas e teste de fronteira", "Mudança local"],
    ["Desempenho", "Latência", "API sem estado", "p95 local 4,22 ms"],
  ];
  const xs = [70, 360, 640, 960], ws = [280, 270, 310, 260];
  head.forEach((h, j) => textbox(slide, h, { left: xs[j], top: 125, width: ws[j], height: 40 }, 22, C.teal, true));
  rows.forEach((row, i) => row.forEach((cell, j) => textbox(slide, cell, { left: xs[j], top: 180 + i * 82, width: ws[j], height: 70 }, 20, j ? C.ink : C.navy, j === 0)));
  notes(slide, "Fonte: docs/ATRIBUTOS_QUALIDADE.md (nove atributos com necessidade, risco, estratégia, resultado e evidência) e relatório, seção 4.8.");
}

// 12
{
  const slide = base("Confiabilidade segurança e observabilidade");
  textbox(slide, "Confiabilidade", { left: 90, top: 145, width: 300, height: 45 }, 27, C.teal, true);
  bullets(slide, ["Outbox e inbox", "Idempotency Key", "Fila de falha e reprocessamento"], { left: 85, top: 210, width: 340, height: 220 }, 22);
  textbox(slide, "Segurança", { left: 475, top: 145, width: 260, height: 45 }, 27, C.teal, true);
  bullets(slide, ["Tokens locais ou segredo público e RBAC", "Validação na fronteira", "Dados mínimos em logs e eventos"], { left: 470, top: 210, width: 340, height: 220 }, 22);
  textbox(slide, "Observabilidade", { left: 850, top: 145, width: 300, height: 45 }, 27, C.teal, true);
  bullets(slide, ["Correlação ponta a ponta", "Logs JSON e métricas", "Health checks e auditoria"], { left: 845, top: 210, width: 340, height: 220 }, 22);
  textbox(slide, "Falha permanente testada após três tentativas e reprocessamento auditado", { left: 170, top: 505, width: 930, height: 70 }, 26, C.rust, true);
  notes(slide, "Fonte: docs/ATRIBUTOS_QUALIDADE.md e docs/EVIDENCIAS_VALIDACAO.md.");
}

// 13
{
  const slide = base("Escalabilidade manutenção e evolução");
  textbox(slide, "Escalabilidade", { left: 80, top: 140, width: 340, height: 45 }, 26, C.teal, true);
  bullets(slide, ["Réplicas da API sem estado", "Consumidores idempotentes por fila", "Extração só com métricas e ADR"], { left: 75, top: 200, width: 360, height: 300 }, 21);
  textbox(slide, "Manutenção", { left: 470, top: 140, width: 340, height: 45 }, 26, C.teal, true);
  bullets(slide, ["Mudança no contexto proprietário", "Novos sistemas por adaptadores", "Testes de contrato e de fronteira"], { left: 465, top: 200, width: 360, height: 300 }, 21);
  textbox(slide, "Evolução", { left: 860, top: 140, width: 340, height: 45 }, 26, C.teal, true);
  bullets(slide, ["Contratos aditivos; quebra cria v2", "Migrações aditivas (ADR-002)", "Atualização gradual por versão"], { left: 855, top: 200, width: 360, height: 300 }, 21);
  textbox(slide, "Viabilidade: um implantável, componentes gratuitos e equipe júnior; custos reais a levantar", { left: 110, top: 540, width: 1060, height: 70 }, 23, C.rust, true);
  notes(slide, "Fonte: docs/EVOLUCAO_MANUTENCAO.md (sete perguntas do enunciado) e docs/VISAO_NEGOCIO.md. Indicadores: tempo de ativação, recadastro, SLA incorreto, falhas por integração e tempo de diagnóstico.");
}

// 14
{
  const slide = base("Demonstração e resultados");
  textbox(slide, "211 testes aprovados", { left: 105, top: 145, width: 520, height: 60 }, 34, C.green, true);
  textbox(slide, "p95  4,22 ms", { left: 800, top: 145, width: 330, height: 60 }, 34, C.green, true);
  bullets(slide, ["F1 cria rascunho sem recadastro: 20 de 20", "F2 cria uma cobrança e uma preparação de retirada: 14 de 14", "F3 registra SLA, resolve e conclui o processo: 15 de 15", "Falha controlada preserva e reconcilia o chamado", "Rastreabilidade reúne auditoria e eventos"], { left: 170, top: 250, width: 960, height: 300 }, 26);
  textbox(slide, "Premissas do AS IS seguem para validação com a organização", { left: 250, top: 590, width: 800, height: 42 }, 23, C.rust, true);
  notes(slide, "Fonte: docs/EVIDENCIAS_VALIDACAO.md. Em 17/10/2026: 211 testes aprovados e 10 ignorados (PostgreSQL/RabbitMQ reais); roteiros demo_f1/f2/f3 contra uvicorn local; p95 de 200 consultas de prontidão em Windows 11, Python 3.12, SQLite.");
}

// 15
{
  const slide = base("Conclusões e próximos passos");
  textbox(slide, "Conclusões", { left: 90, top: 145, width: 430, height: 48 }, 29, C.teal, true);
  bullets(slide, ["A arquitetura integrou os três fluxos obrigatórios", "Reservas e contratos e fronteiras permitem evolução incremental", "Outbox, inbox e correlação tornam falhas recuperáveis"], { left: 85, top: 215, width: 520, height: 255 }, 24);
  textbox(slide, "Limites e evolução", { left: 700, top: 145, width: 430, height: 48 }, 29, C.teal, true);
  bullets(slide, ["Validar premissas e interfaces do AS IS", "Publicar e testar a demo gratuita com dados sintéticos", "Adicionar identidade individual e agendador de vencimentos"], { left: 695, top: 215, width: 500, height: 255 }, 24);
  textbox(slide, "Próxima ação: validar a solução com dados, volumes e responsáveis reais", { left: 165, top: 545, width: 950, height: 62 }, 25, C.rust, true);
  notes(slide, "Fonte: relatório técnico, seções 4.10 e 5, e docs/EVOLUCAO_MANUTENCAO.md. Inserir nomes e contribuições individuais antes da submissão.");
}

for (let i = 0; i < deck.slides.items.length; i++) {
  const slide = deck.slides.items[i];
  const png = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(TMP_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
}

const requirements = { explicitTotalSlideCount: 18, requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [] };
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
await fs.rm(VALIDATED_PPTX, { force: true });
await fs.rm(path.join(stagingDir, "Apresentacao_Cenario_4.validation.json"), { force: true });
const candidatePath = path.join(stagingDir, "cenario4-candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);
await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: VALIDATED_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "design", families: [family] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "Apresentacao_Cenario_4.validation.json"),
});
await fs.copyFile(VALIDATED_PPTX, FINAL_PPTX);
console.log(FINAL_PPTX);
