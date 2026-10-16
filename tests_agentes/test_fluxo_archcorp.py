"""Ciclo coordenado com agentes falsos: aprovação, correção, limites, falhas de ambiente e retomada."""
import json
import os
import subprocess
import sys
import time

import pytest

from conftest import fluxo, git

ID = "e1"


def tarefa(**campos) -> dict:
    dados = {"versao": 1, "resultado": "tarefa", "perguntas": [], "tipo": "correcao", "modo": "padrao",
             "titulo": "Corrige soma", "objetivo": "soma(a, b) devolve a + b",
             "problema_e_reproducao": "soma(2, 2) devolve 0 na base", "escopo_permitido": ["src/", "tests/"],
             "exclusoes": [], "criterios_aceite": [{"id": "C1", "texto": "soma(2, 2) == 4"}],
             "verificacoes_exigidas": [{"comando": "python -m pytest", "proposito": "regressão", "ambiente": "local"}],
             "skills_compartilhadas": [], "adr_necessaria": None, "riscos": [], "fases": []}
    dados.update(campos)
    return {"json": dados}


def entrega(arquivos=None, **campos) -> dict:
    dados = {"versao": 1, "estado": "concluida", "resumo": "Corrigida a soma.",
             "arquivos_alterados": [{"caminho": c, "motivo": "correção"} for c in (arquivos or {})],
             "criterios": [{"id": "C1", "evidencia": "teste", "resultado": "passou"}],
             "comandos": [{"comando": "python -m pytest", "ambiente": "local", "resultado": "1 passed"}],
             "resposta_achados": [], "limitacoes": [], "perguntas": []}
    dados.update(campos)
    return {"json": dados, "arquivos": arquivos or {}}


def parecer(veredito="aprovado", achados=(), **extra) -> dict:
    dados = {"versao": 1, "head_revisado": "$HEAD", "veredito": veredito,
             "motivo_bloqueio": "bloqueio de teste" if veredito == "bloqueado" else None,
             "verificacoes": [{"comando": "python -m pytest", "resultado": "passou", "observacao": ""}],
             "achados": [{"numero": i, "severidade": sev, "caminho": "src/app.py", "linha": 2, "problema": prob,
                          "correcao_exigida": "corrigir", "evidencia": "leitura"}
                         for i, (sev, prob) in enumerate(achados, 1)],
             "alegacoes": [], "padroes": "ok", "especificacao": "ok"}
    return dict({"json": dados}, **extra)


CORRIGIDO = {"src/app.py": "def soma(a, b):\n    return a + b\n"}


def commits_do_ramo(amb) -> list[str]:
    return git(amb.repo, "log", "--format=%H", f"main..archcorp/{ID}").split()


def test_aprovacao_na_primeira_revisao(amb):
    amb.cenario(codex=[tarefa(), parecer()], claude=[entrega(CORRIGIDO)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    estado = amb.execucao(ID)
    assert estado["estado"] == "aprovada"
    commits = commits_do_ramo(amb)
    assert len(commits) == 1
    assert estado["aprovacao"]["sha"] == commits[0] == git(amb.repo, "rev-parse", f"archcorp/{ID}")
    assert f"Archcorp-Tentativa: {ID}/f1/r1" in git(amb.repo, "log", "-1", "--format=%B", commits[0])
    preparacao, revisao = amb.chamadas("codex")
    assert "read-only" in preparacao["args"] and "PREPARAÇÃO" in preparacao["prompt"]
    assert revisao["cwd"].endswith(os.path.join(ID, "base"))  # instruções fixadas na base
    assert "--add-dir" in revisao["args"] and "REVISÃO" in revisao["prompt"]
    implementador = amb.chamadas("claude")[0]
    assert "acceptEdits" in implementador["args"]
    assert not any("bypass" in a.lower() or "dangerously" in a.lower() for a in implementador["args"])
    pasta = amb.repo / ".agentes/execucoes" / ID
    for nome in ("pr.md", "resumo.md", "tarefa-v1.md", "entrega-f1-r1.md", "parecer-f1-t1.md", "instrucoes/AGENTS.md"):
        assert (pasta / nome).is_file(), nome
    assert commits[0] in (pasta / "pr.md").read_text(encoding="utf-8")
    assert " " in str(amb.repo)  # caminho Windows com espaço


def test_correcao_seguida_de_aprovacao(amb):
    amb.cenario(codex=[tarefa(), parecer("correcao_necessaria", [("DEVE_CORRIGIR", "falta teste de regressão")]),
                       parecer()],
                claude=[entrega(CORRIGIDO),
                        entrega({"tests/test_app.py": "def test_soma():\n    pass\n"},
                                resposta_achados=[{"numero": 1, "acao": "corrigido", "prova_ou_motivo": "teste"}])])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    assert len(commits_do_ramo(amb)) == 2
    correcao = amb.chamadas("claude")[1]
    assert "falta teste de regressão" in correcao["prompt"] and "rodada 2 de 3 (correcao)" in correcao["prompt"]
    segunda = amb.chamadas("codex")[2]
    assert "tentativa 2 de 3" in segunda["prompt"] and "Parecer anterior" in segunda["prompt"]


def test_esgota_tentativas_e_bloqueia(amb):
    reprova = parecer("correcao_necessaria", [("BLOQUEANTE", "ainda errado")])
    amb.cenario(codex=[tarefa(), reprova, reprova, reprova],
                claude=[entrega({"src/app.py": f"# v{i}\n"}) for i in range(3)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 2

    estado = amb.execucao(ID)
    assert estado["estado"] == "bloqueada" and "3 pareceres" in estado["motivo"]
    assert len(amb.chamadas("claude")) == 3 and len(amb.chamadas("codex")) == 4
    with pytest.raises(SystemExit, match="decisão humana"):
        amb.rodar("resume", "--execucao", ID)


def test_rodada_extra_autorizada_depois_do_bloqueio(amb):
    reprova = parecer("correcao_necessaria", [("BLOQUEANTE", "ainda errado")])
    amb.cenario(codex=[tarefa(), reprova, reprova, reprova, parecer()],
                claude=[entrega({"src/app.py": f"# v{i}\n"}) for i in range(4)])
    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)

    assert amb.rodar("resume", "--execucao", ID, "--rodada-extra") == 0

    estado = amb.execucao(ID)
    assert estado["estado"] == "aprovada" and estado["decisoes"][0]["decisao"] == "rodada extra autorizada"


def test_revisar_novamente_apos_bloqueio_de_ambiente_nao_chama_o_implementador(amb):
    amb.cenario(codex=[tarefa(), parecer("bloqueado"), parecer()], claude=[entrega(CORRIGIDO)])
    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 2

    assert amb.rodar("resume", "--execucao", ID, "--revisar-novamente") == 0

    estado = amb.execucao(ID)
    assert len(amb.chamadas("claude")) == 1 and len(commits_do_ramo(amb)) == 1
    assert [p["valido"] for p in estado["fases"][0]["pareceres"]] == [False, True]
    assert estado["decisoes"][0]["decisao"] == "revisar novamente o mesmo SHA"


def test_timeout_interrompe_sem_contar_como_reprovacao(amb, monkeypatch):
    monkeypatch.setenv("ARCHCORP_FLUXO_TIMEOUT", "2")
    amb.cenario(codex=[tarefa()], claude=[dict(entrega(CORRIGIDO), dormir=30)])
    inicio = time.monotonic()

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 1

    assert time.monotonic() - inicio < 25
    estado = amb.execucao(ID)
    assert estado["estado"] == "interrompida" and "timeout" in estado["motivo"]
    assert estado["fases"][0]["pareceres"] == []


@pytest.mark.parametrize("papel,resposta,trecho", [
    ("claude", {"texto": "não sou JSON"}, "saída inválida"),
    ("claude", {"json": {"versao": 1, "estado": "talvez"}}, "viola entrega.schema.json"),
    ("claude", dict(entrega(CORRIGIDO), subtype="error_max_turns"), "limite de turnos"),
    ("codex", {"codigo": 3, "stderr": "401 Unauthorized"}, "autenticação"),
])
def test_saida_invalida_ou_erro_de_ambiente_interrompe(amb, papel, resposta, trecho):
    if papel == "claude":
        amb.cenario(codex=[tarefa()], claude=[resposta])
    else:
        amb.cenario(codex=[resposta])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 1

    estado = amb.execucao(ID)
    assert estado["estado"] == "interrompida" and trecho in estado["motivo"]


def test_entrega_sem_listas_vazias_e_completada_mas_sem_conteudo_e_recusada(amb):
    sem_listas = entrega(CORRIGIDO)
    for campo in ("resposta_achados", "limitacoes", "perguntas"):
        del sem_listas["json"][campo]
    amb.cenario(codex=[tarefa(), parecer()], claude=[sem_listas])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    sessao = next(s for s in amb.execucao(ID)["sessoes"] if s["ferramenta"] == "claude")
    assert sessao["campos_completados"] == ["resposta_achados", "limitacoes", "perguntas"]


def test_utilitario_executa_verificacoes_e_prova_vermelho_na_base(amb):
    marcador = amb.estado / "nao-devia-existir.txt"
    verificacoes = [{"comando": '$env:PYTHONPATH="src"; python -m pytest tests/test_app.py -q -p no:cacheprovider',
                     "proposito": "regressão", "ambiente": "local"},
                    {"comando": f"python -c \"open(r'{marcador}', 'w')\"", "proposito": "fora da lista", "ambiente": "local"}]
    teste = {"tests/test_app.py": "from app import soma\n\n\ndef test_soma():\n    assert soma(2, 2) == 4\n"}
    amb.cenario(codex=[tarefa(verificacoes_exigidas=verificacoes), parecer()], claude=[entrega({**CORRIGIDO, **teste})])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    pasta = amb.repo / ".agentes/execucoes" / ID
    resultado = json.loads(next(pasta.glob("revisao-*.verificacoes.json")).read_text(encoding="utf-8"))
    assert [v["resultado"] for v in resultado["head"]] == ["passou", "nao_executado"]
    assert [v["resultado"] for v in resultado["base"]] == ["falhou"]  # teste do head contra o código da base
    assert not marcador.exists()
    assert "executadas pelo utilitário" in amb.chamadas("codex")[1]["prompt"]
    assert "utilitário, código da base" in (pasta / "pr.md").read_text(encoding="utf-8")


def test_parecer_que_aprova_com_achado_aberto_e_invalido(amb):
    amb.cenario(codex=[tarefa(), parecer("aprovado", [("BLOQUEANTE", "x")])], claude=[entrega(CORRIGIDO)])

    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)

    assert "aprovado com achados abertos" in amb.execucao(ID)["motivo"]


def test_dependencia_ausente_interrompe_antes_de_chamar_modelos(amb, monkeypatch, tmp_path):
    monkeypatch.setenv("ARCHCORP_FLUXO_CLAUDE", json.dumps([str(tmp_path / "nao existe" / "claude.exe")]))
    amb.cenario(codex=[tarefa()], claude=[entrega(CORRIGIDO)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 1

    estado = amb.execucao(ID)
    assert estado["estado"] == "interrompida" and "dependência ausente" in estado["motivo"]
    assert amb.chamadas() == []


def test_pedido_ambiguo_e_retomada_com_resposta(amb, tmp_path):
    esclarece = tarefa(resultado="esclarecimento", perguntas=["Qual módulo deve mudar?"])
    amb.cenario(codex=[esclarece, tarefa(), parecer()], claude=[entrega(CORRIGIDO)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 2
    assert amb.execucao(ID)["estado"] == "aguardando_esclarecimento"
    with pytest.raises(SystemExit, match="--resposta"):
        amb.rodar("resume", "--execucao", ID)
    resposta = tmp_path / "resposta.md"
    resposta.write_text("Só src/app.py.", encoding="utf-8")

    assert amb.rodar("resume", "--execucao", ID, "--resposta", str(resposta)) == 0

    pasta = amb.repo / ".agentes/execucoes" / ID
    assert "Qual módulo" in (pasta / "esclarecimento-1.md").read_text(encoding="utf-8")
    assert (pasta / "resposta-1.md").read_text(encoding="utf-8") == "Só src/app.py."
    assert "Só src/app.py." in amb.chamadas("codex")[1]["prompt"]


def test_implementador_pergunta_e_retoma(amb, tmp_path):
    duvida = entrega(estado="bloqueada", perguntas=["Pode mudar a assinatura?"])
    amb.cenario(codex=[tarefa(), parecer()], claude=[duvida, entrega(CORRIGIDO)])
    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)
    assert amb.execucao(ID)["estado"] == "aguardando_esclarecimento"
    resposta = tmp_path / "r.md"
    resposta.write_text("Não.", encoding="utf-8")

    assert amb.rodar("resume", "--execucao", ID, "--resposta", str(resposta)) == 0

    assert "Não." in amb.chamadas("claude")[1]["prompt"]
    assert len(commits_do_ramo(amb)) == 1


def test_entrega_sem_mudancas_bloqueia_tarefa_que_exige_alteracao(amb):
    amb.cenario(codex=[tarefa()], claude=[entrega()])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 2

    assert "sem mudanças" in amb.execucao(ID)["motivo"]
    assert len(amb.chamadas("codex")) == 1


def test_tarefa_so_de_verificacao_revisa_a_base_sem_commit(amb):
    amb.cenario(codex=[tarefa(tipo="verificacao"), parecer()], claude=[entrega()])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    estado = amb.execucao(ID)
    assert commits_do_ramo(amb) == []
    assert estado["aprovacao"]["sha"] == git(amb.repo, "rev-parse", "main")


def test_commit_alterado_durante_a_revisao_rejeita_o_parecer(amb):
    amb.cenario(codex=[tarefa(), parecer(commit_no_impl=True)], claude=[entrega(CORRIGIDO)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 1

    estado = amb.execucao(ID)
    assert estado["estado"] == "interrompida" and "parecer rejeitado" in estado["motivo"]
    assert estado["fases"][0]["pareceres"] == []


def test_commit_alterado_depois_da_aprovacao_invalida_o_status(amb, capsys):
    amb.cenario(codex=[tarefa(), parecer()], claude=[entrega(CORRIGIDO)])
    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)
    impl = amb.repo / ".agentes/worktrees" / ID / "impl"
    (impl / "depois.txt").write_text("x", encoding="utf-8")
    git(impl, "add", "-A")
    git(impl, "commit", "-q", "-m", "depois")
    capsys.readouterr()

    assert amb.rodar("status", "--execucao", ID) == 3

    assert "INVÁLIDA" in capsys.readouterr().out


def test_revisor_que_altera_arquivo_tem_parecer_rejeitado_e_retomada_revisa_de_novo(amb):
    amb.cenario(codex=[tarefa(), parecer(alterar_revisado={"src/app.py": "sabotado\n"}), parecer()],
                claude=[entrega(CORRIGIDO)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 1
    assert "o revisor alterou arquivos" in amb.execucao(ID)["motivo"]

    assert amb.rodar("resume", "--execucao", ID) == 0

    worktrees = amb.repo / ".agentes/worktrees" / ID
    assert (worktrees / "revisao-f1-t1-c1/src/app.py").read_text(encoding="utf-8") == "sabotado\n"  # preservado
    assert (worktrees / "revisao-f1-t1-c2").is_dir()
    assert len(amb.chamadas("claude")) == 1


def test_queda_entre_commit_e_persistencia_retoma_sem_repetir(amb, monkeypatch):
    amb.cenario(codex=[tarefa(), parecer()], claude=[entrega(CORRIGIDO)])
    monkeypatch.setenv("ARCHCORP_FLUXO_FALHA_APOS", "commit")
    with pytest.raises(fluxo._FalhaSimulada):
        amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)
    assert amb.execucao(ID)["fases"][0]["rodadas"][0]["situacao"] == "commit_pendente"
    monkeypatch.delenv("ARCHCORP_FLUXO_FALHA_APOS")

    assert amb.rodar("resume", "--execucao", ID) == 0

    assert len(amb.chamadas("claude")) == 1
    assert len(commits_do_ramo(amb)) == 1


def test_queda_durante_implementacao_com_alteracoes_nao_repete_automaticamente(amb, monkeypatch):
    monkeypatch.setenv("ARCHCORP_FLUXO_TIMEOUT", "2")
    amb.cenario(codex=[tarefa(), parecer()], claude=[dict(entrega(CORRIGIDO), dormir=30), entrega(CORRIGIDO)])
    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)
    impl = amb.repo / ".agentes/worktrees" / ID / "impl"
    (impl / "src/app.py").write_text("meio caminho\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="Resultado incerto"):
        amb.rodar("resume", "--execucao", ID)

    assert len(amb.chamadas("claude")) == 1


def test_retomada_concorrente_e_recusada(amb, monkeypatch):
    monkeypatch.setenv("ARCHCORP_FLUXO_TIMEOUT", "2")
    amb.cenario(codex=[tarefa()], claude=[dict(entrega(CORRIGIDO), dormir=30)])
    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)
    trava = amb.repo / ".agentes/execucoes" / ID / ".trava"
    vivo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        trava.write_text(str(vivo.pid))
        with pytest.raises(SystemExit, match="em uso"):
            amb.rodar("resume", "--execucao", ID)
    finally:
        vivo.kill()
        vivo.wait()
    morto = subprocess.Popen([sys.executable, "-c", "pass"])
    morto.wait()
    trava.write_text(str(morto.pid))
    amb.cenario(codex=[tarefa(), parecer()], claude=[dict(entrega(CORRIGIDO), dormir=30), entrega(CORRIGIDO)])
    monkeypatch.setenv("ARCHCORP_FLUXO_TIMEOUT", "60")

    assert amb.rodar("resume", "--execucao", ID) == 0  # trava de processo morto é retomada
    assert not trava.exists()


def test_deepwork_sequencial_com_revisao_integrada(amb):
    fase = lambda titulo, arquivo: {"titulo": titulo, "objetivo": titulo, "tipo": "funcionalidade",  # noqa: E731
                                    "escopo_permitido": [arquivo], "exclusoes": [],
                                    "criterios_aceite": [{"id": "C1", "texto": titulo}],
                                    "verificacoes_exigidas": [], "skills_compartilhadas": [], "riscos": []}
    plano = tarefa(modo="deepwork", tipo="funcionalidade", criterios_aceite=[], escopo_permitido=[],
                   fases=[fase("caracterizar", "src/a.py"), fase("corrigir", "src/b.py")])
    amb.cenario(codex=[plano, parecer(), parecer(), parecer()],
                claude=[entrega({"src/a.py": "a = 1\n"}), entrega({"src/b.py": "b = 2\n"})])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    estado = amb.execucao(ID)
    primeiro, segundo = reversed(commits_do_ramo(amb))
    assert [f["aprovado_sha"] for f in estado["fases"]] == [primeiro, segundo]
    assert amb.chamadas("claude")[1]["head"] == primeiro  # fase 2 parte do commit aprovado da fase 1
    integrada = amb.chamadas("codex")[3]
    assert "INTEGRADA" in integrada["prompt"] and "não é pós-merge" in integrada["prompt"]
    assert estado["revisao_final"]["veredito"] == "aprovado"


def test_implementador_nao_pode_commitar(amb):
    amb.cenario(codex=[tarefa()], claude=[dict(entrega(CORRIGIDO), commit_proprio=True)])

    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)

    assert "implementador criou commit" in amb.execucao(ID)["motivo"]


def test_caminho_proibido_nao_e_commitado(amb):
    amb.cenario(codex=[tarefa()], claude=[entrega({".claude/settings.local.json": "{}"})])

    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)

    assert "caminhos proibidos" in amb.execucao(ID)["motivo"]
    assert commits_do_ramo(amb) == []


def test_ciclo_nao_publica_no_remoto(amb, tmp_path):
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remoto)], check=True)
    git(amb.repo, "remote", "add", "origin", str(remoto))
    amb.cenario(codex=[tarefa(), parecer()], claude=[dict(entrega(CORRIGIDO), tentar_push=True)])

    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID) == 0

    assert git(amb.repo, "ls-remote", str(remoto)) == ""
    assert (amb.estado / "push.txt").read_text(encoding="utf-8").split("\n")[0] != "0"
    assert '"push"' not in fluxo.FERRAMENTA.read_text(encoding="utf-8")  # o utilitário nunca chama git push


def test_credencial_na_entrega_e_sanitizada(amb):
    segredo = "sk-" + "a1b2c3d4" * 4
    amb.cenario(codex=[tarefa(), parecer()], claude=[entrega(CORRIGIDO, resumo=f"usei {segredo}")])

    amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID)

    pasta = amb.repo / ".agentes/execucoes" / ID
    for arquivo in pasta.rglob("*"):
        if arquivo.is_file() and "instrucoes" not in arquivo.parts:
            assert segredo not in arquivo.read_text(encoding="utf-8", errors="replace"), arquivo


def test_dry_run_nao_cria_nada_nem_chama_agentes(amb, capsys):
    assert amb.rodar("run", "--pedido", str(amb.pedido()), "--execucao", ID, "--dry-run") == 0

    assert not (amb.repo / ".agentes").exists()
    assert amb.chamadas() == []
    assert "[dry-run]" in capsys.readouterr().out


def test_preflight_sem_chamar_modelos(amb, capsys):
    assert amb.rodar("preflight") == 0

    saida = capsys.readouterr().out
    assert "sem chamar modelos" in saida and "FALHA" not in saida
    assert amb.chamadas() == []
