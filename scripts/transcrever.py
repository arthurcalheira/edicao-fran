"""Transcreve o bruto com o tempo de início e fim de cada palavra (faster-whisper, CPU).

Uso: python3 scripts/transcrever.py projetos/<nome>
Lê <projeto>/bruto.* e grava <projeto>/transcricao.json.
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

# Vocabulário do perfil: reduz troca de marca e de termo de modelagem.
VOCABULARIO = ("Renner, C&A, Riachuelo, Farm, Shein, Zara. Comenta QUERO. Laise, viscose, tricoline, "
               "acinturado, wide leg, pantalona, balonê, alfaiataria, cropped, modelagem, caimento.")


def main(projeto, modelo="large-v3-turbo"):
    bruto = sorted(glob.glob(os.path.join(projeto, "bruto.*")))[0]
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", bruto, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32)
    m = WhisperModel(modelo, device="cpu", compute_type="int8", cpu_threads=os.cpu_count())
    segs, _ = m.transcribe(audio, language="pt", word_timestamps=True, vad_filter=True,
                           initial_prompt=VOCABULARIO, condition_on_previous_text=False)
    palavras = [{"i": round(w.start, 2), "f": round(w.end, 2), "p": w.word.strip()}
                for s in segs for w in s.words if w.word.strip()]
    saida = {"fonte": os.path.basename(bruto), "duracao_s": round(len(audio) / 16000, 2), "palavras": palavras,
             "texto": " ".join(w["p"] for w in palavras)}
    json.dump(saida, open(os.path.join(projeto, "transcricao.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{len(palavras)} palavras, {saida['duracao_s']} s")


if __name__ == "__main__":
    main(sys.argv[1], *sys.argv[2:])
