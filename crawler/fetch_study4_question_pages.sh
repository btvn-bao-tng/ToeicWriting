#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${1:-data/database.db}"
CACHE_DIR="${2:-/private/tmp/study4_questions}"
ONLY_PLACEHOLDERS="${STUDY4_ONLY_PLACEHOLDERS:-0}"
DELAY_SECONDS="${STUDY4_DELAY_SECONDS:-0}"

if [[ -z "${STUDY4_COOKIE:-}" ]]; then
  echo "Set STUDY4_COOKIE to a valid Study4 cookie string before running." >&2
  exit 2
fi

mkdir -p "$CACHE_DIR"

if [[ "$ONLY_PLACEHOLDERS" == "1" ]]; then
  FILTER_SQL="WHERE EXISTS (
    SELECT 1
    FROM toeic_sw_writing_questions q
    WHERE q.study4_test_id = t.study4_test_id
      AND q.question_number BETWEEN 1 AND 5
      AND q.prompt_text LIKE 'Image %'
  )"
else
  FILTER_SQL=""
fi

sqlite3 -separator $'\t' "$DB_PATH" "
  SELECT study4_test_id, slug, group_concat(part_param, '&') AS parts
  FROM (
    SELECT
      t.study4_test_id AS study4_test_id,
      t.test_number AS test_number,
      t.slug AS slug,
      p.sort_order AS sort_order,
      'part=' || p.study4_part_id AS part_param
    FROM toeic_sw_writing_tests t
    JOIN toeic_sw_writing_parts p ON p.study4_test_id = t.study4_test_id
    ${FILTER_SQL}
    ORDER BY t.test_number, p.sort_order
  )
  GROUP BY study4_test_id
  ORDER BY test_number;
" | while IFS=$'\t' read -r test_id slug parts; do
  url="https://study4.com/tests/${test_id}/practice/?${parts}"
  output="${CACHE_DIR}/study4_questions_${test_id}.html"
  echo "Fetching ${url}"
  curl -L -sS --compressed --max-time 30 \
    -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
    -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
    -H 'accept-language: en,en-US;q=0.9,en-GB;q=0.8,vi;q=0.7' \
    -H 'cache-control: max-age=0' \
    -H 'priority: u=0, i' \
    -H "referer: https://study4.com/tests/${test_id}/${slug}/" \
    -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "macOS"' \
    -H 'sec-fetch-dest: document' \
    -H 'sec-fetch-mode: navigate' \
    -H 'sec-fetch-site: same-origin' \
    -H 'sec-fetch-user: ?1' \
    -H 'upgrade-insecure-requests: 1' \
    -b "$STUDY4_COOKIE" \
    -o "$output" \
    "$url"
  if [[ "$DELAY_SECONDS" != "0" ]]; then
    sleep "$DELAY_SECONDS"
  fi
done
