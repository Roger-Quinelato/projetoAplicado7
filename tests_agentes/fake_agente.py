"""Executável falso de Codex e Claude para os testes do fluxo (nenhuma chamada a modelo).

Uso: python fake_agente.py <codex|claude> [argumentos da CLI real]
FAKE_CENARIO aponta para {"codex": [respostas], "claude": [respostas]}, consumidas em ordem;
FAKE_ESTADO guarda contadores e o registro das chamadas (chamadas.jsonl).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

AJUDA = {
    "codex": "exec --sandbox --cd --json --output-schema --add-dir -o",
    "claude": "-p --output-format --agent --agents --json-schema --add-dir --permission-mode --allowedTools --settings",
}


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def main() -> int:
    papel, args = sys.argv[1], sys.argv[2:]
    if "--version" in args:
        print(f"fake-{papel} 0.0.1")
        return 0
    if "--help" in args:
        print(AJUDA[papel])
        return 0
    estado = Path(os.environ["FAKE_ESTADO"])
    cenario = json.loads(Path(os.environ["FAKE_CENARIO"]).read_text(encoding="utf-8"))
    contador = estado / f"{papel}.n"
    n = int(contador.read_text()) if contador.exists() else 0
    contador.write_text(str(n + 1))
    prompt = sys.stdin.read()
    cwd = Path.cwd()
    revisado = Path(args[args.index("--add-dir") + 1]) if papel == "codex" and "--add-dir" in args else None
    with (estado / "chamadas.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"papel": papel, "n": n, "args": args, "cwd": str(cwd), "prompt": prompt,
                              "head": git(cwd, "rev-parse", "HEAD").stdout.strip()}, ensure_ascii=False) + "\n")
    respostas = cenario[papel]
    if n >= len(respostas):
        print(f"cenário esgotado para {papel}", file=sys.stderr)
        return 99
    resposta = respostas[n]
    time.sleep(resposta.get("dormir", 0))
    for rel, conteudo in resposta.get("arquivos", {}).items():
        alvo = cwd / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")
    for rel, conteudo in resposta.get("alterar_revisado", {}).items():
        (revisado / rel).write_text(conteudo, encoding="utf-8")
    if resposta.get("commit_proprio"):
        git(cwd, "add", "-A")
        git(cwd, "commit", "-q", "-m", "commit do implementador")
    if resposta.get("commit_no_impl"):
        impl = revisado.parent / "impl"
        (impl / "intruso.txt").write_text("x", encoding="utf-8")
        git(impl, "add", "-A")
        git(impl, "commit", "-q", "-m", "commit depois da revisão")
    if resposta.get("tentar_push"):
        resultado = git(cwd, "push", "origin", "HEAD:refs/heads/vazou")
        (estado / "push.txt").write_text(f"{resultado.returncode}\n{resultado.stderr}", encoding="utf-8")
    if resposta.get("codigo"):
        print(resposta.get("stderr", "falha simulada"), file=sys.stderr)
        return resposta["codigo"]
    saida = resposta.get("json")
    if papel == "codex":
        if isinstance(saida, dict) and saida.get("head_revisado") == "$HEAD":
            saida["head_revisado"] = git(revisado, "rev-parse", "HEAD").stdout.strip()
        print(json.dumps({"type": "thread.started", "thread_id": f"fake-thread-{n}"}))
        destino = Path(args[args.index("-o") + 1])
        destino.write_text(resposta["texto"] if "texto" in resposta else json.dumps(saida), encoding="utf-8")
        return 0
    if "texto" in resposta:
        print(resposta["texto"])
        return 0
    print(json.dumps({"type": "result", "subtype": resposta.get("subtype", "success"), "is_error": False,
                      "session_id": f"fake-sessao-{n}", "num_turns": 3, "result": "ok",
                      "structured_output": saida, "permission_denials": resposta.get("negadas", [])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
