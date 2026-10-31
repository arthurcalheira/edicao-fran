# Pesquisa: ferramentas e técnicas para editar os Reels da Fran (31/10/2026)

Formato-alvo: Reels de provador e comprinhas (Renner, C&A, Riachuelo, Farm). Fala para a câmera, 2 ou 3 looks, de 40 a 90 s, legenda queimada e "Comenta QUERO".

As regras de conteúdo vêm do repositório `analise-conteudos` (STATE.md e `analises/*/ajustes_video_*.md`). **Quando a pesquisa e os dados da Fran discordam, valem os dados dela.**

## 1. Skills e ferramentas (o Claude edita sozinho, sem GPU)

| # | Ferramenta | O que faz | Veredito |
|---|---|---|---|
| 1 | [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill), MIT | Agent Skill com ~40 scripts Python + FFmpeg: corte de silêncio e de filler por palavra, legenda karaokê em ASS, card de gancho, loudness em −14 LUFS, preset de Reels e **exportação de timeline (FCPXML/EDL/OTIO)**. Roda sem GPU e sem API paga | **Base principal** |
| 2 | [browser-use/video-use](https://github.com/browser-use/video-use), MIT | Método "o Claude lê a transcrição → gera a lista de cortes → renderiza → um subagente crítico revisa" | Copiar o método. A transcrição dele usa ElevenLabs (paga) e entra no lugar o faster-whisper |
| 3 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) e [WhisperX](https://github.com/m-bain/whisperX) | Transcrição com o tempo de cada palavra. O WhisperX tem alinhador próprio para português | Motor de transcrição; já é o que o `analise-conteudos` usa |
| 4 | [auto-editor](https://github.com/WyattBlue/auto-editor), domínio público | Corta silêncio e acelera trechos. Exporta para Premiere, Resolve e FCP | Alternativa para o passe de silêncio |
| 5 | [pycaps](https://github.com/francozanardi/pycaps), MIT, alpha | Legendas estilo TikTok com CSS e emoji colorido, renderizadas no Chromium | Opção para legenda mais bonita, mas imatura |
| 6 | [Remotion + skills](https://github.com/remotion-dev/skills) | Vídeo em React, com skills oficiais de legenda e render | **Viável (testado em 31/10).** É grátis para pessoa física e empresa com até 3 funcionários. Um Reel de 60 s levou 5 min 14 s para renderizar aqui, contra 31 s do ffmpeg. A camada visual fica mais bonita (legenda animada, emoji colorido, cards), mas não exporta projeto editável |
| 7 | [blazerior/videoediting-claude-skill](https://github.com/blazerior/videoediting-claude-skill) | Quase o nosso caso: faster-whisper, corte de filler, punch-in e −14 LUFS | Referência, imatura |

**Descartados:**
- DaVinci Resolve MCP: precisa do Resolve Studio com interface gráfica.
- MCPs de CapCut: não são oficiais e o formato muda.
- editly: parado desde 2025.
- anthropics/skills: não tem skill de vídeo.

**Cuidados:**
- **Emoji:** sai em preto e branco no ffmpeg (testado aqui). A saída é usar PNG.
- **Fontes:** instalar fontes com ç, ã e õ.
- **Legendas depois de acelerar:** recalcular os tempos.
- **Silêncio:** o Whisper inventa texto em trechos sem fala.
- **Exportação:** H.264 High, yuv420p, 1080×1920, 30 fps, AAC 48 kHz e `+faststart`.

## 2. Técnicas de edição

### O que o Instagram diz (oficial)
- **Sinais que mais pesam:** tempo de exibição, curtidas e **envios** (Mosseri, jan/2025). Os envios pesam mais para quem não segue a conta.
- **Tempo de exibição:** é contado em segundos, e um vídeo longo não é punido por ter uma % menor assistida.
- **Taxa de pulo:** é a saída nos 3 primeiros segundos. O **gráfico de retenção** (ago/2025) mostra onde cortar.
- **Originalidade:** marca d'água de CapCut ou TikTok e repost reduzem a recomendação.
- **Trial Reels:** o vídeo vai só para quem não segue a conta. Servem para testar o gancho sem gastar a base.
- **"Comente uma palavra":** em 2024 o Instagram disse que não recomenda pedidos de comentário feitos para inflar o alcance. Depois esclareceu que DM automática para mandar link de verdade é permitida. Usar como utilidade ("te mando o link").
- **Área segura (guia de anúncios da Meta, a mais restritiva):** 14% livres em cima, 35% embaixo e 6% de cada lado. Em 1080×1920, o texto importante fica entre Y≈270 e Y≈1250.

### Regras práticas (de terceiros, a validar com o gráfico de retenção da Fran)
- **Gancho escrito:** no máximo 10 palavras, fonte sans grossa de 60 a 80 px, contorno ou fundo, no terço de cima. **Repete a fala** (marca + motivo), sem substituir a Fran falando.
- **Legenda:** blocos de 2 a 4 palavras, com 1 cor de destaque só na palavra-chave (marca, tecido, tamanho), abaixo do queixo e sem cobrir a roupa.
  - Não há estudo sério comparando palavra a palavra com frase inteira. Testar.
- **Ritmo:** 1 a 2 cortes secos a cada 10 s (dado da Fran). Entre eles, mudanças que não são corte:
  - punch-in de 10 a 15%;
  - B-roll de 0,7 a 1,5 s do tecido, da etiqueta ou do caimento, sobre a fala;
  - palavra destacada na legenda.
- **Silêncio:** cortar pausas de mais de 0,3 s.
- **Áudio:** voz em −14 LUFS e pico de −1 dBTP. Música, se tiver, de 18 a 24 dB abaixo da voz. Áudio em alta não é punido, mas também não dá bônus.
- **Troca de look:** corte no movimento (giro ou mão na câmera), com o mesmo enquadramento. A fala pode atravessar o corte (J-cut/L-cut). Nada de transição chamativa na abertura.
- **Capa:** a grade do perfil corta em 3:4. Deixar rosto e look no miolo de 1080×1440.
- **Fim:** a pergunta "1 ou 2?" no fim pode emendar com o começo (loop).

## 3. Regras da Fran que mandam (do `analise-conteudos`)
1. **Abertura:** a Fran fala para a câmera nos 2 primeiros segundos, com a marca e um motivo concreto ("comprei", "a mais vendida", uma escolha). A sacola ajuda.
   - Não cortar a introdução falada; acelerar para 1,3x se precisar.
   - Cabide, ou roupa sem fala, na abertura deu mais de 80% de pulo.
2. **Promessa:** o que o gancho promete aparece em até 10 s.
3. **Cupom:** nada de cupom ou desconto nos 3 primeiros segundos. Sem preço em reais.
4. **Looks:** 2 ou 3 por vídeo. A demonstração mais forte nos primeiros 20 s.
5. **Em cada peça:** tamanho com motivo, altura (1,64 m), tecido, uma objeção respondida com demonstração e uma ressalva honesta.
6. **Elogio:** cortar o adjetivo e manter o fato.
7. **Fim:** veredito, escolha ("1 ou 2?") e pedido de link falado. "Comenta QUERO" escrito na tela desde a primeira peça.
8. **Medição:** comparar só com 24 h ou mais no ar.
