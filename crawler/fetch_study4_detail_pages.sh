#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/database.db}"
CACHE_DIR="${2:-/private/tmp/study4_details}"

mkdir -p "$CACHE_DIR"

sqlite3 -separator $'\t' "$DB_PATH" "
  SELECT study4_test_id, slug
  FROM toeic_sw_writing_tests
  ORDER BY test_number;
" | while IFS=$'\t' read -r test_id slug; do
  url="https://study4.com/tests/${test_id}/${slug}/"
  output="${CACHE_DIR}/study4_detail_${test_id}.html"
  echo "Fetching ${url}"
  curl -L -sS --max-time 30 \
    -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
    -o "$output" \
    "$url"
done
