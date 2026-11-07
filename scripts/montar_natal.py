"""Monta um Reel de Natal/achadinhos a partir de mais de um arquivo bruto (só trechos falados).

Uso: python3 scripts/montar_natal.py projetos/<nome> [--reusar-base] [--kit]
  --reusar-base  não refaz os cortes (usa saida/base_cortes.mp4)
  --kit          também gera capcut/base_capcut.mp4 (a Fran não usa; padrão é só o final.mp4)
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
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from legenda_blocos import blocos  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
FONTES_DIR = os.path.expanduser("~/.fonts")
LEG = {"fonte": "Montserrat SemiBold", "tam": 74, "y": 1180}
ROTULO = {"y": 360, "tam": 80, "cor": "#EE8E9C", "dur": 2.6}
STICKER_ITEM = {"x": 540, "y": 215, "lado": 150, "dur": 2.6}
PASSO = 0.5  # stickers mexem (só rotação) a cada meio segundo
VELOCIDADE = 1.2  # Fran (07/11): "sempre colocar 1.2"
ATRASO = 0.25  # a transcrição sai adiantada ~0,25 s em relação à voz real (medido com o VAD em 03/11)


def bgr(h):
    h = h.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t // 60) % 60:02d}:{t % 60:05.2f}"


def srt_ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def carregar_audio(arq):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def vad(projeto, fonte, audio):
    """Trechos de voz (Silero, via faster-whisper). Respiro e silêncio ficam de fora. Cache em vad_<fonte>.json."""
    cache = os.path.join(projeto, f"vad_{fonte}.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    ts_ = get_speech_timestamps(audio, VadOptions(threshold=0.5, min_silence_duration_ms=120, speech_pad_ms=30,
                                                  min_speech_duration_ms=120))
    reg = [(round(t["start"] / 16000, 3), round(t["end"] / 16000, 3)) for t in ts_]
    json.dump(reg, open(cache, "w"))
    return reg


def vale(audio, t0, t1):
    """Instante mais silencioso (janela de 20 ms) entre t0 e t1: onde cortar entre duas falas coladas."""
    if t1 <= t0:
        return t0
    q = 160  # 10 ms
    a, b = int(t0 * 16000), int(t1 * 16000)
    seg = audio[a:b]
    if len(seg) < 2 * q:
        return (t0 + t1) / 2
    e = np.array([np.sqrt((seg[k:k + 2 * q] ** 2).mean()) for k in range(0, len(seg) - 2 * q, q)])
    return (a + int(e.argmin()) * q + q) / 16000


def pedacos(plano, palavras, projeto):
    """Cada trecho vira pedaços só com voz.

    Os tempos da transcrição (faster-whisper) saem adiantados: o começo da fala vem ~0,3 s antes do real
    e o fim ~0,15 s antes. Por isso as bordas e as pausas vêm do detector de voz (VAD), e a transcrição
    só diz quais falas entram. Entre uma fala que fica e outra que sai, coladas, o corte vai no vale de
    energia. Respiros e silêncios maiores que 0,12 s entre as falas saem.
    """
    PAD_INI, PAD_FIM, GAP = 0.10, 0.07, 0.12
    audios = {f: carregar_audio(os.path.join(projeto, plano["fontes"][f][0])) for f in plano["fontes"]}
    regs = {f: vad(projeto, f, audios[f]) for f in plano["fontes"]}
    out = []
    for k, tr in enumerate(plano["trechos"]):
        f, W = tr["fonte"], palavras[tr["fonte"]]
        idx = [j for j, w in enumerate(W) if tr["de"] - 0.05 <= w["i"] < tr["ate"]]
        if not idx:
            continue
        w0, w1 = W[idx[0]], W[idx[-1]]
        ant = W[idx[0] - 1] if idx[0] > 0 else None
        prox = W[idx[-1] + 1] if idx[-1] + 1 < len(W) else None
        # limites: não invadir a fala de fora que vem antes/depois
        lo = w0["i"] - 0.15
        if ant and w0["i"] - ant["f"] < 0.6:
            lo = vale(audios[f], ant["f"] + 0.05, w0["i"] + 0.3)
        hi = w1["f"] + 0.6
        if prox and prox["i"] - w1["f"] < 0.9:
            hi = vale(audios[f], w1["f"], prox["i"] + 0.2)
        rs = [[a, b] for a, b in regs[f] if b > lo and a < hi]
        # fala baixa: se o VAD começa bem depois do que a transcrição indica, volta pelo volume (> -55 dB)
        if rs and rs[0][0] - (w0["i"] + ATRASO) > 0.3:
            t = rs[0][0]
            while t - 0.02 > max(lo, rs[0][0] - 1.0):
                q = audios[f][int((t - 0.02) * 16000):int(t * 16000)]
                if 20 * np.log10(np.sqrt((q ** 2).mean()) + 1e-9) < -55:
                    break
                t -= 0.02
            rs[0][0] = t
        vozes = [(max(a - PAD_INI, lo), min(b + PAD_FIM, hi)) for a, b in rs]
        vozes = [(a, b) for a, b in vozes if b - a > 0.08]
        # junta vozes separadas por menos de GAP; o resto (respiro, silêncio) sai
        junt = []
        for a, b in vozes:
            if junt and a - junt[-1][1] < GAP:
                junt[-1] = (junt[-1][0], b)
            else:
                junt.append((a, b))
        for a, b in junt:
            out.append({"tr": k, "fonte": f, "a": round(a, 3), "b": round(b, 3)})
    t = 0.0
    for p in out:
        p["vel"] = plano.get("velocidade", VELOCIDADE)
        p["ini"], t = t, t + (p["b"] - p["a"]) / p["vel"]
        p["fim"] = t
    return out


def mapa(pcs, fonte, t, tr=None):
    for p in pcs:
        if p["fonte"] == fonte and p["a"] <= t < p["b"] and (tr is None or p["tr"] == tr):
            return p["ini"] + (t - p["a"]) / p.get("vel", 1.0)
    return None


def janela_trecho(pcs, k):
    ps = [p for p in pcs if p["tr"] == k]
    return (ps[0]["ini"], ps[-1]["fim"]) if ps else None


def main(projeto):
    plano = json.load(open(os.path.join(projeto, "plano.json")))
    fontes = list(plano["fontes"])
    palavras = {f: json.load(open(os.path.join(projeto, plano["fontes"][f][1])))["palavras"] for f in fontes}
    pcs = pedacos(plano, palavras, projeto)
    dur = round(pcs[-1]["fim"], 3)
    saida = os.path.join(projeto, "saida")
    kit = os.path.join(saida, "capcut")
    for d in (saida, kit, os.path.join(kit, "textos"), os.path.join(kit, "stickers")):
        os.makedirs(d, exist_ok=True)
    gancho_fim = max(janela_trecho(pcs, k)[1] for k in plano["gancho"]["trechos"])
    if "dur" in plano["gancho"]:  # gancho escrito só nos primeiros segundos (provador)
        gancho_fim = min(gancho_fim, plano["gancho"]["dur"])
    LEG["tam"] = plano.get("legenda_tam", LEG["tam"])
    efeitos = plano.get("efeitos_abertura", True)  # glitter + sininhos: só nos vídeos de Natal

    # ---------- 1. cortes + zoom vai e volta ----------
    reusar = "--reusar-base" in sys.argv and os.path.exists(os.path.join(saida, "base_cortes.mp4"))
    # Cada pedaço vira um arquivo (busca rápida, recodifica em 1080x1920/30 fps), depois junta com concat.
    tmpd = os.path.join(saida, "pedacos_tmp")
    shutil.rmtree(tmpd, ignore_errors=True)
    os.makedirs(tmpd)
    lista = []
    for j, p in enumerate([] if reusar else pcs):
        arq = os.path.join(tmpd, f"p{j:03d}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{p['a']:.3f}", "-t", f"{p['b'] - p['a']:.3f}", "-i",
                        os.path.join(projeto, plano["fontes"][p["fonte"]][0]),
                        "-vf", f"setpts=PTS/{p['vel']},fps={FPS},scale=1080:1920:force_original_aspect_ratio=increase,"
                               "crop=1080:1920,setsar=1",
                        "-af", f"atempo={p['vel']},aresample=48000", "-ac", "2", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
                        "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", arq.replace(".mp4", ".mov")], check=True)
        lista.append(f"file '{os.path.basename(arq).replace('.mp4', '.mov')}'")
    open(os.path.join(tmpd, "lista.txt"), "w").write("\n".join(lista) + "\n")
    fil = []
    zooms = []
    for k, tr in enumerate(plano["trechos"]):
        jan = janela_trecho(pcs, k)
        if not jan:
            continue
        for z0, z1 in tr.get("zooms", [tr["zoom"]] if "zoom" in tr else []):
            ps = [p for p in pcs if p["tr"] == k]
            a = mapa(pcs, tr["fonte"], z0 + ATRASO, k)
            if a is None:  # caiu num corte: começa no próximo pedaço
                prox = [p["ini"] for p in ps if p["a"] >= z0 + ATRASO]
                a = prox[0] if prox else None
            b = mapa(pcs, tr["fonte"], z1 + ATRASO - 0.01, k)
            if b is None:  # caiu num corte: termina no pedaço anterior
                ant = [p["fim"] for p in ps if p["b"] <= z1 + ATRASO]
                b = ant[-1] if ant else None
            if a is not None and b is not None and b - a >= 0.8:
                zooms.append((round(a, 3), round(b, 3)))
    zooms.sort()
    sem_sobrepor = []
    for a, b in zooms:  # zoom leve: janelas nunca se somam
        if sem_sobrepor and a < sem_sobrepor[-1][1]:
            a = sem_sobrepor[-1][1]
        if b - a >= 0.8:
            sem_sobrepor.append((a, b))
    zooms = sem_sobrepor
    if zooms:
        curva = "+".join(f"between(in/{FPS},{a},{b})*sin(PI*(in/{FPS}-{a})/{b - a})" for a, b in zooms)
        fil.append(f"[vc]scale=2160:3840:flags=lanczos,zoompan=z='1+{plano.get("zoom_max", 0.18)}*({curva})':d=1:"
                   f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=1080x1920:fps={FPS}[vz]")
    else:
        fil.append("[vc]null[vz]")
    fil.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[az]")
    fil.insert(0, "[0:v]null[vc];[0:a]anull[ac]")
    base = os.path.join(saida, "base_cortes.mp4")
    if not reusar:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                        os.path.join(tmpd, "lista.txt"), "-filter_complex", ";".join(fil), "-map", "[vz]",
                        "-map", "[az]", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", base], check=True)
    shutil.rmtree(tmpd)

    # ---------- 2. stickers (abertura + peças), um quadro a cada 0,5 s, só girando ----------
    rnd = random.Random(11)
    usar_stickers = plano.get("stickers", True)  # Fran (03/11, Farm): tirou todos os stickers
    layout = json.load(open(os.path.join(projeto, "layout_intro.json"))) if usar_stickers else []
    imgs = {os.path.basename(a)[:-4]: Image.open(a).convert("RGBA")
            for a in glob.glob(os.path.join(projeto, "stickers", "*.png"))}
    for nome in imgs:
        shutil.copy(os.path.join(projeto, "stickers", nome + ".png"), os.path.join(kit, "stickers"))
    itens = []  # (de, ate, sticker, x, y, lado, giro_base)
    for s in (layout if usar_stickers else []):
        itens.append((0.0, gancho_fim, s["sticker"], s["x"], s["y"], s["lado"], s.get("giro", 0)))
    ctas = []
    for k, tr in enumerate(plano["trechos"]):
        jan = janela_trecho(pcs, k)
        if not jan:
            continue
        if "cta" in tr:
            c0 = mapa(pcs, tr["fonte"], tr["cta"]["de"] + ATRASO, k) or jan[0]
            ctas.append((c0, jan[1], tr["cta"]["texto"]))
            if "sticker" in tr and usar_stickers:
                itens.append((c0, jan[1], tr["sticker"], 880, 500, 170, 8))
        elif "sticker" in tr and usar_stickers:
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
    subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "glitter.py"), glit, f"{gancho_fim:.2f}", "30",
                    "80" if efeitos else "0"],
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
    g = plano["gancho"]
    if g.get("estilo") == "luxo":
        # Reels de provador: Playfair branco, sobretítulo em caixa alta espaçada + título (*itálico*), sombra leve
        tit = re.sub(r"\*(.+?)\*", r"{\\i1}\1{\\i0}", g["titulo"])
        corpo = (rf"{{\fnPlayfair Display SemiBold\fs44\fsp6}}{g['sup']}\N{{\fs14}} \N"
                 rf"{{\fnPlayfair Display\fs{g.get('tam', 104)}\fsp0}}{tit}")
        y = g.get("y", 1250)
        gancho_ev = [rf"Dialogue: 0,{ts(0)},{ts(gancho_fim)},T,,0,0,0,,{{\an2\pos(542,{y + 4})\blur4\1c&H000000&"
                     rf"\1a&H70&\fad(250,200)}}{corpo}",
                     rf"Dialogue: 1,{ts(0)},{ts(gancho_fim)},T,,0,0,0,,{{\an2\pos(540,{y})\fad(250,200)}}{corpo}"]
    else:
        ys = [850, 1055]
        for j, (txt, cor, tam, ital) in enumerate(g["linhas"]):
            gancho_ev += pastel(0, gancho_fim, txt, cor, tam, 540, ys[j], ital, ini_ms=250 * j)
    classico = plano.get("estilo_textos") == "classico"
    ROTULO["y"] = plano.get("rotulo_y", ROTULO["y"])
    cta_y = plano.get("cta_y", 480)

    def classico_ev(de, ate, txt, y):
        """Rótulo clássico (Fran, 03/11): Playfair SemiBold em caixa alta espaçada, branco, sombra curta e leve."""
        f = r"\fnPlayfair Display SemiBold\fs56\fsp6\fad(250,200)"
        return [rf"Dialogue: 0,{ts(de)},{ts(ate)},T,,0,0,0,,{{\an5\pos(542,{y + 4})\blur4\1c&H000000&\1a&H70&{f}}}"
                rf"{txt.upper()}",
                rf"Dialogue: 1,{ts(de)},{ts(ate)},T,,0,0,0,,{{\an5\pos(540,{y}){f}}}{txt.upper()}"]

    rotulos_ev, pngs = [], []
    for k, tr in enumerate(plano["trechos"]):
        jan = janela_trecho(pcs, k)
        if jan and "rotulo" in tr:
            fim = min(jan[0] + ROTULO["dur"], dur)
            ev = (classico_ev(jan[0], fim, tr["rotulo"], ROTULO["y"]) if classico else
                  pastel(jan[0], fim, tr["rotulo"], ROTULO["cor"], ROTULO["tam"], 540, ROTULO["y"], False))
            rotulos_ev += ev
            pngs.append((f"rotulo_{len(pngs) + 1:02d}", ev, jan[0], fim, tr["rotulo"]))
    cta_ev = []
    for c0, c1, txt in ctas:
        partes = txt.split()
        resto = " ".join(p for p in partes if p != "QUERO")
        if classico:
            # Igual ao 1º Reel (laise, 02/11), pedido da Fran em 07/11: "Comenta" Montserrat Medium 50 +
            # "QUERO" Montserrat ExtraBold 84, numa linha, logo acima da legenda, branco, sombra leve, sem animação.
            corpo = rf"{{\fnMontserrat Medium\fs50}}{resto} {{\fnMontserrat ExtraBold\fs84}}QUERO"
            yq = LEG["y"] - LEG["tam"] - 25
            ev = [rf"Dialogue: 0,{ts(c0)},{ts(c1)},T,,0,0,0,,{{\an2\pos(542,{yq + 3})\blur3\1c&H000000&\1a&HA0&"
                  rf"\fad(200,150)}}{corpo}",
                  rf"Dialogue: 1,{ts(c0)},{ts(c1)},T,,0,0,0,,{{\an2\pos(540,{yq})\fad(200,150)}}{corpo}"]
        else:
            corpo = (rf"{{\fnMontserrat Medium\fs60}}{resto}\N"
                     rf"{{\fnMontserrat ExtraBold\fs130\bord5\3c&HFFFFFF&\1c{bgr('#EE8E9C')}}}QUERO")
            sombra = r"\blur5\1c&H000000&\1a&HB0&\bord6\3c&H000000&\3a&HB0&"
            ev = [rf"Dialogue: 0,{ts(c0)},{ts(c1)},T,,0,0,0,,{{\an5\pos(544,{cta_y + 6}){sombra}{pop(0)}}}{corpo}",
                  rf"Dialogue: 1,{ts(c0)},{ts(c1)},T,,0,0,0,,{{\an5\pos(540,{cta_y}){pop(0)}}}{corpo}"]
        cta_ev += ev
        pngs.append(("cta_comenta_quero", ev, c0, c1, txt))

    # legenda: palavras remapeadas, corrigidas; some enquanto o gancho está na tela
    corr = {k.lower(): v for k, v in plano.get("correcoes", {}).items()}
    dest = {d.lower() for d in plano.get("destaques", [])}
    novas = []
    for p in pcs:
        for w in palavras[p["fonte"]]:
            wi, wf = w["i"] + ATRASO, w["f"] + ATRASO
            if p["a"] - 0.05 <= wi < p["b"]:
                txt = w["p"]
                nucleo = txt.strip(".,!?…").lower()
                if nucleo in corr:
                    novo = txt.lower().replace(nucleo, corr[nucleo])
                    if not novo.strip(".,!?…"):  # correção vazia: a palavra sai da legenda
                        continue
                    txt = novo[0].upper() + novo[1:] if txt[:1].isupper() else novo
                i = p["ini"] + max(wi - p["a"], 0) / p["vel"]
                f = p["ini"] + (min(wf, p["b"]) - p["a"]) / p["vel"]
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
              f"[3:a]aresample=48000,volume={'-16dB' if efeitos else '0'}[fx];[0:a][fx]amix=inputs=2:duration=first:normalize=0[ao]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-framerate", str(int(1 / PASSO)), "-i",
                        os.path.join(st_dir, "st_%04d.png"), "-framerate", str(FPS), "-i",
                        os.path.join(glit, "glitter_%04d.png"), "-i", sfx, "-filter_complex", fc, "-map", "[vo]",
                        "-map", "[ao]", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", destino],
                       check=True)

    render(os.path.join(saida, "final.mp4"), ass_final, True)
    if "--kit" in sys.argv:  # a Fran não usa kit do CapCut (03/11); só com --kit
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
