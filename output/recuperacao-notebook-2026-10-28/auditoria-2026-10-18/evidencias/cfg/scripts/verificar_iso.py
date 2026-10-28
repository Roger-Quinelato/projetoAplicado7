"""F-CFG (pré-requisito): confere a cópia isolada contra o manifesto do SHA congelado.

Uso:
    PY -I verificar_iso.py <ISO> <manifest_44b8325.sha256>

Somente leitura: calcula SHA-256 dos arquivos listados no manifesto e reporta divergências,
ausências e arquivos extras na cópia (fora de .git, que não existe na cópia).
"""
import hashlib
import os
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    iso = Path(sys.argv[1])
    manifest = Path(sys.argv[2])
    expected = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, rel = line.split(None, 1)
        rel = rel.strip().lstrip("*")
        expected[rel] = digest.lower()
    missing, changed = [], []
    for rel, digest in sorted(expected.items()):
        target = iso / rel
        if not target.is_file():
            missing.append(rel)
            continue
        if sha256(target) != digest:
            changed.append(rel)
    present = set()
    for root, dirs, files in os.walk(iso):
        dirs[:] = [d for d in dirs if d not in ("tmp", "node_modules", ".git")]
        for name in files:
            present.add((Path(root) / name).relative_to(iso).as_posix())
    extra = sorted(p for p in present if p not in expected and not p.startswith("tmp/"))
    print(f"manifesto: {len(expected)} arquivos")
    print(f"ausentes: {len(missing)}")
    for rel in missing:
        print(f"  AUSENTE {rel}")
    print(f"divergentes: {len(changed)}")
    for rel in changed:
        print(f"  DIVERGENTE {rel}")
    print(f"extras (fora do manifesto, excluindo tmp/node_modules): {len(extra)}")
    for rel in extra[:50]:
        print(f"  EXTRA {rel}")
    print("RESULTADO:", "OK" if not missing and not changed else "DIVERGENCIA")


if __name__ == "__main__":
    main()
