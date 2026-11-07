"""Capa do Reels a partir de uma foto, no mesmo estilo dos textos do vídeo (luxo: Playfair branco, sombra leve).

Uso: python3 scripts/capa.py projetos/<nome> <foto> "<SOBRETÍTULO>" "<título com *itálico*>" [y_texto]
Grava <projeto>/saida/capa.jpg (1080x1920) e saida/capa_grade.jpg (recorte 3:4 que aparece na grade do perfil).

A foto 3:4 entra inteira no miolo 1080x1440 (é exatamente o que a grade do perfil mostra); em cima e embaixo,
a própria foto ampliada e desfocada completa os 1920 px. O texto fica dentro do miolo, na parte de cima
(teto/fundo), longe do rosto e da peça.
"""
import os
import subprocess
import sys

from PIL import Image, ImageFilter, ImageOps

FONTES = os.path.expanduser("~/.fonts")


def main(projeto, foto, sup, titulo, y_texto=330):
    saida = os.path.join(projeto, "saida")
    os.makedirs(saida, exist_ok=True)
    im = ImageOps.exif_transpose(Image.open(foto)).convert("RGB")
    # miolo 3:4
    alvo = 1080 / 1440
    w, h = im.size
    if w / h > alvo:
        nw = int(h * alvo)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / alvo)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    miolo = im.resize((1080, 1440), Image.LANCZOS)
    fundo = im.resize((1440, 1920), Image.LANCZOS).crop((180, 0, 1260, 1920)).filter(ImageFilter.GaussianBlur(40))
    fundo.paste(miolo, (0, 240))
    base = os.path.join(saida, "capa_base.png")
    fundo.save(base)
    tit = titulo
    while "*" in tit:
        tit = tit.replace("*", r"{\i1}", 1).replace("*", r"{\i0}", 1)
    corpo = (rf"{{\fnPlayfair Display SemiBold\fs56\fsp7}}{sup}\N{{\fs16}} \N"
             rf"{{\fnPlayfair Display\fs124\fsp0}}{tit}")
    ass = os.path.join(saida, "capa.ass")
    open(ass, "w").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding\n"
        "Style: T,Playfair Display,100,&H00FFFFFF,&H0,&H0,&H0,0,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        rf"Dialogue: 0,0:00:00.00,0:00:05.00,T,,0,0,0,,{{\an8\pos(543,{y_texto + 5})\blur8\1c&H000000&\1a&H40&}}{corpo}" "\n"
        rf"Dialogue: 1,0:00:00.00,0:00:05.00,T,,0,0,0,,{{\an8\pos(540,{y_texto})}}{corpo}" "\n")
    capa = os.path.join(saida, "capa.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", base, "-vf", f"ass={ass}:fontsdir={FONTES}",
                    "-frames:v", "1", "-q:v", "2", capa], check=True)
    Image.open(capa).crop((0, 240, 1080, 1680)).save(os.path.join(saida, "capa_grade.jpg"), quality=92)
    os.remove(base)
    print("ok:", capa)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], a[4], *[int(x) for x in a[5:]])
