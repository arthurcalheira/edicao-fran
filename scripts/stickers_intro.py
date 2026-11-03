"""Efeito de introdução: stickers que trocam a cada meio segundo (stop-motion).

Uso: python3 scripts/stickers_intro.py projetos/<nome> [duracao_s] [passo_s]
Stickers: os PNGs em <projeto>/stickers/ (os que a Fran aprovou). 3 por passo, sem repetir o passo anterior.
Gera em <projeto>/saida/capcut/stickers_intro/ um PNG transparente 1080x1920 por passo
(intro_01.png, intro_02.png, ...). No CapCut, cada PNG entra numa faixa de sobreposição
com a duração do passo (0,5 s), um atrás do outro.

Os stickers ficam nas bordas (cantos e laterais), longe do rosto e do centro, em posição,
tamanho e giro que mudam a cada passo.
"""
import glob
import json
import os
import random
import sys

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Zonas (x0, y0, x1, y1) para o centro do sticker: cantos e laterais, fora da faixa do rosto e da legenda.
ZONAS = [(150, 640, 360, 820), (720, 640, 930, 820),      # cantos de cima (abaixo do gancho escrito)
         (110, 960, 240, 1200), (840, 960, 970, 1200),     # laterais no meio
         (150, 1350, 400, 1550), (680, 1350, 930, 1550)]  # cantos de baixo (acima da legenda do Reels)


def main(projeto, duracao=3.0, passo=0.5, semente=7):
    rnd = random.Random(semente)
    arqs = sorted(glob.glob(os.path.join(projeto, "stickers", "*.png")))
    imgs = {os.path.basename(a)[:-4]: Image.open(a).convert("RGBA") for a in arqs}
    POOL = list(imgs)
    destino = os.path.join(projeto, "saida", "capcut", "stickers_intro")
    os.makedirs(destino, exist_ok=True)
    for f in glob.glob(os.path.join(destino, "intro_*.png")):
        os.remove(f)
    n = int(round(duracao / passo))
    roteiro, ultimo = [], set()
    for k in range(n):
        quadro = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        zonas = rnd.sample(range(len(ZONAS)), 3)  # 3 stickers por passo, em 3 das 6 zonas
        nomes = rnd.sample([p for p in POOL if p not in ultimo] or POOL, 3)  # não repete o passo anterior
        ultimo = set(nomes)
        itens = []
        for z, nome in zip(zonas, nomes):
            x0, y0, x1, y1 = ZONAS[z]
            img = imgs[nome]
            alvo = rnd.randint(240, 320)  # maior lado, em px; no máximo 2x o original para não borrar
            f = min(alvo / max(img.size), 2.0)
            s = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS).rotate(rnd.uniform(-18, 18), expand=True,
                                                                       resample=Image.BICUBIC)
            cx, cy = rnd.randint(x0, x1), rnd.randint(y0, y1)
            quadro.alpha_composite(s, (cx - s.width // 2, cy - s.height // 2))
            itens.append(nome)
        arq = f"intro_{k + 1:02d}.png"
        quadro.save(os.path.join(destino, arq))
        roteiro.append({"arquivo": arq, "de": round(k * passo, 2), "ate": round((k + 1) * passo, 2), "stickers": itens})
    json.dump(roteiro, open(os.path.join(destino, "roteiro.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{n} quadros em {destino}")


if __name__ == "__main__":
    main(sys.argv[1], *[float(a) for a in sys.argv[2:]])
