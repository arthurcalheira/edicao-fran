"""Etapa comum às duas versões: corta, acelera, tira pausas e padroniza o volume.

Uso: python3 scripts/cortar.py projetos/<nome>
Lê plano.json e transcricao.json. Grava em <projeto>/saida/:
  - cortado.mp4   vídeo cortado, 1080x1920, 30 fps, voz em -14 LUFS (sem textos)
  - cortado.json  palavras, textos e zooms já no tempo do vídeo cortado (entrada dos dois renderizadores)
  - cortes.edl    lista de cortes CMX3600 para abrir no Premiere/DaVinci e ajustar à mão
"""
import glob
import json
import os
import subprocess
import sys

FPS = 30


def pedacos(plano, palavras):
    """Divide cada trecho do plano em pedaços com fala, tirando as pausas longas entre palavras."""
    limite = plano.get("cortar_pausas_acima_s")
    folga = 0.12  # respiro antes e depois da palavra, para não cortar consoante
    saida = []
    for tr in plano["trechos"]:
        a, b, vel = tr["de"], tr["ate"], tr.get("vel", 1.0)
        dentro = [w for w in palavras if w["i"] >= a - 0.05 and w["i"] < b]
        if not limite or not dentro:
            saida.append((a, b, vel))
            continue
        ini = a
        for w0, w1 in zip(dentro, dentro[1:]):
            if w1["i"] - w0["f"] > limite:
                saida.append((ini, min(w0["f"] + folga, b), vel))
                ini = max(w1["i"] - folga, a)
        saida.append((ini, b, vel))
    return [p for p in saida if p[1] - p[0] > 0.1]


def remapear(t, pcs):
    """Tempo do bruto -> tempo do vídeo cortado. None se o instante foi cortado."""
    acc = 0.0
    for a, b, vel in pcs:
        if a <= t < b:
            return round(acc + (t - a) / vel, 3)
        acc += (b - a) / vel
    return None


def intervalo(de, ate, pcs):
    """Remapeia um intervalo; se o começo caiu num corte, começa no próximo trecho mantido."""
    ini = remapear(de, pcs)
    if ini is None:
        prox = [a for a, _, _ in pcs if a >= de]
        ini = remapear(prox[0], pcs) if prox else None
    fim = remapear(ate, pcs)
    if fim is None:
        antes = [(a, b) for a, b, _ in pcs if b <= ate]
        fim = remapear(antes[-1][1] - 0.001, pcs) if antes else None
    return (ini, fim) if ini is not None and fim is not None and fim > ini else None


def tc(seg):
    f = int(round(seg * FPS))
    return f"{f // (3600 * FPS):02d}:{f // (60 * FPS) % 60:02d}:{f // FPS % 60:02d}:{f % FPS:02d}"


def edl(pcs, nome):
    linhas = ["TITLE: " + nome, "FCM: NON-DROP FRAME", ""]
    rec = 0.0
    for n, (a, b, vel) in enumerate(pcs, 1):
        dur = (b - a) / vel
        linhas.append(f"{n:03d}  BRUTO    AA/V  C        {tc(a)} {tc(b)} {tc(rec)} {tc(rec + dur)}")
        if vel != 1.0:
            linhas.append(f"M2   BRUTO    {vel * FPS:05.1f}                {tc(a)}")
        rec += dur
    return "\n".join(linhas) + "\n"


def main(projeto):
    plano = json.load(open(os.path.join(projeto, "plano.json")))
    trans = json.load(open(os.path.join(projeto, "transcricao.json")))
    bruto = sorted(glob.glob(os.path.join(projeto, "bruto.*")))[0]
    corr = plano.get("correcoes", {})
    palavras = trans["palavras"]
    pcs = pedacos(plano, palavras)
    os.makedirs(os.path.join(projeto, "saida"), exist_ok=True)

    # Vídeo: enquadra em 1080x1920, corta cada pedaço, acelera e junta. Áudio: atempo e loudnorm.
    filtros, rot = [], []
    for k, (a, b, vel) in enumerate(pcs):
        filtros.append(f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/{vel},"
                       f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS}[v{k}]")
        filtros.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,atempo={vel}[a{k}]")
        rot.append(f"[v{k}][a{k}]")
    filtros.append("".join(rot) + f"concat=n={len(pcs)}:v=1:a=1[v][a0]")
    filtros.append("[a0]loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[a]")
    destino = os.path.join(projeto, "saida", "cortado.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", bruto, "-filter_complex", ";".join(filtros),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", destino], check=True)

    dur = round(sum((b - a) / v for a, b, v in pcs), 3)
    novas = []
    for w in palavras:
        i = remapear(w["i"], pcs)
        if i is None:
            continue
        f = remapear(min(w["f"], w["i"] + 1.5) - 0.001, pcs) or i + 0.25
        p = w["p"]
        nucleo = p.strip(".,!?…").lower()
        if nucleo in corr:
            p = p.lower().replace(nucleo, corr[nucleo])
            p = p[0].upper() + p[1:] if w["p"][:1].isupper() else p
        novas.append({"i": i, "f": max(f, i + 0.08), "p": p})
    textos = []
    for t in plano.get("textos", []):
        ate = pcs[-1][1] - 0.001 if t["ate"] == "fim" else t["ate"]
        iv = intervalo(t["de"], ate, pcs)
        if iv:
            textos.append({**t, "de": iv[0], "ate": dur if t["ate"] == "fim" else iv[1]})
    zooms = []
    for z in plano.get("zooms", []):
        iv = intervalo(z["de"], z["ate"], pcs)
        if iv:
            zooms.append({**z, "de": iv[0], "ate": iv[1]})
    out = {"duracao_s": dur, "fps": FPS, "palavras": novas, "textos": textos, "zooms": zooms,
           "destaques": plano.get("destaques", []), "pedacos_bruto": [list(p) for p in pcs]}
    json.dump(out, open(os.path.join(projeto, "saida", "cortado.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(projeto, "saida", "cortes.edl"), "w").write(edl(pcs, os.path.basename(projeto.rstrip("/"))))
    print(f"{len(pcs)} pedaços, {trans['duracao_s']} s -> {dur} s")


if __name__ == "__main__":
    main(sys.argv[1])
