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

## Cortes (02/11/2026)
- **Cortar todo trecho sem fala:** giro, voltinha, caminhada ou corredor vazio. Se a peça precisa aparecer de costas, começar o trecho já na fala.
  - Não basta o `cortar_pausas_acima_s`, que só corta pausas entre palavras. Conferir o começo e o fim de cada trecho.
- **Nada de transição feia.** Não usar close tremido nem câmera se mexendo. Na troca de look, entrar com ela já de frente, sem o giro de entrada.
- **Tomadas repetidas:** quando ela repete a frase, ficar só com a melhor tomada.
- **Elogio:** cortar o adjetivo e manter o fato (regra do `analise-conteudos`).

## Zoom (02/11/2026)
- **Quando ela mostra a peça** (tecido, forro, lastex, modelagem, short, blusa), usar o zoom **"vai e volta"**: entra moderado (até cerca de 18%) e volta suave.
  - Não usar o zoom seco (punch-in).
- **Janelas** de cerca de 1,5 a 3,5 s, de 3 a 5 por vídeo, marcadas em `zooms` no `plano.json`.

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
