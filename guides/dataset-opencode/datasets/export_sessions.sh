#!/usr/bin/env bash
# Export OpenCode sessions to individual JSON files.
#
# Usage:
#   ./export_sessions.sh [-n N] [output_dir]
#
# Options:
#   -n N    Export up to N sessions (default: 10). Use 0 for all.
#
# Defaults to ./session_data if no output directory is given.
# Requires: opencode CLI with `db` and `export` subcommands.

set -euo pipefail

command -v opencode >/dev/null 2>&1 || {
  echo "Error: 'opencode' CLI not found in PATH." >&2
  exit 1
}

LIMIT=10
while getopts ":n:h" opt; do
  case "$opt" in
    n) LIMIT="$OPTARG" ;;
    h)
      sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
    :)  echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

if ! [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "Error: -n must be a non-negative integer (got '$LIMIT')." >&2
  exit 1
fi

OUTPUT_DIR="${1:-$(dirname "$0")/session_data}"
mkdir -p "$OUTPUT_DIR"

echo "Fetching session IDs..."
SQL="SELECT id FROM session ORDER BY time_created"
if [[ "$LIMIT" -gt 0 ]]; then
  SQL+=" LIMIT $LIMIT"
fi
SQL+=";"
SESSION_IDS=$(opencode db "$SQL" --format json \
  | python3 -c "import sys, json; [print(s['id']) for s in json.load(sys.stdin)]")

TOTAL=$(echo "$SESSION_IDS" | wc -l)
echo "Found $TOTAL sessions. Exporting to $OUTPUT_DIR ..."

COUNT=0
SKIPPED=0
for SID in $SESSION_IDS; do
  COUNT=$((COUNT + 1))
  OUTFILE="$OUTPUT_DIR/${SID}.json"

  if [[ -f "$OUTFILE" ]]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  # `opencode export` writes an info line to stderr; capture only stdout.
  if opencode export "$SID" > "$OUTFILE" 2>/dev/null; then
    printf "\r[%d/%d] Exported %s" "$COUNT" "$TOTAL" "$SID"
  else
    echo -e "\n[%d/%d] FAILED  %s" "$COUNT" "$TOTAL" "$SID"
    rm -f "$OUTFILE"
  fi
done

echo ""
echo "Done. Exported $((COUNT - SKIPPED)) new sessions ($SKIPPED already existed)."
echo "Files are in: $OUTPUT_DIR"
