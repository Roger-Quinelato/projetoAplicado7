"""F-QUA - contraste WCAG 2.1 calculado a partir das cores de web/src/style.css (SHA 44b8325).

Sem navegador: os pares (primeiro plano, fundo) foram levantados por inspecao do CSS e do TSX.
Formula: WCAG 2.1, luminancia relativa (sRGB) e razao (L1 + 0.05) / (L2 + 0.05).
Uso: python -I contraste_wcag.py
"""

def channel(c: float) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def blend(fg: str, bg: str, alpha: float) -> str:
    f, b = hex_rgb(fg), hex_rgb(bg)
    return "#" + "".join(f"{round(alpha * x + (1 - alpha) * y):02x}" for x, y in zip(f, b))


def luminance(value: str) -> float:
    r, g, b = (channel(c) for c in hex_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# (elemento, local, primeiro plano, fundo, tamanho/peso, minimo exigido)
# Texto normal: 4.5:1. Texto grande (>= 24px, ou >= 18.66px em negrito): 3:1. Componente de interface (1.4.11): 3:1.
PAIRS = [
    ("Texto principal (--ink) na pagina", "style.css:4,20-21", "#182943", "#f4f7fb", "14px", 4.5),
    ("Paragrafo de cartao (--text) no cartao", "style.css:6,75", "#41566e", "#ffffff", "14px", 4.5),
    ("Introducao (--text) na pagina", "style.css:64", "#41566e", "#f4f7fb", "14px", 4.5),
    ("Rotulo de campo (--muted) no cartao", "style.css:86", "#5a6b80", "#ffffff", "12px 700", 4.5),
    ("Dica de campo / .roles (--muted) no cartao", "style.css:76,87", "#5a6b80", "#ffffff", "11px", 4.5),
    ("Cabecalho de tabela th (--muted)", "style.css:120", "#5a6b80", "#ffffff", "10px caixa alta", 4.5),
    ("Rotulo de estatistica .stat span (--muted)", "style.css:79-80", "#5a6b80", "#f7f9fc", "12px 700", 4.5),
    ("Estado vazio .empty (--muted)", "style.css:132", "#5a6b80", "#f7f9fb", "14px", 4.5),
    ("Eyebrow da barra superior na pagina", "style.css:47; App.tsx:112", "#5f7290", "#f4f7fb", "10px 800", 4.5),
    ("Eyebrow da tela de acesso no cartao", "style.css:47; App.tsx:144", "#5f7290", "#ffffff", "10px 800", 4.5),
    ("Rodape (footer) na pagina", "style.css:65", "#66768a", "#f4f7fb", "11px", 4.5),
    ("Link (a) no cartao", "style.css:30", "#1d5f86", "#ffffff", "13-14px", 4.5),
    ("Link da barra superior na pagina", "style.css:30,62", "#1d5f86", "#f4f7fb", "13px 700", 4.5),
    ("Titulo da barra lateral .sidebar-title", "style.css:48", "#8ea6c8", "#0a1730", "10px 800", 4.5),
    ("Subtitulo da marca .brand span", "style.css:45", "#a9bbd6", "#0a1730", "11px", 4.5),
    ("Item de navegacao lateral", "style.css:50", "#b4c4dc", "#0a1730", "~14px 600", 4.5),
    ("Item de navegacao atual/hover", "style.css:51", "#ffffff", "#203657", "~14px 600", 4.5),
    ("Rodape da barra lateral .side-bottom", "style.css:54", "#b4c4dc", "#0a1730", "12px", 4.5),
    ("Botao Sair da barra lateral", "style.css:55", "#dbe6f5", "#0a1730", "12px", 4.5),
    ("Chip de perfil", "style.css:63", "#44586e", "#eef2f7", "12px", 4.5),
    ("Botao primario (texto branco em --brand)", "style.css:104", "#ffffff", "#176b61", "13px 800", 4.5),
    ("Botao secundario", "style.css:108", "#24415e", "#ffffff", "13px 800", 4.5),
    ("Botao inline", "style.css:111", "#11604f", "#e9f6f1", "12px 800", 4.5),
    ("Botao inline.quiet", "style.css:112", "#44586e", "#f1f4f8", "12px 800", 4.5),
    ("Botao inline pressionado (aria-pressed)", "style.css:113", "#11604f", "#cdeee2", "12px 800", 4.5),
    ("Status good", "style.css:128", "#12704a", "#ddf6e9", "11px 800", 4.5),
    ("Status bad", "style.css:129", "#a83a2e", "#ffe9e7", "11px 800", 4.5),
    ("Status warn", "style.css:130", "#6f560c", "#fff4cf", "11px 800", 4.5),
    ("Status neutral", "style.css:131", "#44586e", "#eef2f7", "11px 800", 4.5),
    ("Aviso de sucesso", "style.css:143", "#134f42", "#e9f5f1", "13px", 4.5),
    ("Aviso de erro", "style.css:144", "#7c2318", "#fff2f0", "13px", 4.5),
    ("Meta do aviso de erro (opacidade .95)", "style.css:145", blend("#7c2318", "#fff2f0", 0.95), "#fff2f0", "12px", 4.5),
    ("Meta do aviso de sucesso (opacidade .95)", "style.css:145", blend("#134f42", "#e9f5f1", 0.95), "#e9f5f1", "12px", 4.5),
    ("Codigo (code)", "style.css:124", "#2f5b8a", "#f1f5f9", "12px", 4.5),
    ("Texto digitado em campo", "style.css:89", "#243b55", "#ffffff", "14px", 4.5),
    ("Paragrafo da tela de acesso", "style.css:158", "#4a5d73", "#ffffff", "14px", 4.5),
    ("Link de pular conteudo .skip", "style.css:37", "#182943", "#ffffff", "14px 700", 4.5),
    # 1.4.11 - contraste nao textual (componentes e indicador de foco)
    ("Borda de input/select/textarea (--line-strong) no cartao", "style.css:9,89", "#cfdae6", "#ffffff", "borda 1px", 3.0),
    ("Borda de botao secundario (--line-strong)", "style.css:108", "#cfdae6", "#ffffff", "borda 1px", 3.0),
    ("Fundo do botao inline vs cartao", "style.css:111", "#e9f6f1", "#ffffff", "fundo do controle", 3.0),
    ("Fundo do botao inline.quiet vs cartao", "style.css:112", "#f1f4f8", "#ffffff", "fundo do controle", 3.0),
    ("Indicador de foco (--focus) no cartao", "style.css:14,33", "#2f7fd8", "#ffffff", "contorno 3px", 3.0),
    ("Indicador de foco (--focus) na pagina", "style.css:14,33", "#2f7fd8", "#f4f7fb", "contorno 3px", 3.0),
    ("Foco na barra lateral", "style.css:53", "#7fb5ff", "#0a1730", "contorno 3px", 3.0),
    ("Borda de campo invalido (--bad)", "style.css:92", "#a83a2e", "#ffffff", "borda 1px", 3.0),
    ("Caixa de selecao (accent --brand)", "style.css:96", "#176b61", "#ffffff", "controle 18px", 3.0),
]


def main() -> None:
    print("| Elemento | Local | Primeiro plano | Fundo | Tamanho | Razao | Exigido | Passa? |")
    print("|---|---|---|---|---|---|---|---|")
    failures = 0
    for name, where, fg, bg, size, needed in PAIRS:
        value = ratio(fg, bg)
        ok = value >= needed
        failures += not ok
        print(f"| {name} | {where} | `{fg}` | `{bg}` | {size} | {value:.2f}:1 | {needed}:1 | {'sim' if ok else 'NAO'} |")
    print(f"\nPares avaliados: {len(PAIRS)}; abaixo do minimo: {failures}")


if __name__ == "__main__":
    main()
