#!/usr/bin/env bash
# 同期 PR を作る（journey-sync.yml から呼ぶ）。要る環境変数: BRANCH BEFORE ADDED BASE DRY_RUN GH_TOKEN WRITE_TOKEN GITHUB_REPOSITORY RUNNER_TEMP GITHUB_STEP_SUMMARY
set -euo pipefail

commit_posts() {
  git add -- data/journey public/journey/thumbs
  git commit -q -m "Ingest $ADDED new post(s) from Instagram" -m "---" \
    -m "Instagram の新着 $ADDED 件を取り込んだ（$BEFORE → $((BEFORE + ADDED)) 件）。"
}

report() {
  python3 scripts/journey/sync_report.py --root . --base "$BASE" --repo "$GITHUB_REPOSITORY" \
    --sha "$(git rev-parse HEAD)" --out "$RUNNER_TEMP/report.md" --summary "$RUNNER_TEMP/summary.json" "$@"
}

summary_field() {
  python3 -c 'import json,sys;v=json.load(open(sys.argv[1]))[sys.argv[2]];print(",".join(v) if isinstance(v,list) else str(v).lower())' \
    "$RUNNER_TEMP/summary.json" "$1"
}

read_summary() {
  auto="$(summary_field autoMerge)"
  warnings="$(summary_field warnings)"
}

open_pr() {
  title="Journey: 新着 ${ADDED} 件（$(TZ=Asia/Tokyo date +%Y-%m-%d)）"
  [ "$warnings" -gt 0 ] && title="${title}・要確認 ${warnings} 件"
  git push -q -u origin "$BRANCH"
  url="$(gh pr create --base main --head "$BRANCH" --title "$title" --body-file "$RUNNER_TEMP/report.md")"
  echo "PR: $url" | tee -a "$GITHUB_STEP_SUMMARY"
}

merge_pr() {
  # 作った直後は GitHub がマージできるかをまだ決めていない（UNKNOWN）ことがあるので、決まるまで少し待つ
  for _ in 1 2 3 4 5 6; do
    [ "$(gh pr view "$url" --json mergeable -q .mergeable 2>/dev/null || true)" != "UNKNOWN" ] && break
    sleep 5
  done
  # GITHUB_TOKEN でマージした push では Deploy が起動しないので、個人トークンでマージして本番まで流す
  GH_TOKEN="$WRITE_TOKEN" gh pr merge "$url" --rebase --delete-branch \
    || { sleep 15; GH_TOKEN="$WRITE_TOKEN" gh pr merge "$url" --rebase --delete-branch; }
  echo "日付の後ろの場所だけで要確認も無いので、マージした（Deploy to Production が本番へ出す）" | tee -a "$GITHUB_STEP_SUMMARY"
}

count() { python3 -c 'import json;print(len(json.load(open("data/journey/posts.json"))["posts"]))'; }

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
commit_posts
report
cat "$RUNNER_TEMP/report.md" >> "$GITHUB_STEP_SUMMARY"
read_summary
auto_ids="$(summary_field autoIds)"
hold_ids="$(summary_field holdIds)"
auto_count="$(python3 -c 'import sys;print(len([i for i in sys.argv[1].split(",") if i]))' "$auto_ids")"
hold_count="$(python3 -c 'import sys;print(len([i for i in sys.argv[1].split(",") if i]))' "$hold_ids")"
if [ "$auto_count" -gt 0 ] && [ "$hold_count" -gt 0 ]; then
  plan="場所を書いた投稿と書いていない投稿（または要確認が出た投稿）が混ざっているので、PR を分ける（組み直して自動マージできなければ1つに戻す）"
elif [ "$auto" = "true" ]; then
  plan="新着がすべて日付の後ろの場所で要確認も無いので、PR を作ってマージする"
else
  plan="PR を作って開いたままにする"
fi
echo "自動マージ $auto_count 件 / 保留 $hold_count 件：$plan" | tee -a "$GITHUB_STEP_SUMMARY"
if [ "$DRY_RUN" = "true" ]; then
  echo "dry_run なので push も PR もしない"
  exit 0
fi

if [ "$auto_count" -eq 0 ] || [ "$hold_count" -eq 0 ]; then
  open_pr
  [ "$auto" = "true" ] || exit 0
  merge_pr
  exit 0
fi

full_sha="$(git rev-parse HEAD)"
full_added="$ADDED"
python3 scripts/journey/drop_posts.py --root . --ids "$hold_ids"
npm run journey:build
# 全件のコミットを、保留を除いたコミットで置き換える
git reset --soft HEAD^
ADDED="$auto_count"
commit_posts
report
read_summary
if [ "$auto" != "true" ]; then
  echo "組み直すと自動マージできないため、全件の PR に戻す" | tee -a "$GITHUB_STEP_SUMMARY"
  git reset --hard "$full_sha"
  ADDED="$full_added"
  report
  read_summary
  open_pr
  exit 0
fi

open_pr
auto_pr="${url##*/}"
merge_pr
# 自動マージ済みの main から保留分を取り込み直し、データの競合を避ける（gh pr merge は手元を main に切り替えていることがある）
git fetch -q origin main
BASE="origin/main"
BRANCH="${BRANCH}-hold"
git checkout -q -b "$BRANCH" "$BASE"
BEFORE="$(count)"
npm run journey:sync
after="$(count)"
[ "$after" -ge "$BEFORE" ] || { echo "::error::投稿数が $BEFORE から $after に減った"; exit 1; }
# API は既知の投稿だけのページで読むのをやめるので、新着が多い日は保留分を拾い損ねうる
missing="$(python3 -c 'import json,sys;have={p["id"] for p in json.load(open("data/journey/posts.json"))["posts"]};print(",".join(i for i in sys.argv[1].split(",") if i not in have))' "$hold_ids")"
if [ -n "$missing" ]; then
  msg="保留の投稿を取り込み直せなかった: ${missing}（Run workflow をもう一度回す。それでも拾えなければ手元で sync_instagram.py --all）"
  echo "::warning::$msg"
  echo "$msg" >> "$GITHUB_STEP_SUMMARY"
fi
if [ -z "$(git status --porcelain -- data/journey public/journey/thumbs)" ]; then
  echo "保留分の取り込み直しで新着が無かった" | tee -a "$GITHUB_STEP_SUMMARY"
  exit 0
fi
ADDED="$((after - BEFORE))"
commit_posts
report --preface "日付の後ろに場所を書いた $auto_count 件は #$auto_pr で自動マージした。"
cat "$RUNNER_TEMP/report.md" >> "$GITHUB_STEP_SUMMARY"
read_summary
open_pr
