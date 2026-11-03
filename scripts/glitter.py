"""Glitter: brilhinhos de 4 pontas que piscam (camada transparente, quadro a quadro).

Uso: python3 scripts/glitter.py <pasta_saida> <duracao_s> [fps] [qtd] [semente]
Gera <pasta_saida>/glitter_0001.png ... (1080x1920 RGBA), para sobrepor com ffmpeg
(-framerate <fps> -i glitter_%04d.png) ou importar no CapCut como sequência.

Cores pastel de Natal + branco e dourado claro. Mais brilhos perto do centro (onde fica o
gancho) e alguns espalhados. Cada brilho pisca numa curva seno com fase e velocidade próprias,
e some nos últimos 0,3 s.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

CORES = [(255, 255, 255), (255, 244, 200), (246, 227, 161), (255, 214, 224), (200, 236, 214)]


def brilho(tam, cor):
    """Estrela de 4 pontas com halo suave."""
    s = tam * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c, r, w = s / 2, tam * 1.6, tam * 0.22
    d.polygon([(c, c - r), (c + w, c - w), (c + r, c), (c + w, c + w), (c, c + r), (c - w, c + w), (c - r, c), (c - w, c - w)],
              fill=cor + (255,))
    halo = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse([c - tam * 0.7, c - tam * 0.7, c + tam * 0.7, c + tam * 0.7], fill=cor + (170,))
    halo = halo.filter(ImageFilter.GaussianBlur(tam * 0.5))
    return Image.alpha_composite(halo, im)


def main(saida, duracao, fps=30, qtd=80, semente=3):
    rnd = random.Random(semente)
    os.makedirs(saida, exist_ok=True)
    itens = []
    for k in range(qtd):
        if k < qtd * 0.65:  # concentrados em volta do gancho (meio da tela)
            x, y = rnd.gauss(540, 260), rnd.gauss(950, 230)
        else:
            x, y = rnd.uniform(40, 1040), rnd.uniform(250, 1650)
        tam = rnd.choice([10, 14, 18, 22, 26, 32, 38])
        itens.append({"x": x, "y": y, "spr": brilho(tam, rnd.choice(CORES)), "fase": rnd.uniform(0, 2 * math.pi),
                      "vel": rnd.uniform(5, 11), "giro": rnd.uniform(0, 45)})
    n = int(round(duracao * fps))
    for f in range(n):
        t = f / fps
        saida_fim = max(0.0, min(1.0, (duracao - t) / 0.3))
        q = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        for it in itens:
            a = max(0.0, math.sin(it["fase"] + it["vel"] * t)) ** 2 * saida_fim
            if a < 0.05:
                continue
            esc = 0.6 + 0.4 * a
            spr = it["spr"].resize((max(2, int(it["spr"].width * esc)),) * 2, Image.LANCZOS).rotate(it["giro"])
            al = spr.getchannel("A").point(lambda v: int(v * a))
            spr.putalpha(al)
            q.alpha_composite(spr, (int(it["x"] - spr.width / 2), int(it["y"] - spr.height / 2)))
        q.save(os.path.join(saida, f"glitter_{f + 1:04d}.png"))
    print(f"{n} quadros em {saida}")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], float(a[2]), *[int(x) for x in a[3:]])
