"""Revisão cruzada de QUA-08 (independente): razão de contraste WCAG 2.1 dos pares do style.css (cálculo próprio)."""


def canal(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def razao(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


pares = [
    ("rodapé #66768a sobre --page #f4f7fb (style.css:65; body:26)", "#66768a", "#f4f7fb", 4.5),
    ("borda do campo --line-strong #cfdae6 sobre branco (style.css:9, 89)", "#cfdae6", "#ffffff", 3.0),
    ("borda do botão secundário #cfdae6 sobre branco (style.css:108)", "#cfdae6", "#ffffff", 3.0),
    ("--muted #5a6b80 sobre branco (rótulos, th)", "#5a6b80", "#ffffff", 4.5),
    ("--muted #5a6b80 sobre .stat #f7f9fc (style.css:79-80)", "#5a6b80", "#f7f9fc", 4.5),
    ("--text #41566e sobre branco (texto de apoio)", "#41566e", "#ffffff", 4.5),
    ("eyebrow #5f7290 sobre --page #f4f7fb (style.css:47; App.tsx:112)", "#5f7290", "#f4f7fb", 4.5),
    ("texto do botão branco sobre --brand #176b61 (style.css:104)", "#ffffff", "#176b61", 4.5),
]
for rotulo, texto, fundo, minimo in pares:
    valor = razao(texto, fundo)
    print(f"{valor:5.2f}:1  minimo {minimo}:1  {'OK ' if valor >= minimo else 'ABAIXO'}  {rotulo}")
