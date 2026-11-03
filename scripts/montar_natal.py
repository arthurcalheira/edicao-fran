"""Monta um Reel de Natal/achadinhos a partir de mais de um arquivo bruto (só trechos falados).

Uso: python3 scripts/montar_natal.py projetos/<nome>
Lê <projeto>/plano.json (fontes, trechos, gancho, rótulos, stickers, zooms, CTA, destaques, correções),
<projeto>/layout_intro.json e os stickers aprovados em <projeto>/stickers/.

Saídas em <projeto>/saida/:
  base_cortes.mp4             cortes (só fala, pausas > pausa_max_s fora) + zoom vai e volta, voz em -14 LUFS
  final.mp4                   vídeo pronto: abertura (glitter, título animado, stickers, efeito sonoro),
                              rótulos com sticker de cada peça, legenda e CTA
  capcut/base_capcut.mp4      base para o CapCut: cortes + zoom + abertura completa, sem legenda/rótulos/CTA
  capcut/legenda.srt          legenda para importar no CapCut (Legendas > Importar)
  capcut/textos/*.png         rótulos e CTA em PNG transparente 1080x1920 (já na posição certa)
  capcut/stickers/*.png       stickers aprovados
  capcut/sfx_brilho.wav       efeito sonoro da abertura
  capcut/roteiro.md           tempos de cada sticker, texto e efeito
Regras da Fran: ver CLAUDE.md (só fala, legenda Montserrat, gancho pastel no meio, stickers pequenos girando).
"""
import glob
import json
import os
import random
import shutil
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from legenda_blocos import blocos  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
FONTES_DIR = os.path.expanduser("~/.fonts")
LEG = {"fonte": "Montserrat SemiBold", "tam": 74, "y": 1180}
ROTULO = {"y": 360, "tam": 68, "cor": "#EE8E9C", "dur": 2.6}
STICKER_ITEM = {"x": 540, "y": 215, "lado": 150, "dur": 2.6}
PASSO = 0.5  # stickers mexem (só rotação) a cada meio segundo


def bgr(h):
    h = h.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t // 60) % 60:02d}:{t % 60:05.2f}"


def srt_ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def pedacos(plano, palavras):
    """Cada trecho vira pedaços só com fala: encosta nas palavras e tira pausas longas."""
    lim, folga_i, folga_f = plano.get("pausa_max_s", 0.3), 0.08, 0.12
    out = []
    for k, tr in enumerate(plano["trechos"]):
        ws = [w for w in palavras[tr["fonte"]] if tr["de"] - 0.05 <= w["i"] < tr["ate"]]
        if not ws:
            continue
        a = max(tr["de"], ws[0]["i"] - folga_i)
        for w0, w1 in zip(ws, ws[1:]):
            if w1["i"] - w0["f"] > lim:
                out.append({"tr": k, "fonte": tr["fonte"], "a": a, "b": min(w0["f"] + folga_f, tr["ate"])})
                a = w1["i"] - folga_i
        out.append({"tr": k, "fonte": tr["fonte"], "a": a, "b": min(ws[-1]["f"] + folga_f, tr["ate"])})
    t = 0.0
    for p in out:
        p["ini"], t = t, t + (p["b"] - p["a"])
        p["fim"] = t
    return out


def mapa(pcs, fonte, t, tr=None):
    for p in pcs:
        if p["fonte"] == fonte and p["a"] <= t < p["b"] and (tr is None or p["tr"] == tr):
            return p["ini"] + (t - p["a"])
    return None


def janela_trecho(pcs, k):
    ps = [p for p in pcs if p["tr"] == k]
    return (ps[0]["ini"], ps[-1]["fim"]) if ps else None


def main(projeto):
    plano = json.load(open(os.path.join(projeto, "plano.json")))
    fontes = list(plano["fontes"])
    palavras = {f: json.load(open(os.path.join(projeto, plano["fontes"][f][1])))["palavras"] for f in fontes}
    pcs = pedacos(plano, palavras)
    dur = round(pcs[-1]["fim"], 3)
    saida = os.path.join(projeto, "saida")
    kit = os.path.join(saida, "capcut")
    for d in (saida, kit, os.path.join(kit, "textos"), os.path.join(kit, "stickers")):
        os.makedirs(d, exist_ok=True)
    gancho_fim = max(janela_trecho(pcs, k)[1] for k in plano["gancho"]["trechos"])

    # ---------- 1. cortes + zoom vai e volta ----------
    # Cada pedaço vira um arquivo (busca rápida, recodifica em 1080x1920/30 fps), depois junta com concat.
    tmpd = os.path.join(saida, "pedacos_tmp")
    shutil.rmtree(tmpd, ignore_errors=True)
    os.makedirs(tmpd)
    lista = []
    for j, p in enumerate(pcs):
        arq = os.path.join(tmpd, f"p{j:03d}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{p['a']:.3f}", "-i",
                        os.path.join(projeto, plano["fontes"][p["fonte"]][0]), "-t", f"{p['b'] - p['a']:.3f}",
                        "-vf", f"fps={FPS},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                        "-af", "aresample=48000", "-ac", "2", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
                        "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", arq.replace(".mp4", ".mov")], check=True)
        lista.append(f"file '{os.path.basename(arq).replace('.mp4', '.mov')}'")
    open(os.path.join(tmpd, "lista.txt"), "w").write("\n".join(lista) + "\n")
    fil = []
    zooms = []
    for k, tr in enumerate(plano["trechos"]):
        if "zoom" in tr:
            a, b = mapa(pcs, tr["fonte"], tr["zoom"][0], k), mapa(pcs, tr["fonte"], tr["zoom"][1] - 0.01, k)
            if a is None:
                a = janela_trecho(pcs, k)[0]
            if b is None:
                b = janela_trecho(pcs, k)[1]
            zooms.append((round(a, 3), round(b, 3)))
    if zooms:
        curva = "+".join(f"between(in/{FPS},{a},{b})*sin(PI*(in/{FPS}-{a})/{b - a})" for a, b in zooms)
        fil.append(f"[vc]scale=2160:3840:flags=lanczos,zoompan=z='1+0.18*({curva})':d=1:"
                   f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=1080x1920:fps={FPS}[vz]")
    else:
        fil.append("[vc]null[vz]")
    fil.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[az]")
    fil.insert(0, "[0:v]null[vc];[0:a]anull[ac]")
    base = os.path.join(saida, "base_cortes.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmpd, "lista.txt"),
                    "-filter_complex", ";".join(fil), "-map", "[vz]",
                    "-map", "[az]", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", base], check=True)
    shutil.rmtree(tmpd)

    # ---------- 2. stickers (abertura + peças), um quadro a cada 0,5 s, só girando ----------
    rnd = random.Random(11)
    layout = json.load(open(os.path.join(projeto, "layout_intro.json")))
    imgs = {os.path.basename(a)[:-4]: Image.open(a).convert("RGBA")
            for a in glob.glob(os.path.join(projeto, "stickers", "*.png"))}
    for nome in imgs:
        shutil.copy(os.path.join(projeto, "stickers", nome + ".png"), os.path.join(kit, "stickers"))
    itens = []  # (de, ate, sticker, x, y, lado, giro_base)
    for s in layout:
        itens.append((0.0, gancho_fim, s["sticker"], s["x"], s["y"], s["lado"], s.get("giro", 0)))
    ctas = []
    for k, tr in enumerate(plano["trechos"]):
        jan = janela_trecho(pcs, k)
        if not jan:
            continue
        if "cta" in tr:
            c0 = mapa(pcs, tr["fonte"], tr["cta"]["de"], k) or jan[0]
            ctas.append((c0, jan[1], tr["cta"]["texto"]))
            if "sticker" in tr:
                itens.append((c0, jan[1], tr["sticker"], 880, 650, 170, 8))
        elif "sticker" in tr:
            itens.append((jan[0], min(jan[0] + STICKER_ITEM["dur"], dur), tr["sticker"], STICKER_ITEM["x"],
                          STICKER_ITEM["y"], STICKER_ITEM["lado"], rnd.choice([-7, 6, -5, 8])))
    seq = os.path.join(kit, "stickers_seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    n = int(dur / PASSO) + 1
    for q in range(n):
        t = q * PASSO + 0.01
        quadro = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        for de, ate, nome, x, y, lado, giro in itens:
            if de <= t < ate:
                img = imgs[nome]
                f = min(lado / max(img.size), 2.0)
                im = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
                im = im.rotate(giro + rnd.uniform(-6, 6), expand=True, resample=Image.BICUBIC)
                quadro.alpha_composite(im, (x - im.width // 2, y - im.height // 2))
        quadro.save(os.path.join(seq, f"st_{q + 1:04d}.png"))

    # ---------- 3. glitter e efeito sonoro da abertura ----------
    glit = os.path.join(kit, "glitter")
    shutil.rmtree(glit, ignore_errors=True)
    subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "glitter.py"), glit, f"{gancho_fim:.2f}", "30", "80"],
                   check=True, stdout=subprocess.DEVNULL)
    sfx = os.path.join(kit, "sfx_brilho.wav")
    subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "sfx_brilho.py"), sfx, "1.6"], check=True,
                   stdout=subprocess.DEVNULL)

    # ---------- 4. textos (ASS) ----------
    cab = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
           "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
           "MarginL, MarginR, MarginV, Encoding\n"
           "Style: T,Montserrat SemiBold,74,&H00FFFFFF,&H0,&H0,&H0,0,0,0,0,100,100,0,0,1,0,0,5,60,60,0,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

    def pop(ini_ms):
        return (rf"\fscx55\fscy55\alpha&HFF&\t({ini_ms},{ini_ms + 230},\fscx110\fscy110\alpha&H00&)"
                rf"\t({ini_ms + 230},{ini_ms + 380},\fscx100\fscy100)\fad(0,200)")

    def pastel(de, ate, txt, cor, tam, x, y, ital, ini_ms=0):
        f = rf"\fnPlayfair Display\b1\fs{tam}\i{1 if ital else 0}"
        return [rf"Dialogue: 0,{ts(de)},{ts(ate)},T,,0,0,0,,{{\an5\pos({x + 4},{y + 6})\bord6\3c&H000000&\3a&HB0&"
                rf"\blur6\1c&H000000&\1a&HB0&{f}{pop(ini_ms)}}}{txt}",
                rf"Dialogue: 1,{ts(de)},{ts(ate)},T,,0,0,0,,{{\an5\pos({x},{y})\bord5\3c&HFFFFFF&\1c{bgr(cor)}{f}"
                rf"{pop(ini_ms)}}}{txt}"]

    gancho_ev = []
    ys = [850, 1055]
    for j, (txt, cor, tam, ital) in enumerate(plano["gancho"]["linhas"]):
        gancho_ev += pastel(0, gancho_fim, txt, cor, tam, 540, ys[j], ital, ini_ms=250 * j)
    rotulos_ev, pngs = [], []
    for k, tr in enumerate(plano["trechos"]):
        jan = janela_trecho(pcs, k)
        if jan and "rotulo" in tr:
            fim = min(jan[0] + ROTULO["dur"], dur)
            ev = pastel(jan[0], fim, tr["rotulo"], ROTULO["cor"], ROTULO["tam"], 540, ROTULO["y"], False)
            rotulos_ev += ev
            pngs.append((f"rotulo_{len(pngs) + 1:02d}", ev, jan[0], fim, tr["rotulo"]))
    cta_ev = []
    for c0, c1, txt in ctas:
        partes = txt.split()
        corpo = (rf"{{\fnMontserrat Medium\fs60}}{' '.join(p for p in partes if p != 'QUERO')}\N"
                 rf"{{\fnMontserrat ExtraBold\fs130\bord5\3c&HFFFFFF&\1c{bgr('#EE8E9C')}}}QUERO")
        ev = [rf"Dialogue: 0,{ts(c0)},{ts(c1)},T,,0,0,0,,{{\an5\pos(544,786)\blur5\1c&H000000&\1a&HB0&"
              rf"\bord6\3c&H000000&\3a&HB0&{pop(0)}}}{corpo}",
              rf"Dialogue: 1,{ts(c0)},{ts(c1)},T,,0,0,0,,{{\an5\pos(540,780){pop(0)}}}{corpo}"]
        cta_ev += ev
        pngs.append(("cta_comenta_quero", ev, c0, c1, txt))

    # legenda: palavras remapeadas, corrigidas; some enquanto o gancho está na tela
    corr = {k.lower(): v for k, v in plano.get("correcoes", {}).items()}
    dest = {d.lower() for d in plano.get("destaques", [])}
    novas = []
    for p in pcs:
        for w in palavras[p["fonte"]]:
            if p["a"] <= w["i"] < p["b"]:
                txt = w["p"]
                nucleo = txt.strip(".,!?…").lower()
                if nucleo in corr:
                    novo = txt.lower().replace(nucleo, corr[nucleo])
                    txt = novo[0].upper() + novo[1:] if txt[:1].isupper() else novo
                i = p["ini"] + w["i"] - p["a"]
                f = p["ini"] + min(w["f"], p["b"]) - p["a"]
                novas.append({"i": round(i, 3), "f": round(max(f, i + 0.08), 3), "p": txt})
    leg_ev, srt = [], []
    for b in blocos(novas, 4, max_dur=1.8):
        if b["i"] < gancho_fim - 0.05:
            continue
        partes = []
        for w in b["palavras"]:
            nucleo = w["p"].strip(".,!?…").lower()
            partes.append(rf"{{\i1}}{w['p']}{{\i0}}" if nucleo in dest else w["p"])
        linha = " ".join(partes).replace(" -", "-").replace(" %", "%")
        limpo = " ".join(w["p"] for w in b["palavras"]).replace(" -", "-")
        leg_ev += [rf"Dialogue: 0,{ts(b['i'])},{ts(b['f'])},T,,0,0,0,,{{\an2\pos(542,{LEG['y'] + 3})\blur3"
                   rf"\1c&H000000&\1a&HA0&\fn{LEG['fonte']}\fs{LEG['tam']}}}{linha}",
                   rf"Dialogue: 1,{ts(b['i'])},{ts(b['f'])},T,,0,0,0,,{{\an2\pos(540,{LEG['y']})"
                   rf"\fn{LEG['fonte']}\fs{LEG['tam']}}}{linha}"]
        srt.append(f"{len(srt) + 1}\n{srt_ts(b['i'])} --> {srt_ts(b['f'])}\n{limpo}\n")
    open(os.path.join(kit, "legenda.srt"), "w").write("\n".join(srt))
    ass_final = os.path.join(saida, "final.ass")
    open(ass_final, "w").write(cab + "\n".join(gancho_ev + rotulos_ev + cta_ev + leg_ev) + "\n")
    ass_gancho = os.path.join(kit, "gancho.ass")
    open(ass_gancho, "w").write(cab + "\n".join(gancho_ev) + "\n")

    # PNGs dos rótulos e do CTA (quadro cheio, transparente, já na posição)
    for nome, ev, de, ate, _ in pngs:
        meio = (de + ate) / 2
        tmp = os.path.join(kit, "textos", nome + ".ass")
        open(tmp, "w").write(cab + "\n".join(e.replace(ts(de), "0:00:00.00").replace(ts(ate), "0:00:05.00")
                                              for e in ev) + "\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black@0.0:s=1080x1920:d=2,format=rgba",
                        "-vf", f"ass={tmp}:fontsdir={FONTES_DIR}:alpha=1", "-ss", "1", "-frames:v", "1",
                        os.path.join(kit, "textos", nome + ".png")], check=True)
        os.remove(tmp)

    # ---------- 5. render final e base do CapCut ----------
    def render(destino, ass, com_stickers_itens):
        st_dir = seq
        if not com_stickers_itens:  # base do CapCut: só os stickers da abertura
            st_dir = os.path.join(kit, "stickers_seq_abertura")
            shutil.rmtree(st_dir, ignore_errors=True)
            os.makedirs(st_dir)
            for q in range(n):
                src = os.path.join(seq, f"st_{q + 1:04d}.png")
                if q * PASSO < gancho_fim:
                    shutil.copy(src, os.path.join(st_dir, f"st_{q + 1:04d}.png"))
                else:
                    Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(os.path.join(st_dir, f"st_{q + 1:04d}.png"))
        fc = (f"[1:v]fps={FPS},format=rgba[s];[2:v]format=rgba[g];[0:v][g]overlay=0:0:eof_action=pass[vg];"
              f"[vg][s]overlay=0:0:eof_action=pass[vs];[vs]ass={ass}:fontsdir={FONTES_DIR}[vo];"
              f"[3:a]aresample=48000,volume=-16dB[fx];[0:a][fx]amix=inputs=2:duration=first:normalize=0[ao]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-framerate", str(int(1 / PASSO)), "-i",
                        os.path.join(st_dir, "st_%04d.png"), "-framerate", str(FPS), "-i",
                        os.path.join(glit, "glitter_%04d.png"), "-i", sfx, "-filter_complex", fc, "-map", "[vo]",
                        "-map", "[ao]", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", destino],
                       check=True)

    render(os.path.join(saida, "final.mp4"), ass_final, True)
    render(os.path.join(kit, "base_capcut.mp4"), ass_gancho, False)

    # ---------- 6. roteiro ----------
    r = ["# Roteiro para o CapCut (Mac)", "",
         f"Duração: {dur:.1f} s. Arquivos nesta pasta. Tempos no vídeo `base_capcut.mp4`.", "",
         "## Já está no `base_capcut.mp4`",
         f"- Cortes (só fala), zoom vai e volta em {len(zooms)} momentos e voz em -14 LUFS.",
         f"- Abertura (0 a {gancho_fim:.1f} s): título \"Achadinhos / de Natal\" animado, glitter, 4 stickers girando "
         "e efeito sonoro (`sfx_brilho.wav`).", "",
         "## Para colocar no CapCut",
         "1. **Legenda:** Texto > Legendas > Importar legenda > `legenda.srt`. Fonte Montserrat SemiBold, branca, "
         "sombra leve, embaixo (acima da legenda do Reels).",
         "2. **Rótulos, CTA e stickers das peças:** arraste cada PNG para uma faixa de sobreposição e ajuste o tempo "
         "abaixo. Os PNGs de texto já estão no tamanho e na posição do quadro (1080x1920).", "",
         "| De | Até | O quê | Arquivo |", "|---:|---:|---|---|"]
    for nome, _, de, ate, txt in pngs:
        r.append(f"| {de:.1f} s | {ate:.1f} s | {txt} | `textos/{nome}.png` |")
    for de, ate, nome, *_ in itens:
        if de >= gancho_fim - 0.01:
            r.append(f"| {de:.1f} s | {ate:.1f} s | sticker (girando de leve a cada 0,5 s) | `stickers/{nome}.png` |")
    r += ["", "Os stickers das peças entram em cima do rótulo, no centro. O do CTA, à direita do QUERO.",
          "Para o efeito de girar no CapCut: Animação > Loop > \"Balançar\" (ou keyframes de rotação de ±6° a cada 0,5 s)."]
    open(os.path.join(kit, "roteiro.md"), "w").write("\n".join(r) + "\n")
    json.dump({"duracao_s": dur, "gancho_fim": gancho_fim, "pedacos": pcs, "zooms": zooms},
              open(os.path.join(saida, "montagem.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{len(pcs)} pedaços, {dur:.1f} s; gancho até {gancho_fim:.2f} s; {len(zooms)} zooms")


if __name__ == "__main__":
    main(sys.argv[1])
