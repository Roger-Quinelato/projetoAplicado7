"""Consolida as evidências de verificação num único arquivo, gerado a partir das execuções.

Evita números copiados à mão: roda as verificações locais, lê os resultados das próprias
ferramentas (JUnit XML do pytest, JSON do performance_smoke) e, se o `gh` estiver disponível,
consulta a CI do commit. Grava `output/evidencias/evidencias.json`, que é a fonte usada por
`docs/EVIDENCIAS_VALIDACAO.md` e por `tools/build_report.py`.

Uso, na raiz do repositório (Windows PowerShell ou bash):
    python tools/consolidar_evidencias.py            # pytest, OpenAPI, desempenho e CI
    python tools/consolidar_evidencias.py --com-web  # inclui npm test em web/
    python tools/consolidar_evidencias.py --sem-pytest --sem-desempenho  # só OpenAPI e CI

Docker e PostgreSQL ficam com a CI. Saída 0 quando todas as verificações executadas passam.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "output" / "evidencias"
PYTHON = next((str(path) for path in (RAIZ / ".venv" / "Scripts" / "python.exe", RAIZ / ".venv" / "bin" / "python") if path.exists()), sys.executable)


def run(command: list[str], *, cwd: Path = RAIZ, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, env={**os.environ, "PYTHONPATH": str(RAIZ / "src"), **(env or {})},
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def git(*args: str) -> str:
    return run(["git", *args]).stdout.strip()


def pytest_evidence() -> dict:
    junit = SAIDA / "pytest.xml"
    started = datetime.now(timezone.utc)
    result = run([PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"],
                 env={"DATABASE_URL": "sqlite:///./tmp/evidencias-pytest.db", "TEST_DATABASE_URL": "sqlite:///./tmp/evidencias-pytest.db"})
    suite = ET.parse(junit).getroot()
    suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
    total, failures, errors, skipped = (int(suite.get(name, 0)) for name in ("tests", "failures", "errors", "skipped"))
    return {"comando": "pytest -q", "banco": "SQLite", "aprovados": total - failures - errors - skipped, "ignorados": skipped,
            "falhas": failures + errors, "segundos": round(float(suite.get("time", 0)), 1),
            "inicio": started.isoformat().replace("+00:00", "Z"), "ok": result.returncode == 0}


def openapi_evidence() -> dict:
    result = run([PYTHON, "tools/export_openapi.py", "--check"])
    return {"comando": "tools/export_openapi.py --check", "ok": result.returncode == 0}


def performance_evidence() -> dict:
    destino = SAIDA / "desempenho.json"
    result = run([PYTHON, "scripts/performance_smoke.py", "--json", str(destino)],
                 env={"DATABASE_URL": "sqlite:///./tmp/evidencias-desempenho.db"})
    if not destino.exists():
        return {"comando": "scripts/performance_smoke.py", "ok": False}
    data = json.loads(destino.read_text(encoding="utf-8"))
    return {"comando": "scripts/performance_smoke.py", "banco": data["banco"], "metaP95Ms": data["metaP95Ms"],
            "maiorP95Ms": data["maiorP95Ms"], "consultas": len(data["consultas"]), "ok": result.returncode == 0}


def web_evidence() -> dict:
    npm = shutil.which("npm")
    if not npm:
        return {"comando": "npm test", "ok": False, "observacao": "npm não encontrado"}
    result = run([npm, "test"], cwd=RAIZ / "web")
    summary = [line.strip("ℹ ").strip() for line in result.stdout.splitlines() if line.lstrip("ℹ ").startswith(("pass ", "fail "))]
    return {"comando": "npm test (web)", "resumo": summary, "ok": result.returncode == 0}


def ci_evidence(commit: str) -> dict:
    gh = shutil.which("gh")
    if not gh:
        return {"disponivel": False, "observacao": "gh não encontrado"}
    result = run([gh, "run", "list", "--commit", commit, "--json", "databaseId,status,conclusion,workflowName,url", "--limit", "5"])
    runs = json.loads(result.stdout or "[]") if result.returncode == 0 else []
    if not runs:
        return {"disponivel": False, "observacao": "nenhuma execução de CI para este commit (faça push e aguarde)"}
    latest = runs[0]
    return {"disponivel": True, "execucao": latest["databaseId"], "workflow": latest["workflowName"],
            "status": latest["status"], "conclusao": latest["conclusion"], "url": latest["url"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sem-pytest", action="store_true")
    parser.add_argument("--sem-desempenho", action="store_true")
    parser.add_argument("--com-web", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")
    SAIDA.mkdir(parents=True, exist_ok=True)
    (RAIZ / "tmp").mkdir(exist_ok=True)

    commit = git("rev-parse", "HEAD")
    evidence = {
        "geradoEm": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "commit": commit, "commitCurto": commit[:7], "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "arvoreLimpa": not git("status", "--porcelain", "--untracked-files=no"),
        "ambiente": {"sistema": platform.platform(), "python": platform.python_version()},
        "verificacoes": {"openapi": openapi_evidence()},
    }
    if not args.sem_pytest:
        evidence["verificacoes"]["pytest"] = pytest_evidence()
    if not args.sem_desempenho:
        evidence["verificacoes"]["desempenho"] = performance_evidence()
    if args.com_web:
        evidence["verificacoes"]["web"] = web_evidence()
    evidence["ci"] = ci_evidence(commit)
    evidence["ok"] = all(item.get("ok", False) for item in evidence["verificacoes"].values())

    (SAIDA / "evidencias.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"commit={evidence['commitCurto']} arvore_limpa={evidence['arvoreLimpa']} ok={evidence['ok']}")
    for name, item in evidence["verificacoes"].items():
        print(f"- {name}: {'OK' if item.get('ok') else 'FALHA'} {json.dumps({k: v for k, v in item.items() if k not in ('ok', 'comando')}, ensure_ascii=False)}")
    print(f"- ci: {json.dumps(evidence['ci'], ensure_ascii=False)}")
    if not evidence["arvoreLimpa"]:
        print("Aviso: há alterações não commitadas; a evidência não corresponde exatamente ao commit.")
    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
