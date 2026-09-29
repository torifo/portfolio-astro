#!/bin/bash
# Instagram の新着を取り込んで PR を作る。マージすると Actions が本番へ出す。--dry-run で PR を作らない。
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# 取り込みスクリプト（sync_instagram.py）と同じく、リポジトリの2つ上の .env.dev を読む
ENV_FILE="${ENV_FILE:-$(cd "$REPO/../.." && pwd)/.env.dev}"
LOG="$HOME/Library/Logs/portorifo-journey-sync.log"
LOCK="/tmp/portorifo-journey-sync.lock"
WORK="$HOME/Library/Caches/portorifo-journey-sync"
WT="$WORK/worktree"
# 起点。試すときだけ古いコミットを渡す（SYNC_BASE=<sha> で新着がある状態を再現できる）
BASE="${SYNC_BASE:-origin/main}"

# PR に含めるのはここだけ
PATHS=(data/journey public/journey/thumbs)
# Git の管理外だが取り込みに要るもの（撮影地の座標・生の地名辞書）
LOCAL_ONLY=(data/journey/gps.json data/ontology/places.json)

# launchd の PATH は最小限。nvm の node は版でパスが変わるので見つからなければ探す
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
if ! command -v node >/dev/null 2>&1; then
  for dir in "$HOME"/.nvm/versions/node/*/bin; do
    [ -x "$dir/node" ] && export PATH="$dir:$PATH" && break
  done
fi

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }

notify() { # notify <タイトル> <本文>
  osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true
}

DIED=0
die() { # die <理由>
  DIED=1
  log "中断: $1"
  notify "Journey 同期に失敗" "$1"
  exit 1
}

BRANCH=""
PUSHED=0
cleanup() {
  local rc=$?
  # die を通らずに落ちた（set -u の未定義変数など）ときも、黙って終わらせない
  if [ "$rc" -ne 0 ] && [ "$DIED" = "0" ]; then
    log "予期しない終了（終了コード ${rc}）。直前のエラーはこのログにある"
    notify "Journey 同期が途中で止まった" "終了コード ${rc}。ログを確認する"
  fi
  cd "$REPO" 2>/dev/null || return
  [ -d "$WT" ] && git worktree remove --force "$WT" >/dev/null 2>&1
  # push していない作業ブランチは残さない
  [ -n "$BRANCH" ] && [ "$PUSHED" = "0" ] && git branch -D "$BRANCH" >/dev/null 2>&1
  rmdir "$LOCK" 2>/dev/null
}

mkdir -p "$(dirname "$LOG")" "$WORK"
# エラー出力もログに残す（手で走らせたときに見落として原因を失わないため）
exec 2> >(tee -a "$LOG" >&2)

# mkdir はアトミックなので排他に使える
if ! mkdir "$LOCK" 2>/dev/null; then
  log "前回の実行がまだ動いている。今回は見送る。"
  exit 0
fi
trap cleanup EXIT

cd "$REPO" || die "リポジトリが見つからない: $REPO"

for cmd in node npm python3 git curl gh; do
  command -v "$cmd" >/dev/null 2>&1 || die "$cmd が PATH にない"
done

log "=== 開始 ==="

# --- 1. 未マージの同期 PR があれば重ねない（手で直している最中を上書きしないため）---
open_pr="$(gh pr list --state open --json url,headRefName \
  --jq '[.[] | select(.headRefName | startswith("journey/sync-"))][0].url // empty' 2>/dev/null)"
if [ -n "$open_pr" ]; then
  log "未マージの同期 PR がある。今回は見送る: $open_pr"
  notify "Journey 同期は見送り" "未マージの PR があります"
  exit 0
fi

# --- 2. トークンの延命（60日で失効。毎日叩けば都度60日延びる）---
TOKEN="$(grep '^INSTAGRAM_ACCESS_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' \r')"
[ -n "$TOKEN" ] || die "$ENV_FILE に INSTAGRAM_ACCESS_TOKEN が無い"

me="$(curl -s --max-time 30 "https://graph.instagram.com/v21.0/me?fields=id&access_token=$TOKEN")"
case "$me" in
  *'"error"'*)
    # 失効(190)とアクセス遮断(200)で対処が違う
    code="$(printf '%s' "$me" | python3 -c 'import sys,json; print(json.load(sys.stdin)["error"].get("code",""))' 2>/dev/null)"
    [ "$code" = "190" ] && die "トークンが失効した。Meta コンソールで再発行して $ENV_FILE を更新する。"
    die "Instagram API がアクセスを拒否した (code $code)。アプリの状態を確認する。"
    ;;
esac

if [ "$DRY_RUN" = "1" ]; then
  log "トークンは有効。--dry-run なので延命しない。"
else
  refreshed="$(curl -s --max-time 30 "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=$TOKEN")"
  new_token="$(printf '%s' "$refreshed" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))' 2>/dev/null)"
  if [ -n "$new_token" ] && [ "$new_token" != "$TOKEN" ]; then
    # 書き損じでトークンを失わないよう控えを取る
    cp "$ENV_FILE" "$ENV_FILE.bak" || die "$ENV_FILE の控えを取れない"
    tmp="$(mktemp)"
    awk -v t="$new_token" '/^INSTAGRAM_ACCESS_TOKEN=/{print "INSTAGRAM_ACCESS_TOKEN=" t; next} {print}' "$ENV_FILE" > "$tmp" \
      && mv "$tmp" "$ENV_FILE" || die "$ENV_FILE を更新できない"
    TOKEN="$new_token"
    log "トークンを延命した（ここから60日）"
  else
    log "トークンは据え置き"
  fi
fi

# --- 3. 手元を触らないよう、別の作業ツリーで origin/main から始める ---
git fetch -q origin main || die "git fetch に失敗"
BRANCH="journey/sync-$(date +%Y%m%d-%H%M)"
git worktree prune
rm -rf "$WT"
git worktree add -q -b "$BRANCH" "$WT" "$BASE" || die "作業ツリーを作れない"
for f in "${LOCAL_ONLY[@]}"; do
  [ -e "$REPO/$f" ] && ln -s "$REPO/$f" "$WT/$f"
done
cd "$WT" || die "作業ツリーに入れない"

# --- 4. 取り込み ---
# 取り込みスクリプトはトークンを「リポジトリの2つ上の .env.dev」から探すので、作業ツリーでは環境変数で渡す
export INSTAGRAM_ACCESS_TOKEN="$TOKEN"
count_posts() { python3 -c 'import json;print(len(json.load(open("data/journey/posts.json"))["posts"]))'; }
before="$(count_posts)"
npm run journey:sync >>"$LOG" 2>&1 || die "journey:sync が失敗した。ログ: $LOG"
after="$(count_posts)"
log "投稿 $before -> $after 件"

# 減るのは API が壊れた応答を返したときくらい
[ "$after" -ge "$before" ] || die "投稿数が $before から $after に減った。取り込みを疑う。"

if [ -z "$(git status --porcelain -- "${PATHS[@]}")" ]; then
  log "新着なし。何もしない。"
  log "=== 終了 ==="
  exit 0
fi
added="$((after - before))"

# --- 5. コミットして PR の本文を作る ---
git add -- "${PATHS[@]}" || die "git add に失敗"
git commit -q -m "Ingest $added new post(s) from Instagram" -m "---" \
  -m "Instagram の新着 $added 件を取り込んだ（$before → $after 件）。" || die "git commit に失敗"

slug="$(gh repo view --json nameWithOwner -q .nameWithOwner)" || die "リポジトリ名を取れない"
python3 "$HERE/sync_report.py" --root "$WT" --base "$BASE" --repo "$slug" --sha "$(git rev-parse HEAD)" \
  --out "$WORK/report.md" --summary "$WORK/summary.json" >>"$LOG" 2>&1 || die "PR の本文を作れない"
warnings="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["warnings"])' "$WORK/summary.json")"
log "新着 $added 件 / 要確認 $warnings 件"

if [ "$DRY_RUN" = "1" ]; then
  cat "$WORK/report.md"
  log "--dry-run のため push も PR もしない"
  exit 0
fi

# --- 6. push して PR（マージで本番デプロイが走る）---
git push -q -u origin "$BRANCH" || die "git push に失敗"
PUSHED=1

title="Journey: 新着 $added 件（$(date +%Y-%m-%d)）"
# 変数名の直後に全角文字を置くと、日本語ロケールの bash は変数名の続きとして読む（${} で区切る）
[ "$warnings" -gt 0 ] && title="${title}・要確認 ${warnings} 件"
url="$(gh pr create --base main --head "$BRANCH" --title "$title" --body-file "$WORK/report.md")" \
  || die "PR を作れない（ブランチ $BRANCH は push 済み）"

log "PR を作った: $url"
if [ "$warnings" -gt 0 ]; then
  notify "Journey に新着 $added 件" "PR を作った。要確認が $warnings 件ある。"
else
  notify "Journey に新着 $added 件" "PR を作った。問題が無ければマージで本番に出る。"
fi
log "=== 終了 ==="
