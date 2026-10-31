"""Agrupa as palavras em blocos curtos de legenda (usado pelas duas versões)."""


def blocos(palavras, max_palavras=3, max_dur=1.6, pausa=0.45):
    out, atual = [], []
    for k, w in enumerate(palavras):
        atual.append(w)
        prox = palavras[k + 1] if k + 1 < len(palavras) else None
        fecha = (len(atual) >= max_palavras or w["p"][-1:] in ".,!?…" or prox is None
                 or prox["i"] - w["f"] > pausa or prox["f"] - atual[0]["i"] > max_dur)
        if fecha:
            fim = w["f"] if prox is None or prox["i"] - w["f"] > 0.3 else prox["i"]
            out.append({"i": atual[0]["i"], "f": round(fim, 3), "palavras": atual})
            atual = []
    return out
