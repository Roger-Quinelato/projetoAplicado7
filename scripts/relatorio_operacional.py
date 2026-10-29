"""Relatório operacional: transforma logs, métricas e auditoria em indicadores para decisão.

Lê somente endpoints públicos da API (resumos, insights de integração, /metrics e listagens)
e grava `output/insights/relatorio_operacional.md` e `.json`. Cada indicador traz a pergunta
de decisão, o valor medido e uma decisão sugerida por regra explícita. Não grava nada na API.

Uso (com a API no ar):
    python scripts/relatorio_operacional.py --base-url http://localhost:8000 --token demo-admin

As métricas de /metrics ficam em memória: o relatório reflete o processo desde o último
reinício da API. As listagens são limitadas a 200 itens; o relatório avisa quando o limite é atingido.
O token também pode vir de ARCHCORP_TOKEN e a URL de ARCHCORP_BASE_URL.
Saída: 0 com relatório gerado; 2 se a API estiver inacessível.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

LIST_LIMIT = 200
P95_TARGET_SECONDS = 0.5  # RNF-07
LAG_ATTENTION_SECONDS = 60.0
BREACH_ATTENTION_SHARE = 0.2
METRIC_LINE = re.compile(r'^(?P<name>archcorp_[a-z_]+)\{(?P<labels>[^}]*)\} (?P<value>[0-9.e+-]+)$')
LABEL = re.compile(r'([a-zA-Z_]+)="((?:[^"\\]|\\.)*)"')


def parse_metrics(text: str) -> list[tuple[str, dict, float]]:
    """Converte o texto Prometheus em (nome, rótulos, valor)."""
    samples = []
    for line in text.splitlines():
        match = METRIC_LINE.match(line)
        if match:
            samples.append((match["name"], dict(LABEL.findall(match["labels"])), float(match["value"])))
    return samples


def latency_by_operation(samples) -> list[dict]:
    """p95 estimado pelo histograma: limite superior do primeiro bucket que alcança 95%."""
    buckets: dict[str, list[tuple[float, float]]] = {}
    counts: dict[str, float] = {}
    for name, labels, value in samples:
        if name == "archcorp_request_latency_seconds_bucket":
            limit = float("inf") if labels["le"] == "+Inf" else float(labels["le"])
            buckets.setdefault(labels["operation"], []).append((limit, value))
        elif name == "archcorp_request_latency_seconds_count":
            counts[labels["operation"]] = value
    rows = []
    for operation, total in counts.items():
        if not total or operation.endswith("unmatched"):
            continue
        p95 = next(limit for limit, cumulative in sorted(buckets[operation]) if cumulative >= 0.95 * total)
        rows.append({"operation": operation, "requests": int(total), "p95UpperBoundSeconds": p95})
    return sorted(rows, key=lambda row: (-row["p95UpperBoundSeconds"], -row["requests"]))


class Report:
    def __init__(self, client: httpx.Client):
        self.client = client
        self.indicators: list[dict] = []
        self.warnings: list[str] = []

    def get(self, path: str, **params):
        response = self.client.get(path, params=params or None)
        if response.status_code != 200:
            self.warnings.append(f"{path} respondeu {response.status_code}; indicador incompleto.")
            return None
        return response.json() if "json" in response.headers.get("content-type", "") else response.text

    def listing(self, path: str) -> list:
        items = self.get(path) or []
        if len(items) >= LIST_LIMIT:
            self.warnings.append(f"{path} atingiu o limite de {LIST_LIMIT} itens; a proporção usa só os primeiros.")
        return items

    def add(self, name: str, question: str, value, decision: str, evidence: str) -> None:
        self.indicators.append({"indicador": name, "pergunta": question, "valor": value,
                                "decisaoSugerida": decision, "evidenciaGuia": evidence})

    def build(self) -> dict:
        state = self.get("/api/v1/demo/state") or {}
        contracts = self.get("/api/v1/contracts/summary") or {}
        invoices = self.listing("/api/v1/finance/invoices")
        tickets = self.listing("/api/v1/support/tickets")
        insights = self.get("/api/v1/integration/insights") or {}
        outbox = self.get("/api/v1/integration/outbox/summary") or {}
        samples = parse_metrics(self.get("/metrics") or "")

        paid = sum(invoice["status"] == "PAID" for invoice in invoices)
        resolved = [ticket for ticket in tickets if ticket["status"] == "RESOLVED"]
        funnel = {"clientes": state.get("customers", 0), "contratos": contracts.get("total", 0),
                  "contratosAtivos": contracts.get("active", 0), "faturas": len(invoices), "faturasPagas": paid,
                  "chamados": len(tickets), "chamadosResolvidos": len(resolved), "processos": state.get("processes", 0)}
        stuck = [stage for stage, before, after in (("ativação", funnel["contratos"], funnel["contratosAtivos"]),
                                                     ("pagamento", funnel["faturas"], funnel["faturasPagas"]),
                                                     ("resolução", funnel["chamados"], funnel["chamadosResolvidos"]))
                 if before and after / before < 0.5]
        self.add("Funil F1→F2→F3", "Em que etapa o fluxo integrado trava?", funnel,
                 f"Investigar a etapa de {', '.join(stuck)}: menos da metade avança." if stuck else "Nenhuma etapa com perda acima de 50%.",
                 "Três fluxos integrados; visão de negócio (retrabalho)")

        sla = {status: sum(ticket.get("slaStatus") == status for ticket in tickets)
               for status in ("MET", "BREACHED", "WITHIN", "PENDING", "NOT_APPLICABLE")}
        closed = sla["MET"] + sla["BREACHED"]
        breach_share = sla["BREACHED"] / closed if closed else 0.0
        self.add("Cumprimento de SLA", "O SLA herdado do contrato está sendo cumprido?",
                 {**sla, "violacaoEntreResolvidos": round(breach_share, 3)},
                 "Rever a premissa de prazo ou a priorização por categoria (premissas de 24 h e 72 h a validar)."
                 if breach_share > BREACH_ATTENTION_SHARE else "Violação dentro da margem; manter as premissas de SLA.",
                 "RNF-02 e RNF-06; F3")

        lag = insights.get("dispatchLag", [])
        slow = [row["consumer"] for row in lag if row["p95Seconds"] > LAG_ATTENTION_SECONDS]
        self.add("Atraso de despacho por consumidor", "O despacho explícito da outbox atrasa os efeitos?", lag,
                 f"Avaliar despacho automático (agendador) para {', '.join(slow)}: p95 acima de {LAG_ATTENTION_SECONDS:.0f} s."
                 if slow else "Despacho explícito suficiente no volume observado.",
                 "Escalabilidade e evolução (item 9)")

        events = insights.get("events", [])
        failing = [row["eventType"] for row in events if row["failed"]]
        retried = [row["eventType"] for row in events if row["retried"]]
        self.add("Retentativas e falhas por evento", "Qual consumidor endurecer primeiro?",
                 {"porEvento": events, "pendentes": outbox.get("pending", 0), "falhas": outbox.get("failed", 0)},
                 f"Corrigir a causa e reprocessar: {', '.join(failing)}." if failing
                 else (f"Sem falha permanente; observar retentativas em {', '.join(retried)}." if retried else "Sem falhas nem retentativas."),
                 "Confiabilidade e tolerância a falhas")

        replays = {labels["operation"]: int(value) for name, labels, value in samples if name == "archcorp_idempotency_replays_total"}
        self.add("Duplicidades evitadas", "A idempotência está evitando efeitos repetidos?",
                 {"repeticoesRecuperadas": replays, "chavesRegistradas": insights.get("idempotencyKeys", [])},
                 "Repetições foram absorvidas sem duplicar efeitos; manter Idempotency-Key nos comandos."
                 if replays else "Nenhuma repetição observada desde o último reinício.",
                 "Interoperabilidade; redução de duplicidade (visão de negócio)")

        latency = latency_by_operation(samples)
        over = [row["operation"] for row in latency if row["p95UpperBoundSeconds"] > P95_TARGET_SECONDS]
        problems = [{"status": int(labels["status"]), "code": labels["code"], "count": int(value)}
                    for name, labels, value in samples if name == "archcorp_problems_total"]
        self.add("Latência p95 por operação e erros por código", "Há gargalo ou erro recorrente de uso?",
                 {"latencia": latency[:10], "erros": sorted(problems, key=lambda row: -row["count"])},
                 f"Otimizar {', '.join(over)}: p95 acima de 500 ms (RNF-07)." if over
                 else "Todas as operações dentro da meta de 500 ms (RNF-07).",
                 "RNF-07 e observabilidade")

        usage: dict[str, int] = {}
        for row in insights.get("audit", []):
            usage[row["module"]] = usage.get(row["module"], 0) + row["count"]
        self.add("Uso por módulo (auditoria)", "Quais contextos concentram as operações?",
                 dict(sorted(usage.items(), key=lambda item: -item[1])),
                 f"Priorizar evolução e testes em {max(usage, key=usage.get)}, o contexto mais usado." if usage else "Sem operações auditadas.",
                 "Evolução e manutenção (item 9)")
        return {"geradoEm": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "baseUrl": str(self.client.base_url), "avisos": self.warnings, "indicadores": self.indicators}


def to_markdown(report: dict) -> str:
    lines = ["# Relatório operacional do ArchCorp", "",
             f"Gerado em {report['geradoEm']} a partir de {report['baseUrl']}. Dados sintéticos.",
             "As métricas em memória refletem o processo da API desde o último reinício.", ""]
    if report["avisos"]:
        lines += ["## Avisos", "", *[f"- {warning}" for warning in report["avisos"]], ""]
    lines += ["## Resumo", "", "| Indicador | Decisão sugerida | Evidência para |", "|---|---|---|"]
    lines += [f"| {item['indicador']} | {item['decisaoSugerida']} | {item['evidenciaGuia']} |" for item in report["indicadores"]]
    for item in report["indicadores"]:
        lines += ["", f"## {item['indicador']}", "", f"**Pergunta:** {item['pergunta']}", "",
                  "```json", json.dumps(item["valor"], ensure_ascii=False, indent=2), "```", "",
                  f"**Decisão sugerida:** {item['decisaoSugerida']}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=os.environ.get("ARCHCORP_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.environ.get("ARCHCORP_TOKEN", "demo-admin"))
    parser.add_argument("--saida", default="output/insights")
    args = parser.parse_args()
    # O console do Windows (cp1252) não representa todos os caracteres do relatório.
    sys.stdout.reconfigure(errors="replace")
    try:
        with httpx.Client(base_url=args.base_url, headers={"Authorization": f"Bearer {args.token}"}, timeout=10) as client:
            client.get("/health/ready").raise_for_status()
            report = Report(client).build()
    except httpx.HTTPError as exc:
        print(f"API inacessível em {args.base_url}: {type(exc).__name__}", file=sys.stderr)
        return 2
    folder = Path(args.saida)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "relatorio_operacional.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "relatorio_operacional.md").write_text(to_markdown(report), encoding="utf-8")
    print(f"Relatório gravado em {folder / 'relatorio_operacional.md'}")
    for item in report["indicadores"]:
        print(f"- {item['indicador']}: {item['decisaoSugerida']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
