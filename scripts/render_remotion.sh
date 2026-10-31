#!/usr/bin/env bash
# Versão B: renderiza com Remotion sobre o mesmo cortado.mp4/cortado.json da versão A.
# Uso: scripts/render_remotion.sh projetos/<nome>
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
P="$(cd "$1" && pwd)"
cd "$RAIZ/remotion"
[ -d node_modules ] || npm install --silent --no-audit --no-fund
python3 -c "import json,sys; d=json.load(open('$P/saida/cortado.json')); json.dump({'dados': d, 'video': 'cortado.mp4'}, open('$P/saida/props.json','w'), ensure_ascii=False)"
CHROME=$(ls -d /opt/pw-browsers/chromium-*/chrome-linux*/chrome 2>/dev/null | head -1 || true)
npx remotion render src/index.jsx Reel "$P/saida/final_remotion_bruto.mp4" --props="$P/saida/props.json" \
  --public-dir="$P/saida" --concurrency="$(nproc)" ${CHROME:+--browser-executable=$CHROME} --log=error
# Mesmo acabamento de exportação da versão A (H.264 High, faststart, áudio sem recompressão extra).
ffmpeg -v error -y -i "$P/saida/final_remotion_bruto.mp4" -c:v libx264 -preset slow -crf 18 -profile:v high \
  -pix_fmt yuv420p -c:a copy -movflags +faststart "$P/saida/final_remotion.mp4"
rm -f "$P/saida/final_remotion_bruto.mp4" "$P/saida/props.json"
echo "ok: $P/saida/final_remotion.mp4"
