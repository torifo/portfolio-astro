"""Wikidata SPARQL の薄いクライアント。

リトライとレート制御だけを担当し、クエリの中身は呼び出し側が持つ。
"""

import json
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "portfolio-journey-ontology/0.1 (https://portorifo.riumu.net)"

# Wikidata の負荷を抑えるため、クエリ間に必ずこの秒数を空ける
MIN_INTERVAL_SEC = 1.5
_last_call = 0.0


def run(query: str, *, retries: int = 3, timeout: int = 180) -> list[dict]:
    """SPARQL を実行し、bindings を素の dict のリストにして返す。

    値は {"value": ...} の入れ子を剥がして、変数名 -> 文字列 の形に均す。
    """
    global _last_call

    last_error: Exception | None = None
    for attempt in range(retries):
        elapsed = time.time() - _last_call
        if elapsed < MIN_INTERVAL_SEC:
            time.sleep(MIN_INTERVAL_SEC - elapsed)

        url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query})
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                payload = json.load(res)
            _last_call = time.time()
            return [
                {k: v["value"] for k, v in row.items()}
                for row in payload["results"]["bindings"]
            ]
        except Exception as exc:  # タイムアウト・429・一時的な500をまとめて再試行
            last_error = exc
            _last_call = time.time()
            if attempt < retries - 1:
                backoff = 5 * (attempt + 1)
                print(f"  retry in {backoff}s ({type(exc).__name__}: {exc})")
                time.sleep(backoff)

    raise RuntimeError(f"SPARQL failed after {retries} attempts: {last_error}")


def qid(uri: str) -> str:
    """エンティティURIから Q番号だけ取り出す。"""
    return uri.rsplit("/", 1)[-1]
