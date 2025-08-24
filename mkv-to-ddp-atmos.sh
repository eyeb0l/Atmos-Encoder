#!/usr/bin/env bash
# mkv-to-ddp-atmos.sh
# 1) Extract first TrueHD stream from an MKV
# 2) Encode 5.1 DD+ Atmos via your main.py (-am 5.1 -w normal)
# 3) Remux MKV with new DD+ Atmos track, removing all original audio tracks
#
# Usage:
#   ./mkv-to-ddp-atmos.sh -i "Movie.mkv" [-b 768] [-l en] [-o /path/to/outdir]

set -euo pipefail

# Defaults
BITRATE=768
LANG=en
OUTDIR=""

usage() {
  echo "Usage: $0 -i <input.mkv> [-b 768] [-l en] [-o outdir]"
}

# Parse args
INPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input) INPUT="$2"; shift 2 ;;
    -b|--bitrate) BITRATE="$2"; shift 2 ;;
    -l|--lang|--language) LANG="$2"; shift 2 ;;
    -o|--outdir|--output-dir) OUTDIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "${INPUT}" ]]; then
  echo "Error: input MKV not specified."; usage; exit 1
fi
[[ -f "$INPUT" ]] || { echo "Error: file not found: $INPUT" >&2; exit 1; }

# Validate bitrate
ALLOWED_BA=(384 448 576 640 768 1024)
valid_bitrate=false
for v in "${ALLOWED_BA[@]}"; do
  if [[ "$BITRATE" == "$v" ]]; then valid_bitrate=true; break; fi
done
if [[ "$valid_bitrate" != true ]]; then
  echo "Error: invalid bitrate '$BITRATE'. Allowed: ${ALLOWED_BA[*]}" >&2
  exit 1
fi

# Resolve paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_PY="${SCRIPT_DIR}/main.py"
[[ -f "$MAIN_PY" ]] || { echo "Error: main.py not found at $MAIN_PY" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

for dep in mkvmerge mkvextract ffmpeg python3; do
  have "$dep" || { echo "Error: dependency not found: $dep" >&2; exit 1; }
done

# Prepare output dir
if [[ -z "${OUTDIR}" ]]; then
  OUTDIR="$PWD"
fi
mkdir -p "$OUTDIR"

# Work dir
WORKDIR="$(mktemp -d -t ddp-thd-XXXXXX)"
trap 'rm -rf "$WORKDIR"' EXIT

# Base names
IN_BASENAME="$(basename "$INPUT")"
BASE="${IN_BASENAME%.*}"

echo "[INFO] Input: $INPUT"
echo "[INFO] Work dir: $WORKDIR"

# 1) Find first TrueHD track id
TRACK_ID=""
if have jq; then
  TRACK_ID="$(mkvmerge -J "$INPUT" \
    | jq -r '.tracks[] | select(.type=="audio" and (.codec=="A_TRUEHD" or (.properties.codec_id?=="A_TRUEHD"))) | .id' \
    | head -n1)"
fi
if [[ -z "$TRACK_ID" ]]; then
  INFO="$(mkvmerge -i "$INPUT")"
  TRACK_ID="$(sed -n 's/^[Tt]rack ID \([0-9]\+\): audio (.*) (A_TRUEHD).*/\1/p' <<<"$INFO" | head -n1)"
  if [[ -z "$TRACK_ID" ]]; then
    TRACK_ID="$(sed -n 's/^[Tt]rack ID \([0-9]\+\): audio (.*TrueHD.*).*/\1/p' <<<"$INFO" | head -n1)"
  fi
fi
if [[ -z "$TRACK_ID" ]]; then
  echo "Error: no TrueHD track found in: $INPUT" >&2
  exit 1
fi
echo "[INFO] TrueHD track id: $TRACK_ID"

# 2) Extract THD
THD_OUT="${WORKDIR}/${BASE}.thd"
echo "[INFO] Extracting TrueHD to: $THD_OUT"
mkvextract tracks "$INPUT" "${TRACK_ID}:${THD_OUT}"

# 3) Encode 5.1 DD+ Atmos via your main.py
echo "[INFO] Running Atmos encode: 5.1 DD+ Atmos at ${BITRATE} kbps"
python3 "$MAIN_PY" -i "$THD_OUT" -ba "$BITRATE" -am 5.1 -w normal

# 4) Locate the produced DD+ Atmos file
DDP_DIR="${SCRIPT_DIR}/ddp_encode"
DDP_AUDIO="${DDP_DIR}/${BASE}_atmos_5_1.mp4"
if [[ ! -f "$DDP_AUDIO" ]]; then
  echo "Error: expected encoder output not found: $DDP_AUDIO" >&2
  exit 1
fi
echo "[INFO] Encoder output: $DDP_AUDIO"

# 5) Remux MKV: remove all original audio, add new DD+ Atmos
OUT_MKV="${OUTDIR}/${BASE}.DDP.Atmos.mkv"
TITLE="DD+ Atmos 5.1 ${BITRATE} kbps"

echo "[INFO] Writing new MKV: $OUT_MKV"
ffmpeg -loglevel error -y \
  -i "$INPUT" \
  -i "$DDP_AUDIO" \
  -map 0 -map -0:a \
  -map 1:a:0 \
  -c copy \
  -metadata:s:a:0 language="$LANG" \
  -metadata:s:a:0 title="$TITLE" \
  -disposition:a:0 default \
  "$OUT_MKV"

echo "[OK] Done."
echo " - Output: $OUT_MKV"
