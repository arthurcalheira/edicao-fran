# Regras de edição dos Reels da Fran

**Ler antes de editar qualquer vídeo.** Estas regras vêm de pedidos e correções da própria Fran e valem para todos os vídeos. Elas mandam sobre as regras de terceiros em `pesquisa/`. As regras de conteúdo (gancho, argumento, CTA) continuam vindo do `analise-conteudos` (STATE.md).

Toda correção nova que a Fran fizer entra aqui na mesma hora, com data, para não ser repetida.

## Visual (02/11/2026)
- **Estilo "luxo":** simples, preto e branco, sem frufru. O render padrão é `scripts/render_luxo.py` com `estilo_luxo.json`. As versões A (ffmpeg colorido) e B (Remotion) do teste de 31/10 não são mais usadas.
- **Só branco, com sombra preta.** Nenhuma cor (nada de amarelo nem rosa) e nenhuma caixa atrás do texto.
- **Legenda:**
  - fonte Montserrat (SemiBold), **não serifada**;
  - estática, sem animação palavra a palavra e sem a palavra falada crescendo;
  - palavra-chave só em itálico.
- **Títulos (gancho, rótulo, texto final):** fonte serifada, Playfair Display.
- **Sombra:** curta e com pouca opacidade, numa camada só (`dx 2, dy 3, blur 3`, cerca de 37% de opacidade). Nada de sombra grande ou halo forte.
  - Ressalva: em roupa branca a leitura cai. Avisar a Fran em vez de reforçar a sombra por conta própria.

## "Comenta QUERO" (02/11/2026)
- **Nunca deixar o tempo todo na tela.** Ele só aparece enquanto ela pede o link ou fala o CTA.
- No CTA, a palavra **QUERO** vai com ênfase: caixa alta, Montserrat ExtraBold, bem maior que o "Comenta".
- Se ela falar "quero" na fala, a palavra sai em ênfase na própria legenda (o `render_luxo.py` já faz).
- Isso substitui a regra antiga do `analise-conteudos` de "Comenta QUERO escrito na tela já na primeira peça".

## Velocidade (07/11/2026)
- **Sempre 1,2x** (pedido da Fran: "sempre colocar 1.2"). Padrão `VELOCIDADE = 1.2` no `montar_natal.py`; `"velocidade"` no `plano.json` só para exceção. O `dur` do gancho é em tempo do vídeo final (já acelerado).

## Cortes (02/11/2026)
- **(03/11) Sem crítica ao produto:** a Fran tirou o "cerâmica pode quebrar, poderia ser outro material". Não incluir ressalvas negativas sobre a peça, mesmo que os dados sugiram ressalva honesta.
- **Cortar todo trecho sem fala:** giro, voltinha, caminhada ou corredor vazio. Se a peça precisa aparecer de costas, começar o trecho já na fala.
  - Não basta o `cortar_pausas_acima_s`, que só corta pausas entre palavras. Conferir o começo e o fim de cada trecho.
- **Nada de transição feia.** Não usar close tremido nem câmera se mexendo. Na troca de look, entrar com ela já de frente, sem o giro de entrada.
- **Tomadas repetidas:** quando ela repete a frase, ficar só com a melhor tomada.
- **Elogio:** cortar o adjetivo e manter o fato (regra do `analise-conteudos`).

- **(03/11) No vídeo só entram as partes em que ela está falando.** Cortar ao máximo os silêncios: pausas, abrir caixa calada, conversa com quem filma. Isso vale também para a abertura.

- **(03/11) Falas cortadas e respiros:** os tempos de palavra do faster-whisper saem **adiantados** (começo ~0,3 s antes, fim ~0,15 s antes), então cortar pelo tempo da transcrição corta o fim das palavras. Os cortes usam o **detector de voz (VAD Silero)**: borda de cada trecho = onde a voz começa/termina de verdade (+0,10 s antes, +0,07 s depois); respiros e silêncios > 0,12 s entre falas saem; entre uma fala que fica e outra que sai, coladas, corta no ponto mais silencioso. A legenda é deslocada +0,25 s.
- **Conferência obrigatória dos cortes:** transcrever cada pedaço cortado e conferir que começa e termina em palavra inteira, sem sobra da frase vizinha.

## Zoom (02/11/2026)
- **Quando ela mostra a peça** (tecido, forro, lastex, modelagem, short, blusa), usar o zoom **"vai e volta"**: entra e volta suave.
- **(03/11) Zoom leve onde for possível mostrar detalhe** (estampa, borda dourada, gravação, pauta, acabamento): até ~12%, em todo momento de detalhe, não só 3 a 5 por vídeo. No `plano.json`: `"zooms": [[de, ate], ...]` por trecho e `"zoom_max"`.
  - Não usar o zoom seco (punch-in).
- **Janelas** de cerca de 1,5 a 3,5 s.

## Stickers e aprovação (03/11/2026)
- **Sticker é sticker "aesthetic", não emoji.** Nada de Fluent Emoji, Twemoji ou parecidos. O estilo é de Pinterest/Instagram: laço coquette, enfeite vintage, azevinho em aquarela, estrela com glitter.
- **Nada de editar, baixar asset ou montar kit antes de a Fran aprovar.** Primeiro mostrar as opções (folha com as imagens), esperar o "pode" e só depois seguir. Quando ela diz "não edita ainda", só preparar (baixar o bruto, transcrever) e perguntar.
- **Legenda (03/11):** a Fran pediu "aumenta um pouco". Nos vídeos de Natal ficou Montserrat SemiBold **74 px** (antes 62 a 64).
- **Vídeos de Natal e achadinhos podem ter cor.** O preto e branco vale para os Reels de provador. **(03/11) A Fran não quer kit do CapCut:** entregar só o vídeo final pronto (`saida/final.mp4`).
- **Introdução (corrigido em 03/11):** os stickers **não trocam**. Os mesmos ficam parados na tela e têm um **leve movimento a cada 0,5 s só na rotação** (mudam o ângulo; não andam em x/y nem mudam de tamanho). **Pequenos** (cerca de 160 a 185 px) e **perto do texto do gancho**. Gerados por `scripts/stickers_intro.py` a partir do `layout_intro.json` do projeto, longe do rosto e da peça.
- **Stickers aprovados ficam em `projetos/<nome>/stickers/`** (fora do git, porque são de terceiros). Origem: pins que a Fran manda. Recortar a cartela em PNGs, montar a folha numerada e esperar ela escolher os códigos.
- **Gancho dos vídeos de Natal (03/11):** texto **no meio da tela**, quebrado em linhas ("Achadinhos" ENTER "de Natal"), em **cores pastel de Natal** (vermelho/rosa pastel #EE8E9C e verde pastel #7FC497), Playfair Display em negrito, com contorno branco fino e sombra leve para dar leitura.
- **Abertura de Natal (03/11):**
  - **glitter** de brilhinhos piscando (`scripts/glitter.py`), em pastel, branco e dourado, com brilhos grandes o bastante para aparecer;
  - **texto com animação de entrada:** cada linha entra crescendo, com um leve "pop" e escalonada;
  - **efeito sonoro** de sininhos subindo junto com o texto (`scripts/sfx_brilho.py`, gerado aqui, sem licença de terceiros), uns 16 dB abaixo da voz.
- **Abertura:** a Fran grava a apresentação ("Achadinhos de Natal da Farm…") num arquivo separado e menor. **Antes de propor a abertura, olhar TODOS os vídeos da pasta do Drive**, não só o mais recente.

- **(03/11, Farm, depois de ver o vídeo pronto) Tirar os stickers e trocar os rótulos rosa por algo clássico.**
  - Rótulos das peças: Playfair Display SemiBold em caixa alta espaçada, **branco**, sombra leve um pouco mais firme que a da legenda (para ler no teto claro). No `plano.json`: `"estilo_textos": "classico"`.
  - "QUERO" do CTA em branco (Montserrat ExtraBold), sem rosa.
  - Sem stickers no vídeo: `"stickers": false` no `plano.json`. Antes de pôr stickers num vídeo novo, perguntar se ela quer.
  - O gancho pastel "Achadinhos de Natal", o glitter e o efeito sonoro da abertura continuam.

## Reels de provador com o pipeline novo (07/11/2026, calça C&A)
- Usar `scripts/montar_natal.py` também no provador: `"stickers": false`, `"efeitos_abertura": false`, `"estilo_textos": "classico"`, `"gancho": {"estilo": "luxo", "sup": ..., "titulo": "*itálico* ...", "dur": ~4,5, "y": 1250}`. Ajustar `rotulo_y`/`cta_y` para não encostar na cabeça dela.
- **Fala baixa:** o VAD pode perder o começo de frase falada mais baixo; o script volta pelo volume (> -55 dB) quando o VAD começa > 0,3 s depois da transcrição. Mesmo assim, conferir cada pedaço transcrevendo.
- **Transcrição completa sem filtro de silêncio** (`vad_filter=False`): com o filtro, o faster-whisper perdeu frases ("Qual é o argumento mais dessa calça?").
- **Capa do Reels:** `scripts/capa.py` a partir da foto que ela manda. A foto 3:4 entra inteira no miolo (é o que a grade do perfil mostra), fundo desfocado completa o 9:16, texto no mesmo estilo do gancho (Playfair branco, sobretítulo em caixa alta + título com itálico) na parte de cima, longe do rosto.

## Conferência antes de entregar
1. Fazer a grade de quadros com o tempo na tela (`drawtext`, 2 a 4 quadros por segundo) e olhar:
   - os trechos sem fala;
   - as transições;
   - se a legenda está legível em cima da roupa.
2. Listar para a Fran as palavras que a transcrição pode ter errado (marca, cupom, nome de modelagem) e pedir confirmação.

## Ambiente
- **Rede:** a transcrição precisa de `huggingface.co` liberado (o modelo do faster-whisper vem de lá).
- **Fontes:** vêm do npm (`@fontsource/playfair-display` e `@fontsource/montserrat`), convertidas de `.woff2` para `.ttf` em `~/.fonts` com o fontTools.
  - Na Montserrat, renomear a família para "Montserrat" (o pacote vem como "Montserrat Thin"), ou o libass não acha a fonte.
- **Bruto:** vem do Drive pela pasta que a Fran manda. Pode ser um arquivo só, mesmo que ela fale em partes: confirmar antes de juntar.
