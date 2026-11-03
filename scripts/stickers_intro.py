"""Efeito de introdução: stickers parados que mexem de leve a cada meio segundo (stop-motion).

Pedido da Fran (03/11/2026): os stickers NÃO trocam. Os mesmos ficam na tela o tempo todo
da introdução e, a cada passo (0,5 s), só mudam um pouco o ângulo (rotação), como um adesivo
animado quadro a quadro. Posição e tamanho ficam fixos.

Uso: python3 scripts/stickers_intro.py projetos/<nome> [duracao_s] [passo_s]
Lê <projeto>/layout_intro.json:
  [{"sticker": "D3_gatinho_arvore", "x": 180, "y": 700, "lado": 260, "giro": -8}, ...]
  (x, y = centro em 1080x1920; lado = maior lado em px; giro = ângulo base em graus)
Stickers: os PNGs aprovados em <projeto>/stickers/.
Gera <projeto>/saida/capcut/stickers_intro/intro_01.png, ... (1080x1920 transparente, um por passo).
No CapCut: cada PNG numa faixa de sobreposição com a duração do passo, um atrás do outro.
"""
import glob
import json
import os
import random
import sys

from PIL import Image

MEXE = {"desloca_px": 0, "giro_graus": 6, "escala": 0.0}  # Fran (03/11): só gira; não anda em x/y nem muda de tamanho


def main(projeto, duracao=3.0, passo=0.5, semente=7):
    rnd = random.Random(semente)
    layout = json.load(open(os.path.join(projeto, "layout_intro.json")))
    imgs = {s["sticker"]: Image.open(os.path.join(projeto, "stickers", s["sticker"] + ".png")).convert("RGBA")
            for s in layout}
    destino = os.path.join(projeto, "saida", "capcut", "stickers_intro")
    os.makedirs(destino, exist_ok=True)
    for f in glob.glob(os.path.join(destino, "intro_*.png")):
        os.remove(f)
    n = int(round(duracao / passo))
    roteiro = []
    for k in range(n):
        quadro = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        for s in layout:
            img = imgs[s["sticker"]]
            f = min(s["lado"] / max(img.size), 2.0) * (1 + rnd.uniform(-MEXE["escala"], MEXE["escala"]))
            giro = s.get("giro", 0) + rnd.uniform(-MEXE["giro_graus"], MEXE["giro_graus"])
            t = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
            t = t.rotate(giro, expand=True, resample=Image.BICUBIC)
            cx = s["x"] + rnd.randint(-MEXE["desloca_px"], MEXE["desloca_px"])
            cy = s["y"] + rnd.randint(-MEXE["desloca_px"], MEXE["desloca_px"])
            quadro.alpha_composite(t, (cx - t.width // 2, cy - t.height // 2))
        arq = f"intro_{k + 1:02d}.png"
        quadro.save(os.path.join(destino, arq))
        roteiro.append({"arquivo": arq, "de": round(k * passo, 2), "ate": round((k + 1) * passo, 2)})
    json.dump({"layout": layout, "passos": roteiro}, open(os.path.join(destino, "roteiro.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"{n} quadros em {destino}")


if __name__ == "__main__":
    main(sys.argv[1], *[float(a) for a in sys.argv[2:]])
