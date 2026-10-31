"""Versão A: textos e legenda com ffmpeg + libass, sobre o cortado.mp4.

Uso: python3 scripts/render_ffmpeg.py projetos/<nome>
Grava <projeto>/saida/final_ffmpeg.mp4 (e legenda.ass, para conferir).
Limite conhecido: o libass não desenha emoji colorido, então os emojis são removidos dos textos.
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


def cor(hexa, alfa="00"):
    h = hexa.lstrip("#")
    return f"&H{alfa}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t // 60) % 60:02d}:{t % 60:05.2f}"


def limpo(txt):
    return re.sub(r"\s{2,}", " ", EMOJI.sub("", txt)).strip()


def main(projeto):
    e = json.load(open(os.path.join(RAIZ, "estilo.json")))
    d = json.load(open(os.path.join(projeto, "saida", "cortado.json")))
    f, amarelo, rosa = e["fonte"], cor(e["cor_destaque"]), cor(e["cor_cta"])
    estilos = [
        # Nome, fonte, tamanho, cor, cor2, contorno, fundo, negrito, ..., borda, contorno, sombra, alinh, mL, mR, mV
        f"Style: Leg,{f},{e['legenda']['tamanho']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,7,0,2,80,80,{1920 - e['legenda']['y_base']},1",
        f"Style: Gancho,{f},{e['gancho']['tamanho']},&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,20,0,8,110,110,{e['gancho']['y_topo']},1",
        f"Style: Meio,{f},62,&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,16,0,8,110,110,{e['gancho']['y_topo']},1",
        f"Style: CTA,{f},{e['cta']['tamanho']},&H00FFFFFF,&H00FFFFFF,{rosa},{rosa},-1,0,0,0,100,100,0,0,3,14,0,9,80,80,{e['cta']['y_topo']},1",
        f"Style: Rotulo,{f},{e['rotulo']['tamanho']},&H00FFFFFF,&H00FFFFFF,&H64000000,&H64000000,-1,0,0,0,100,100,0,0,3,12,0,7,80,80,{e['rotulo']['y_topo']},1",
    ]
    ev = []
    destaques = {x.lower() for x in d["destaques"]}
    for b in blocos(d["palavras"], e["legenda"]["palavras_por_bloco"]):
        ws = b["palavras"]
        for k, w in enumerate(ws):
            ini = w["i"] if k else b["i"]
            fim = ws[k + 1]["i"] if k + 1 < len(ws) else b["f"]
            partes = []
            for j, x in enumerate(ws):
                chave = x["p"].strip(".,!?…").lower() in destaques
                c = amarelo if chave else "&H00FFFFFF"
                esc = r"\fscx112\fscy112" if j == k else ""
                partes.append(f"{{\\c{c}{esc}}}{limpo(x['p'])}{{\\r}}")
            ev.append(f"Dialogue: 0,{ts(ini)},{ts(fim)},Leg,,0,0,0,,{' '.join(partes)}")
    mapa = {"gancho": "Gancho", "final": "Gancho", "meio": "Meio", "cta": "CTA", "rotulo": "Rotulo"}
    for t in d["textos"]:
        txt = limpo(t["texto"])
        if t["tipo"] in ("gancho", "final", "meio"):
            txt = txt.replace(" · ", r"\N")
        de = t["de"]
        if t["tipo"] == "cta":  # o CTA some enquanto o texto final (que já pede o QUERO) está na tela
            finais = [x["de"] for x in d["textos"] if x["tipo"] == "final"]
            for a, b in [(de, finais[0]), ] if finais else [(de, t["ate"])]:
                ev.append(f"Dialogue: 1,{ts(a)},{ts(b)},CTA,,0,0,0,,{txt}")
            continue
        ev.append(f"Dialogue: 2,{ts(de)},{ts(t['ate'])},{mapa[t['tipo']]},,0,0,0,,{txt}")
    ass = os.path.join(projeto, "saida", "legenda.ass")
    open(ass, "w").write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
                         "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
                         "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
                         "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" + "\n".join(estilos) +
                         "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" +
                         "\n".join(ev) + "\n")
    # Zoom seco (punch-in): uma cópia recortada entra por cima nos intervalos marcados.
    vf = "[0:v]null[base]"
    if d["zooms"]:
        z = d["zooms"][0].get("escala", e["zoom_padrao"])
        janelas = "+".join(f"between(t,{x['de']},{x['ate']})" for x in d["zooms"])
        vf = (f"[0:v]split[a][b];[b]crop=iw/{z}:ih/{z},scale=1080:1920[z];"
              f"[a][z]overlay=0:0:enable='{janelas}'[base]")
    vf += f";[base]ass={ass}[v]"
    destino = os.path.join(projeto, "saida", "final_ffmpeg.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(projeto, "saida", "cortado.mp4"),
                    "-filter_complex", vf, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", destino], check=True)
    print("ok:", destino)


if __name__ == "__main__":
    main(sys.argv[1])
