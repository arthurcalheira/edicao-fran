"""Efeito sonoro de brilho natalino (gerado aqui, sem licença de terceiros).

Uso: python3 scripts/sfx_brilho.py <saida.wav> [duracao_s]
Arpejo rápido de sininhos subindo (tons de sino com harmônicos inarmônicos e decaimento),
mais um "shimmer" agudo de guizos que se apaga. Mono, 48 kHz, pico em -3 dBFS.
No vídeo, mixar uns 18 dB abaixo da voz.
"""
import sys
import wave

import numpy as np

SR = 48000


def sino(freq, dur, amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    parciais = [(1.0, 1.0), (2.76, 0.45), (5.40, 0.25), (8.93, 0.12)]  # sino: parciais inarmônicos
    s = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t * (3 + 2.5 * m)) for m, a in parciais)
    ataque = np.minimum(1, t / 0.004)
    return amp * s * ataque


def main(saida, dur=1.6):
    n = int(dur * SR)
    out = np.zeros(n)
    notas = [1046.5, 1318.5, 1568.0, 2093.0, 2637.0, 3136.0]  # C6 E6 G6 C7 E7 G7
    for k, f in enumerate(notas):
        ini = int(k * 0.055 * SR)
        s = sino(f, dur - k * 0.055, amp=0.9 - k * 0.08)
        out[ini:ini + len(s)] += s[: n - ini]
    rnd = np.random.default_rng(5)
    t = np.arange(n) / SR
    guizo = np.zeros(n)
    for _ in range(40):  # guizos: estalinhos agudos aleatórios que somem
        ini = int(rnd.uniform(0.05, dur * 0.7) * SR)
        f = rnd.uniform(4500, 7500)
        ln = int(0.06 * SR)
        tt = np.arange(ln) / SR
        g = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 70) * rnd.uniform(0.1, 0.3)
        guizo[ini:ini + ln] += g[: n - ini]
    out += guizo * np.exp(-t * 1.5)
    out *= np.minimum(1, (dur - t) / 0.25)  # fade-out
    out = out / np.abs(out).max() * 10 ** (-3 / 20)
    with wave.open(saida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    print("ok:", saida)


if __name__ == "__main__":
    main(sys.argv[1], *[float(x) for x in sys.argv[2:]])
