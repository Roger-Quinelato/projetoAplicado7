import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/ProjetoAplicado7";
const SKILL_DIR = "C:/Users/roger/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
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
  textbox(slide, "Equipe do Projeto Aplicado\n14 de setembro de 2026", { left: 94, top: 560, width: 520, height: 70 }, 20, C.white);
  notes(slide, "Fonte principal: Projeto Aplicado ArchCorp, enunciado acadêmico fornecido ao projeto, 2026.");
}

// 2
{
  const slide = base("Cenário e problema");
  bullets(slide, ["Cinco sistemas corporativos com integrações insuficientes", "Duplicidade e lançamentos manuais entre áreas", "Falhas difíceis de rastrear e processos fragmentados", "Primeira entrega exige arquitetura e três fluxos funcionando"], { left: 80, top: 145, width: 590, height: 390 }, 27);
  box(slide, "CRM", { left: 760, top: 140, width: 180, height: 70 }, C.pale);
  box(slide, "Contratos", { left: 960, top: 235, width: 190, height: 70 }, C.pale);
  box(slide, "Financeiro", { left: 760, top: 330, width: 180, height: 70 }, C.pale);
  box(slide, "Atendimento", { left: 960, top: 425, width: 190, height: 70 }, C.pale);
  box(slide, "Processos", { left: 760, top: 520, width: 180, height: 70 }, C.pale);
  notes(slide, "Fonte: enunciado acadêmico, páginas 1 a 3. Produtos, tecnologias e fluxos atuais específicos permanecem como premissas a validar.");
}

// 3
{
  const slide = base("Arquitetura atual AS IS");
  const nodes = [
    box(slide, "CRM", { left: 80, top: 210, width: 170, height: 85 }),
    box(slide, "Contratos", { left: 320, top: 210, width: 180, height: 85 }),
    box(slide, "Financeiro", { left: 570, top: 210, width: 180, height: 85 }),
    box(slide, "Atendimento", { left: 820, top: 210, width: 180, height: 85 }),
    box(slide, "Processos", { left: 1070, top: 210, width: 150, height: 85 }),
  ];
  for (let i = 0; i < nodes.length - 1; i++) slide.shapes.connect(nodes[i], nodes[i + 1], { kind: "straight", fromSide: "right", toSide: "left", line: { style: "dashed", fill: C.rust, width: 2 }, tail: { type: "arrow", width: "sm", length: "sm" } });
  textbox(slide, "Premissa de modelagem", { left: 80, top: 130, width: 420, height: 40 }, 24, C.rust, true);
  textbox(slide, "Recadastro, planilhas ou integrações específicas ligam as áreas. O enunciado confirma os sistemas e os problemas gerais, mas não informa as interfaces atuais.", { left: 110, top: 360, width: 1030, height: 140 }, 26, C.ink);
  notes(slide, "Fonte: docs/arquitetura/AS_IS.md e enunciado acadêmico. A sequência ilustrada é uma hipótese explícita para a demonstração.");
}

// 4
{
  const slide = base("Requisitos prioritários");
  bullets(slide, ["RF 01 a RF 02: identidade global e contrato sem recadastro", "RF 03: ativação cria cobrança e onboarding sem duplicidade", "RF 04: chamado consulta contrato, serviço e SLA", "RF 05 a RF 07: propagação cadastral, correlação e reprocessamento"], { left: 75, top: 145, width: 700, height: 380 }, 25);
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
  const api = box(slide, "API REST v1", { left: 535, top: 125, width: 210, height: 70 }, C.navy, C.white);
  const modules = ["CRM", "Contracts", "Finance", "Support", "Workflow"].map((name, i) => box(slide, name, { left: 80 + i * 235, top: 285, width: 180, height: 78 }, C.pale));
  for (const m of modules) slide.shapes.connect(api, m, { fromSide: "bottom", toSide: "top", kind: "elbow", line: { style: "solid", fill: C.teal, width: 2 }, tail: { type: "arrow", width: "sm", length: "sm" } });
  const integration = box(slide, "Integration\nOutbox  Inbox  Auditoria", { left: 390, top: 465, width: 500, height: 95 }, "#E7F2EF");
  for (const m of modules) slide.shapes.connect(m, integration, { fromSide: "bottom", toSide: "top", kind: "elbow", line: { style: "solid", fill: C.gray, width: 1.5 } });
  textbox(slide, "Um processo, fronteiras preservadas por interfaces públicas", { left: 310, top: 590, width: 690, height: 44 }, 23, C.rust, true);
  notes(slide, "Fonte: docs/arquitetura/TO_BE.md. Os conectores representam dependências por portas e eventos, não acesso direto a tabelas.");
}

// 7
{
  const slide = base("Propriedade dos dados");
  const items = [
    ["CRM", "Cliente, contato, consentimento e oportunidade"],
    ["Contracts", "Contrato, itens, vigência, plano e SLA"],
    ["Finance", "Cobrança, vencimento, pagamento e inadimplência"],
    ["Support", "Chamado, prioridade, histórico e resolução"],
    ["Workflow", "Instância, tarefa, responsável, prazo e estado"],
    ["Integration", "IDs legados, correlação, outbox, inbox e falhas"],
  ];
  items.forEach(([name, data], i) => {
    const y = 130 + i * 82;
    textbox(slide, name, { left: 90, top: y, width: 210, height: 45 }, 25, C.teal, true);
    textbox(slide, data, { left: 330, top: y, width: 820, height: 50 }, 23, C.ink);
  });
  notes(slide, "Fonte: AGENT.md, tabela de propriedade dos dados, e plano de implementação, seção 6.");
}

// 8
{
  const slide = base("Fluxo F1 Cliente para contrato");
  const crm = box(slide, "CRM\ncliente elegível", { left: 100, top: 245, width: 220, height: 110 }, C.pale);
  const api = box(slide, "POST\n/contracts/drafts", { left: 430, top: 245, width: 250, height: 110 }, C.navy, C.white);
  const ct = box(slide, "Contracts\nrascunho DRAFT", { left: 800, top: 245, width: 250, height: 110 }, "#E7F2EF");
  slide.shapes.connect(crm, api, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(api, ct, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  textbox(slide, "Idempotency Key devolve o mesmo contractId em uma repetição", { left: 220, top: 440, width: 830, height: 55 }, 26, C.rust, true);
  textbox(slide, "Resultado testado: rascunho sem recadastro", { left: 350, top: 535, width: 620, height: 50 }, 24, C.green, true);
  notes(slide, "Fonte: docs/INTEGRACOES.md e teste test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia.");
}

// 9
{
  const slide = base("Fluxo F2 Ativação cobrança e onboarding", "Projeto Aplicado Cenário 4", 36);
  const ct = box(slide, "Contracts\nACTIVE", { left: 80, top: 260, width: 200, height: 100 }, C.pale);
  const outbox = box(slide, "Outbox\nContractActivated", { left: 370, top: 260, width: 260, height: 100 }, C.navy, C.white);
  const finance = box(slide, "Finance\n1 cobrança", { left: 770, top: 180, width: 220, height: 90 }, "#E7F2EF");
  const workflow = box(slide, "Workflow\n1 onboarding", { left: 770, top: 360, width: 220, height: 90 }, "#E7F2EF");
  slide.shapes.connect(ct, outbox, { fromSide: "right", toSide: "left", kind: "straight", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(outbox, finance, { fromSide: "right", toSide: "left", kind: "elbow", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  slide.shapes.connect(outbox, workflow, { fromSide: "right", toSide: "left", kind: "elbow", line: { style: "solid", fill: C.teal, width: 3 }, tail: { type: "arrow", width: "med", length: "med" } });
  textbox(slide, "Inbox e restrições únicas impedem efeitos duplicados", { left: 280, top: 530, width: 760, height: 55 }, 26, C.rust, true);
  notes(slide, "Fonte: docs/INTEGRACOES.md e teste test_f2_ativacao_cria_uma_cobranca_e_um_onboarding.");
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
  textbox(slide, "Indisponibilidade preserva a solicitação para reconciliação", { left: 220, top: 550, width: 820, height: 50 }, 25, C.rust, true);
  notes(slide, "Fonte: docs/INTEGRACOES.md e testes de F3 e indisponibilidade.");
}

// 11
{
  const slide = base("Interoperabilidade e contratos");
  bullets(slide, ["UUID global com identificadores legados associados", "JSON UTF 8, UTC ISO 8601 e moeda explícita", "OpenAPI para REST e AsyncAPI para eventos", "Fonte oficial vence; divergência fica auditada", "Mudança incompatível cria uma nova versão"], { left: 95, top: 145, width: 720, height: 410 }, 26);
  box(slide, "eventId\neventType\neventVersion\noccurredAt\ncorrelationId\ncausationId\nproducer\npayload", { left: 900, top: 140, width: 250, height: 390 }, C.navy, C.white);
  textbox(slide, "Envelope obrigatório", { left: 920, top: 555, width: 250, height: 40 }, 23, C.teal, true);
  notes(slide, "Fonte: docs/events/asyncapi.yaml, docs/api/openapi.yaml e plano de implementação, seção 7.");
}

// 12
{
  const slide = base("Confiabilidade segurança e observabilidade");
  textbox(slide, "Confiabilidade", { left: 90, top: 145, width: 300, height: 45 }, 27, C.teal, true);
  bullets(slide, ["Outbox e inbox", "Idempotency Key", "Fila de falha e reprocessamento"], { left: 85, top: 210, width: 340, height: 220 }, 22);
  textbox(slide, "Segurança", { left: 475, top: 145, width: 260, height: 45 }, 27, C.teal, true);
  bullets(slide, ["OIDC simulado e RBAC", "Validação na fronteira", "Dados mínimos em logs e eventos"], { left: 470, top: 210, width: 340, height: 220 }, 22);
  textbox(slide, "Observabilidade", { left: 850, top: 145, width: 300, height: 45 }, 27, C.teal, true);
  bullets(slide, ["Correlação ponta a ponta", "Logs JSON e métricas", "Health checks e auditoria"], { left: 845, top: 210, width: 340, height: 220 }, 22);
  textbox(slide, "Falha permanente testada após três tentativas e reprocessamento auditado", { left: 170, top: 505, width: 930, height: 70 }, 26, C.rust, true);
  notes(slide, "Fonte: docs/ATRIBUTOS_QUALIDADE.md e docs/EVIDENCIAS_VALIDACAO.md.");
}

// 13
{
  const slide = base("Evolução e viabilidade");
  bullets(slide, ["Novos sistemas entram por adaptadores", "Campos opcionais permitem evolução compatível", "API sem estado e consumidores por fila permitem escala", "Extração de módulo exige métricas e novo ADR", "Docker Compose limita custo da demonstração"], { left: 90, top: 145, width: 720, height: 390 }, 27);
  textbox(slide, "Indicadores", { left: 890, top: 145, width: 240, height: 45 }, 28, C.teal, true);
  bullets(slide, ["Tempo de ativação", "Recadastro", "SLA incorreto", "Falhas por integração", "Tempo de diagnóstico"], { left: 850, top: 220, width: 330, height: 330 }, 23);
  notes(slide, "Fonte: docs/EVOLUCAO_MANUTENCAO.md e docs/VISAO_NEGOCIO.md.");
}

// 14
{
  const slide = base("Demonstração e resultados");
  textbox(slide, "13 testes aprovados", { left: 105, top: 145, width: 380, height: 60 }, 34, C.green, true);
  textbox(slide, "p95  6,36 ms", { left: 800, top: 145, width: 330, height: 60 }, 34, C.green, true);
  bullets(slide, ["F1 cria rascunho sem recadastro", "F2 cria uma cobrança e um onboarding", "F3 registra SLA e inicia resolução", "Falha controlada preserva e reconcilia o chamado", "Rastreabilidade reúne auditoria e eventos"], { left: 170, top: 250, width: 900, height: 300 }, 28);
  textbox(slide, "Premissas do AS IS seguem para validação com a organização", { left: 250, top: 590, width: 800, height: 42 }, 23, C.rust, true);
  notes(slide, "Fonte: docs/EVIDENCIAS_VALIDACAO.md. Medição local em 13 de setembro de 2026 com 200 consultas de prontidão.");
}

// 15
{
  const slide = base("Conclusões e próximos passos");
  textbox(slide, "Conclusões", { left: 90, top: 145, width: 430, height: 48 }, 29, C.teal, true);
  bullets(slide, ["A arquitetura integrou os três fluxos obrigatórios", "Contratos e fronteiras permitem evolução incremental", "Outbox, inbox e correlação tornam falhas recuperáveis"], { left: 85, top: 215, width: 520, height: 255 }, 24);
  textbox(slide, "Limites e evolução", { left: 700, top: 145, width: 430, height: 48 }, 29, C.teal, true);
  bullets(slide, ["Validar premissas e interfaces do AS IS", "Conectar OIDC, TLS e sistemas reais por adaptadores", "Automatizar retentativas e sincronizar o prazo do Workflow"], { left: 695, top: 215, width: 500, height: 255 }, 24);
  textbox(slide, "Próxima ação: validar a solução com dados, volumes e responsáveis reais", { left: 165, top: 545, width: 950, height: 62 }, 25, C.rust, true);
  notes(slide, "Fonte: relatório técnico, seção 12, e docs/EVOLUCAO_MANUTENCAO.md. Inserir nomes e contribuições individuais antes da submissão.");
}

for (let i = 0; i < deck.slides.items.length; i++) {
  const slide = deck.slides.items[i];
  const png = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(TMP_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
}

const requirements = { explicitTotalSlideCount: 15, requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [] };
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
