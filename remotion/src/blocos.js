// Mesma regra de scripts/legenda_blocos.py (as duas versões cortam a legenda igual).
export const blocos = (palavras, maxPalavras = 3, maxDur = 1.6, pausa = 0.45) => {
  const out = [];
  let atual = [];
  palavras.forEach((w, k) => {
    atual.push(w);
    const prox = palavras[k + 1];
    const fecha = atual.length >= maxPalavras || /[.,!?…]$/.test(w.p) || !prox ||
      prox.i - w.f > pausa || prox.f - atual[0].i > maxDur;
    if (fecha) {
      const fim = !prox || prox.i - w.f > 0.3 ? w.f : prox.i;
      out.push({i: atual[0].i, f: fim, palavras: atual});
      atual = [];
    }
  });
  return out;
};
