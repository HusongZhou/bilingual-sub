#!/usr/bin/env bash
# Generic pipeline: give it any YouTube URL and get back a video with
# embedded English/Chinese bilingual subtitles.
#
# Output goes to <out-dir>/<video title>/ ; <out-dir> defaults to the folder
# two levels above this script (tools/bilingual-sub -> E:\Asset Library\youtube).
#
# Usage:
#   ./bilingual_sub.sh <youtube_url> [--engine ENGINE] [--api-key KEY] [--model M] [--base-url URL] [--context "..."] [--out-dir DIR] [--burn]
#
# --engine: google (default, no key) | deepl | microsoft | yandex | claude | deepseek | openai
# API keys: put them in .env next to this script (copy .env.example), or pass --api-key.
# See translate_srt.py for details.
# --burn permanently renders the subtitles into the video frame instead of
#   attaching them as a selectable soft-subtitle track.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

URL="$1"
shift || true

ENGINE="google"
API_KEY=""
REGION=""
MODEL=""
BASE_URL=""
CONTEXT=""
OUT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BURN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine) ENGINE="$2"; shift 2 ;;
    --api-key) API_KEY="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    --context) CONTEXT="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --burn) BURN=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$URL" ]]; then
  echo "Usage: $0 <youtube_url> [--engine ENGINE] [--api-key KEY] [--model M] [--context \"...\"] [--out-dir DIR] [--burn]"
  exit 1
fi

# Windows: keys saved with `setx` only reach terminals opened afterwards; read the saved value as a fallback.
for VAR in DEEPSEEK_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY DEEPL_API_KEY MICROSOFT_TRANSLATOR_KEY YANDEX_API_KEY; do
  if [[ -z "${!VAR}" ]] && command -v powershell.exe >/dev/null; then
    VAL=$(powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('$VAR','User')" | tr -d '\r\n')
    [[ -n "$VAL" ]] && export "$VAR=$VAL"
  fi
done

if ! command -v ffmpeg >/dev/null && command -v cygpath >/dev/null; then
  FF_DIR=$(ls -d "$(cygpath -u "$LOCALAPPDATA")"/Microsoft/WinGet/Packages/*FFmpeg*/*/bin 2>/dev/null | head -1)
  [[ -z "$FF_DIR" ]] && { echo "ffmpeg not found. Install it: winget install ffmpeg"; exit 1; }
  export PATH="$FF_DIR:$PATH"
fi
command -v ffmpeg >/dev/null || { echo "ffmpeg not found. Install it first."; exit 1; }

export PYTHONIOENCODING=utf-8
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

echo "== Downloading video + English subtitles into $OUT_DIR =="
yt-dlp --encoding utf-8 -f "bv*+ba/best" --merge-output-format mp4 \
  --write-subs --write-auto-subs --sub-langs "en,en-orig,en-US,en-GB" \
  --sub-format srt --convert-subs srt \
  --print after_move:filepath \
  -P "$OUT_DIR" -o "%(title)s/%(title)s.%(ext)s" \
  "$URL" > "$LOG"

VIDEO=$(grep -E '\.(mp4|mkv|webm)$' "$LOG" | tail -1)
[[ -n "$VIDEO" ]] && command -v cygpath >/dev/null && VIDEO=$(cygpath -u "$VIDEO")
VIDEO_DIR=$(dirname "$VIDEO")
BASENAME="${VIDEO%.*}"
EN_SRT=$(ls "${BASENAME}".*en*.srt 2>/dev/null | head -1)

if [[ -z "$VIDEO" || -z "$EN_SRT" ]]; then
  echo "Could not locate the downloaded video or its English subtitle file."
  echo "The video may have no English subtitles. yt-dlp output:"
  cat "$LOG"
  exit 1
fi

echo "Folder: $VIDEO_DIR"
echo "Video:  $(basename "$VIDEO")"
echo "Subs:   $(basename "$EN_SRT")"

echo "== Translating to bilingual subtitles (engine: $ENGINE) =="
TRANSLATE_ARGS=(--engine "$ENGINE")
[[ -n "$API_KEY" ]] && TRANSLATE_ARGS+=(--api-key "$API_KEY")
[[ -n "$REGION" ]] && TRANSLATE_ARGS+=(--region "$REGION")
[[ -n "$MODEL" ]] && TRANSLATE_ARGS+=(--model "$MODEL")
[[ -n "$BASE_URL" ]] && TRANSLATE_ARGS+=(--base-url "$BASE_URL")
[[ -n "$CONTEXT" ]] && TRANSLATE_ARGS+=(--context "$CONTEXT")

python "$SCRIPT_DIR/translate_srt.py" "$EN_SRT" "${TRANSLATE_ARGS[@]}"
BILINGUAL_SRT="${EN_SRT%.srt}.bilingual.srt"

echo "== Muxing subtitles into the video =="
OUT="${BASENAME}_bilingual.mp4"

if [[ "$BURN" -eq 1 ]]; then
  # ffmpeg's subtitles filter can't take paths with spaces/colons/quotes, so use a plain temp name.
  cd "$VIDEO_DIR"
  cp "$BILINGUAL_SRT" .burn_tmp.srt
  ffmpeg -y -i "$VIDEO" -vf "subtitles=.burn_tmp.srt" -c:a copy "$OUT"
  rm -f .burn_tmp.srt
else
  ffmpeg -y -i "$VIDEO" -i "$BILINGUAL_SRT" -map 0 -map 1 -c copy -c:s mov_text \
    -metadata:s:s:0 language=chi "$OUT"
fi

echo "Done: $OUT"
