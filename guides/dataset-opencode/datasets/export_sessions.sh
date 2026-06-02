#!/usr/bin/env bash
# Export all OpenCode sessions to individual JSON files.
#
# Usage:
#   ./export_sessions.sh [output_dir]
#
# Defaults to ./session_data if no output directory is given.
# Requires: opencode CLI with `db` and `export` subcommands.

set -euo pipefail

OUTPUT_DIR="${1:-$(dirname "$0")/session_data}"
mkdir -p "$OUTPUT_DIR"

echo "Fetching session IDs..."
SESSION_IDS=$(opencode db "SELECT id FROM session ORDER BY time_created;" --format json \
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
