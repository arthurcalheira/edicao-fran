# edicao-fran

Edição dos Reels da @fran.calheira com o Claude, seguindo as regras do repositório `analise-conteudos`.

## Como funciona

```
bruto (Drive) ─► transcrever.py ─► transcricao.json ─┐
                                plano.json (cortes) ─┴► cortar.py ─► saida/cortado.mp4 + cortado.json + cortes.edl
                                                                        │
                                       ┌────────────────────────────────┴───────────────────────┐
                              A: render_ffmpeg.py                                   B: render_remotion.sh
                              saida/final_ffmpeg.mp4                                saida/final_remotion.mp4
```

### Etapa comum: `cortar.py`
- Corta e acelera os trechos.
- Tira pausas maiores que o limite.
- Enquadra em 1080×1920 a 30 fps.
- Leva a voz a −14 LUFS.
- Corrige palavras da transcrição.
- Gera o `cortes.edl`, que abre no Premiere ou no DaVinci para ajustar os cortes à mão.

### Duas versões do visual (teste)

As duas leem o mesmo `cortado.json` e usam o mesmo `estilo.json`.

| | A: ffmpeg + libass | B: Remotion (React) |
|---|---|---|
| Render de um Reel de 55 s (4 CPUs) | ~40 s | ~6 min |
| Legenda | blocos de 3 palavras; palavra-chave em amarelo; palavra falada um pouco maior | igual, com animação de mola na palavra falada e entrada do bloco |
| Gancho e textos | caixa branca reta | cartão arredondado com sombra e entrada animada |
| Emoji | **não aparece** (o libass não desenha emoji colorido) | colorido |
| Zoom | seco (punch-in) | rampa curta de 4 quadros |
| Licença | livre | grátis para pessoa física ou empresa com até 3 funcionários |

## Uso
```
python3 scripts/transcrever.py projetos/<nome>      # precisa de projetos/<nome>/bruto.mp4
# escrever projetos/<nome>/plano.json (trechos, textos, zooms, destaques, correções)
python3 scripts/cortar.py projetos/<nome>
python3 scripts/render_ffmpeg.py projetos/<nome>    # versão A
scripts/render_remotion.sh projetos/<nome>          # versão B
```

**Requisitos:**
- ffmpeg com libass;
- `pip install faster-whisper`;
- Node 18+ e Chromium (no ambiente na nuvem, `/opt/pw-browsers`).

## Projetos
- `projetos/2026-10-23_riachuelo_floral_laise/`: o plano segue o ajuste corrigido de 23/10 (introdução acelerada para 1,3x e 4 cortes de elogio, de 71 s para cerca de 55 s).
  - Foi testado com um vídeo sintético que mostra o tempo do bruto na tela, para conferir os cortes.
  - **Falta o bruto real.**

- `projetos/2026-11-02_cea_laise_vermelho_branco/`: conjunto de laise da C&A (camisa + short) em vermelho e branco. 98,5 s → 42 s, renderizado na versão luxo.

### Versão luxo (`render_luxo.py`, pedida pela Fran em 02/11)
- Fonte serifada (Playfair Display), só branco com sombra preta suave, sem cor e sem animação na legenda.
- Palavra-chave em itálico; nos textos do plano, `*assim*` vira itálico e o gancho usa `SOBRETÍTULO | título`.
- Gancho e texto final escondem a legenda enquanto estão na tela.
- Estilo em `estilo_luxo.json`.
- **Fontes:** `npm i @fontsource/playfair-display` e converter os `.woff2` para `.ttf` em `~/.fonts` (fontTools).
- `python3 scripts/render_luxo.py projetos/<nome>` (depois do `cortar.py`).

Pesquisa de ferramentas e técnicas: `pesquisa/2026-10-31_ferramentas_e_tecnicas.md`.
