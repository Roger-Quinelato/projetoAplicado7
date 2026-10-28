"""F-CFG, item 12 e S-01: governança de refs (somente leitura).

Uso (de qualquer diretório):
    python refs_governanca.py <WT> <gh_pr_list.json> > ../logs/refs_governanca.txt

Para cada PR mesclado, verifica se o commit de merge é ancestral de origin/main.
Para cada branch remota, conta commits fora da main (rev-list), commits sem patch
equivalente na main (git cherry) e arquivos alterados pela branch cujo conteúdo
difere da main (indício de trabalho que não chegou à main).
Não altera o repositório: só git rev-parse/merge-base/rev-list/cherry/diff/log/worktree.
"""
import json
import subprocess
import sys


def git(wt: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=check)


def is_ancestor(wt: str, commit: str, ref: str = "origin/main") -> bool:
    return git(wt, "merge-base", "--is-ancestor", commit, ref, check=False).returncode == 0


def main() -> None:
    wt, pr_json = sys.argv[1], sys.argv[2]
    main_sha = git(wt, "rev-parse", "origin/main").stdout.strip()
    print(f"origin/main = {main_sha}")
    print()
    print("## PRs mesclados: o commit de merge é ancestral de origin/main?")
    print("PR | base | head | merge | mergedAt | ancestral_da_main")
    prs = json.load(open(pr_json, encoding="utf-8"))
    for pr in sorted(prs, key=lambda p: p["number"]):
        if pr["state"] != "MERGED":
            print(f"#{pr['number']} | {pr['baseRefName']} | {pr['headRefName']} | - | - | {pr['state']} (draft={pr['isDraft']})")
            continue
        sha = (pr.get("mergeCommit") or {}).get("oid", "")
        exists = git(wt, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0
        verdict = ("sim" if is_ancestor(wt, sha) else "NAO") if exists else "commit ausente no clone"
        print(f"#{pr['number']} | {pr['baseRefName']} | {pr['headRefName']} | {sha[:7]} | {pr['mergedAt']} | {verdict}")
    print()
    print("## Branches remotas x origin/main")
    print("ref | sha | data_commit | a_frente | atras | ancestral | cherry_sem_equivalente | arquivos_alterados | arquivos_que_diferem_da_main")
    refs = git(wt, "for-each-ref", "--format=%(refname:short) %(objectname:short) %(committerdate:short)",
               "refs/remotes/origin").stdout.split("\n")
    for line in filter(None, refs):
        ref, sha, date = line.split()
        if ref in ("origin/HEAD", "origin/main", "origin"):
            continue
        ahead = git(wt, "rev-list", "--count", f"origin/main..{ref}").stdout.strip()
        behind = git(wt, "rev-list", "--count", f"{ref}..origin/main").stdout.strip()
        anc = "sim" if is_ancestor(wt, ref) else "nao"
        cherry = git(wt, "cherry", "origin/main", ref).stdout.split("\n")
        plus = sum(1 for c in cherry if c.startswith("+"))
        base = git(wt, "merge-base", "origin/main", ref).stdout.strip()
        changed = [f for f in git(wt, "diff", "--name-only", base, ref).stdout.split("\n") if f]
        differ = []
        for f in changed:
            if git(wt, "diff", "--quiet", ref, "origin/main", "--", f, check=False).returncode != 0:
                differ.append(f)
        print(f"{ref} | {sha} | {date} | {ahead} | {behind} | {anc} | {plus} | {len(changed)} | {len(differ)}")
        if differ and anc == "nao":
            sample = ", ".join(differ[:12]) + (" ..." if len(differ) > 12 else "")
            print(f"    difere: {sample}")
    print()
    print("## Branches locais x origin/main (mesmas métricas)")
    locs = git(wt, "for-each-ref", "--format=%(refname:short) %(objectname:short) %(committerdate:short) %(upstream:short)",
               "refs/heads").stdout.split("\n")
    for line in filter(None, locs):
        parts = line.split()
        ref, sha, date = parts[0], parts[1], parts[2]
        upstream = parts[3] if len(parts) > 3 else "-"
        ahead = git(wt, "rev-list", "--count", f"origin/main..{ref}").stdout.strip()
        anc = "sim" if is_ancestor(wt, ref) else "nao"
        cherry = git(wt, "cherry", "origin/main", ref).stdout.split("\n")
        plus = sum(1 for c in cherry if c.startswith("+"))
        on_remote = git(wt, "branch", "-r", "--contains", sha).stdout.strip().replace("\n", ",").replace(" ", "")
        print(f"{ref} | {sha} | {date} | upstream={upstream} | a_frente={ahead} | ancestral={anc} | cherry+={plus} | contido_em_remotas={on_remote or 'NENHUMA'}")
    print()
    print("## git worktree list --porcelain")
    print(git(wt, "worktree", "list", "--porcelain").stdout)


if __name__ == "__main__":
    main()
