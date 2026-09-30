# ドキュメント / Documentation

このディレクトリには、プロジェクトのドキュメントが整理されています。

## 📁 ディレクトリ構成

### superpowers/specs/
機能の設計書

- **[2026-09-11-journey-instagram-design.md](./superpowers/specs/2026-09-11-journey-instagram-design.md)** - Journey × Instagram 連携
  - 都道府県の解決パイプライン（raw + 辞書 + override の純関数）
  - 外部依存を任意レイヤに置く方針
  - 調査で覆った事実の記録
  - 2026-09-29 改訂: 毎朝の同期と PR での確認、PR の点検、座標が無い環境での判定、
    人の指定の置き場（県・撮影日）、旅の判定規則、海外の枠と地方シルエット
- **[2026-09-30-journey-accuracy-design.md](./superpowers/specs/2026-09-30-journey-accuracy-design.md)** - Journey 県判定の精度改善
  - 文字だけの判定の精度を測る `eval_resolve.py`、判定の層の順序と除外語、日付の後ろの場所、同じ日の点検

### deployment/
デプロイメントとバージョン管理に関するドキュメント

- **[DEPLOYMENT.md](./deployment/DEPLOYMENT.md)** - デプロイ手順とワークフロー
  - main への push で本番が入れ替わる仕組み（GitHub Actions）
  - Journey の同期（毎朝 Instagram の新着を取り込んで PR にする）
  - 必要な GitHub Secrets とリポジトリ設定
  - 存在しない URL の 404
  - push 前に手元で CI と同じビルドを再現する方法
  - ロールバック手順とイメージ容量の注意

- **[STABLE_VERSION.md](./deployment/STABLE_VERSION.md)** - 戻せるイメージタグの記録
  - 稼働中のタグの調べ方
  - 過去の版と、それが何を含むか

### troubleshooting/
トラブルシューティングガイド

- **[TROUBLESHOOTING.md](./troubleshooting/TROUBLESHOOTING.md)** - 問題解決ガイド
  - 開発環境の問題
  - ビルド時の問題
  - Docker関連の問題
  - API関連の問題
  - コンポーネントの問題
  - テーマ機能の問題（ライトモードで色が上書きされる件を含む）
  - Journey（Instagram 同期）の問題

---

## 🔗 関連ドキュメント

ルートディレクトリにある関連ドキュメント：

- **[README.md](../README.md)** - プロジェクトのメインREADME
- **[README_astro.md](../README_astro.md)** - Astroフレームワークのテンプレートドキュメント
- **[data/ontology/README.md](../data/ontology/README.md)** - 地名オントロジーと県境データの再生成手順・地方シルエットの作り方
