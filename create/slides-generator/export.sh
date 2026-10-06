#!/bin/bash
# Export a slides-generator deck to PDF (all slides, via print CSS) and/or PNG (one file per slide).
# Usage: export.sh "/path/to/Deck.html" [pdf|png|both]
set -euo pipefail

# Chrome/Chromium: $CHROME, macOS app, затем PATH (Linux / Git Bash на Windows)
if [ -z "${CHROME:-}" ]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "/Applications/Chromium.app/Contents/MacOS/Chromium" \
           "$(command -v google-chrome || true)" "$(command -v google-chrome-stable || true)" \
           "$(command -v chromium || true)" "$(command -v chromium-browser || true)" \
           "/c/Program Files/Google/Chrome/Application/chrome.exe"; do
    [ -n "$c" ] && [ -x "$c" ] && CHROME="$c" && break
  done
fi
[ -n "${CHROME:-}" ] || { echo "Chrome/Chromium not found — install it or set \$CHROME" >&2; exit 1; }
HTML="${1:?Usage: export.sh <deck.html> [pdf|png|both]}"
MODE="${2:-both}"

if [ ! -f "$HTML" ]; then
  echo "File not found: $HTML" >&2
  exit 1
fi

DIR="$(cd "$(dirname "$HTML")" && pwd)"
BASE="$(basename "$HTML" .html)"
URL="file://$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$DIR/$BASE.html")"
TOTAL=$(grep -o 'class="slide' "$HTML" | wc -l | tr -d ' ')

if [ "$MODE" = "pdf" ] || [ "$MODE" = "both" ]; then
  echo "→ PDF ($TOTAL slides, using @media print layout)..."
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$DIR/$BASE.pdf" "$URL" 2>/dev/null
  echo "  saved: $DIR/$BASE.pdf"
fi

if [ "$MODE" = "png" ] || [ "$MODE" = "both" ]; then
  OUTDIR="$DIR/$BASE - PNG"
  mkdir -p "$OUTDIR"
  echo "→ PNG ($TOTAL slides, 1920x1080)..."
  for n in $(seq 1 "$TOTAL"); do
    p=$(printf "%02d" "$n")
    "$CHROME" --headless=new --disable-gpu --window-size=1920,1080 \
      --screenshot="$OUTDIR/slide-$p.png" "$URL#slide-$n" 2>/dev/null
  done
  echo "  saved: $OUTDIR/ ($TOTAL files)"
fi
