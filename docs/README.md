# ドキュメント / Documentation

このディレクトリには、プロジェクトのドキュメントが整理されています。

## 📁 ディレクトリ構成

### superpowers/specs/
機能の設計書

- **[2026-09-11-journey-instagram-design.md](./superpowers/specs/2026-09-11-journey-instagram-design.md)** - Journey × Instagram 連携
  - 都道府県の解決パイプライン（raw + 辞書 + override の純関数）
  - 外部依存を任意レイヤに置く方針
  - 調査で覆った事実の記録

### deployment/
デプロイメントとバージョン管理に関するドキュメント

- **[DEPLOYMENT.md](./deployment/DEPLOYMENT.md)** - デプロイ手順とワークフロー
  - main への push で本番が入れ替わる仕組み（GitHub Actions）
  - 必要な GitHub Secrets
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
  - テーマ機能の問題

---

## 🔗 関連ドキュメント

ルートディレクトリにある関連ドキュメント：

- **[README.md](../README.md)** - プロジェクトのメインREADME
- **[README_astro.md](../README_astro.md)** - Astroフレームワークのテンプレートドキュメント
- **[data/ontology/README.md](../data/ontology/README.md)** - 地名オントロジーと県境データの再生成手順
