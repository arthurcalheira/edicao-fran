"""Versão "luxo": serifada, preto e branco, sombra suave, sem animação na legenda.

Uso: python3 scripts/render_luxo.py projetos/<nome>
Lê <projeto>/saida/cortado.json e estilo_luxo.json. Grava <projeto>/saida/final_luxo.mp4 (e legenda_luxo.ass).
- Palavra-chave (lista "destaques" do plano) em itálico, sem cor.
- Textos do plano: *assim* vira itálico; no gancho, "SOBRETÍTULO | título".
- Enquanto o gancho ou o texto final estão na tela, a legenda some (o texto já repete a fala).
- Precisa das fontes Playfair Display instaladas (ver README).
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from legenda_blocos import blocos  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t // 60) % 60:02d}:{t % 60:05.2f}"


def italico(txt):
    return re.sub(r"\*(.+?)\*", r"{\\i1}\1{\\i0}", EMOJI.sub("", txt)).strip()


def main(projeto):
    e = json.load(open(os.path.join(RAIZ, "estilo_luxo.json")))
    d = json.load(open(os.path.join(projeto, "saida", "cortado.json")))
    F, FC, sp = e["fonte"], e["fonte_caixa_alta"], e["espacamento_caixa_alta"]
    fad = r"\fad({},{})".format(*e["fade_ms"])
    caps = lambda tam: rf"{{\fn{FC}\fs{tam}\fsp{sp}}}"  # noqa: E731
    ev = []

    def texto(ini, fim, txt, x, y, an, efeito=""):
        """Sombra em duas camadas (larga e desfocada + curta e nítida) e o texto branco por cima."""
        for s in e["sombra"]:
            ev.append(f"Dialogue: 0,{ts(ini)},{ts(fim)},T,,0,0,0,,{{\\an{an}\\pos({x + s['dx']},{y + s['dy']})"
                      f"\\bord{s.get('bord', 0)}\\3c&H000000&\\3a&H{s['alfa']}&\\blur{s['blur']}\\1c&H000000&\\1a&H{s['alfa']}&{efeito}}}{txt}")
        ev.append(f"Dialogue: 1,{ts(ini)},{ts(fim)},T,,0,0,0,,{{\\an{an}\\pos({x},{y}){efeito}}}{txt}")

    # Janelas em que a legenda fica escondida.
    tampa = [(t["de"], t["ate"]) for t in d["textos"] if t["tipo"] in ("gancho", "final")]
    livre = lambda a, b: not any(a < y and b > x for x, y in tampa)  # noqa: E731

    destaques = {x.lower() for x in d["destaques"]}
    for b in blocos(d["palavras"], e["legenda"]["palavras_por_bloco"], max_dur=1.8):
        if not livre(b["i"], b["f"]):
            continue
        partes = []
        for w in b["palavras"]:
            p = EMOJI.sub("", w["p"])
            partes.append(rf"{{\i1}}{p}{{\i0}}" if p.strip(".,!?…").lower() in destaques else p)
        texto(b["i"], b["f"], " ".join(partes).replace(" %", "%"), 540, e["legenda"]["y_base"], 2)

    for t in d["textos"]:
        de, ate = t["de"], t["ate"]
        if t["tipo"] == "gancho":
            sup, _, tit = t["texto"].partition("|")
            txt = caps(e["gancho"]["tamanho_sup"]) + sup.strip() + r"\N{\fs18} \N" + \
                rf"{{\fn{F}\fs{e['gancho']['tamanho']}\fsp0}}" + italico(tit)
            texto(de, ate, txt, 540, e["gancho"]["y_base"], 2, fad)
        elif t["tipo"] == "final":
            texto(de, ate, rf"{{\fs{e['final']['tamanho']}}}" + italico(t["texto"]), 540, e["final"]["y_base"], 2, fad)
        elif t["tipo"] == "rotulo":
            texto(de, ate, caps(e["rotulo"]["tamanho"]) + t["texto"], 540, e["rotulo"]["y_base"], 2, fad)
        elif t["tipo"] == "cta":
            texto(de, ate, caps(e["cta"]["tamanho"]) + t["texto"], 540, e["cta"]["y_base"], 2, fad)

    ass = os.path.join(projeto, "saida", "legenda_luxo.ass")
    open(ass, "w").write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: T,{F},{e['legenda']['tamanho']},&H00FFFFFF,&H0,&H0,&H0,0,0,0,0,100,100,0,0,1,0,0,2,70,70,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(ev) + "\n")

    vf = "[0:v]null[base]"
    if d["zooms"]:
        z = e["zoom_padrao"]
        janelas = "+".join(f"between(t,{x['de']},{x['ate']})" for x in d["zooms"])
        vf = (f"[0:v]split[a][b];[b]crop=iw/{z}:ih/{z},scale=1080:1920[z];"
              f"[a][z]overlay=0:0:enable='{janelas}'[base]")
    fontes = os.path.expanduser("~/.fonts")
    vf += f";[base]ass={ass}:fontsdir={fontes}[v]"
    destino = os.path.join(projeto, "saida", "final_luxo.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(projeto, "saida", "cortado.mp4"),
                    "-filter_complex", vf, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", destino], check=True)
    print("ok:", destino)


if __name__ == "__main__":
    main(sys.argv[1])
