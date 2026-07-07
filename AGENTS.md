# AGENTS.md

## このリポジトリについて

このリポジトリは、GitHub Pagesで公開する静的な地図アプリです。  
基本的に `main` ブランチは公開用の安定版として扱います。

## ブランチ運用

- `main` へ直接コミットしない。
- 機能追加は `feature/...` ブランチで行う。
- 軽微な修正は `fix/...` ブランチで行う。
- 作業完了後、確認してから `main` にマージする。
- マージ済みの作業ブランチは削除してよい。

今回のMapbox Directions対応は、次のブランチで行う。

`feature/mapbox-directions-profile`

## Mapbox token 方針

- Mapbox tokenは、このアプリ専用の public token を使う。
- secret token は使用しない。
- tokenは最終的にブラウザ側のHTML/JavaScriptから見える前提で扱う。
- URL制限は `https://nishikama-ra.github.io/nishikama-transit-map/` を想定する。
- Canva側ドメインは、Mapboxを直接呼ぶページではないため、このtokenの許可URLには含めない。
- GAS中継は今回は使わない。

## 実装方針

- 既存の直線断面図モードを壊さない。
- 「直線 / 徒歩 / 車」を切り替えられるようにする。
- 徒歩・車はMapbox Directions APIでルートを取得する。
- 取得したルート座標列を、既存の標高断面図描画処理に渡す。
- 連打防止、取得中表示、失敗時メッセージを入れる。
- ルート距離や点数が大きすぎる場合は制限する。

## 作業時の注意

- 公開ページに影響するため、`main` で直接試行錯誤しない。
- 変更前に既存の断面図・標高クリック・レイヤ切替が壊れないよう確認する。
- Mapbox tokenの実値を入れる前提の箇所は、1か所に集約する。
