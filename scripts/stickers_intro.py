"""Efeito de introdução: stickers que trocam a cada meio segundo (stop-motion).

Uso: python3 scripts/stickers_intro.py projetos/<nome> [duracao_s] [passo_s]
Gera em <projeto>/saida/capcut/stickers_intro/ um PNG transparente 1080x1920 por passo
(intro_01.png, intro_02.png, ...). No CapCut, cada PNG entra numa faixa de sobreposição
com a duração do passo (0,5 s), um atrás do outro.

Os stickers ficam nas bordas (cantos e laterais), longe do rosto e do centro, em posição,
tamanho e giro que mudam a cada passo. Pasta de stickers: assets/stickers/ (Fluent Emoji 3D, MIT).
"""
import glob
import json
import os
import random
import sys

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL = ["ribbon_3d", "wrapped_gift_3d", "christmas_tree_3d", "star_3d", "glowing_star_3d", "sparkles_3d",
        "bell_3d", "snowflake_3d", "sparkling_heart_3d"]
# Zonas (x0, y0, x1, y1) para o centro do sticker: cantos e laterais, fora da faixa do rosto e da legenda.
ZONAS = [(140, 330, 380, 560), (700, 330, 940, 560),      # cantos de cima (abaixo da barra do Reels)
         (110, 700, 260, 1000), (820, 700, 970, 1000),     # laterais no meio
         (150, 1350, 400, 1550), (680, 1350, 930, 1550)]  # cantos de baixo (acima da legenda do Reels)


def main(projeto, duracao=3.0, passo=0.5, semente=7):
    rnd = random.Random(semente)
    imgs = {n: Image.open(os.path.join(RAIZ, "assets", "stickers", n + ".png")).convert("RGBA") for n in POOL}
    destino = os.path.join(projeto, "saida", "capcut", "stickers_intro")
    os.makedirs(destino, exist_ok=True)
    for f in glob.glob(os.path.join(destino, "intro_*.png")):
        os.remove(f)
    n = int(round(duracao / passo))
    roteiro, ultimo = [], set()
    for k in range(n):
        quadro = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        zonas = rnd.sample(range(len(ZONAS)), 4)  # 4 stickers por passo, em 4 das 6 zonas
        nomes = rnd.sample([p for p in POOL if p not in ultimo] or POOL, 4)  # não repete o passo anterior
        ultimo = set(nomes)
        itens = []
        for z, nome in zip(zonas, nomes):
            x0, y0, x1, y1 = ZONAS[z]
            lado = rnd.randint(230, 330)
            s = imgs[nome].resize((lado, lado), Image.LANCZOS).rotate(rnd.uniform(-18, 18), expand=True,
                                                                       resample=Image.BICUBIC)
            cx, cy = rnd.randint(x0, x1), rnd.randint(y0, y1)
            quadro.alpha_composite(s, (cx - s.width // 2, cy - s.height // 2))
            itens.append(nome.replace("_3d", ""))
        arq = f"intro_{k + 1:02d}.png"
        quadro.save(os.path.join(destino, arq))
        roteiro.append({"arquivo": arq, "de": round(k * passo, 2), "ate": round((k + 1) * passo, 2), "stickers": itens})
    json.dump(roteiro, open(os.path.join(destino, "roteiro.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{n} quadros em {destino}")


if __name__ == "__main__":
    main(sys.argv[1], *[float(a) for a in sys.argv[2:]])
