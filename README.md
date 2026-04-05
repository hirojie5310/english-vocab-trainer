# English Vocabulary Trainer

英単語を学習するための4択クイズアプリです。現在は iPhone を含むスマートフォンで使いやすい、WebAssembly ベースのブラウザ版を同梱しています。

## 公開URL

GitHub Pages で公開する場合は、以下のURLから実行できます。

[https://hirojie5310.github.io/english-vocab-trainer/](https://hirojie5310.github.io/english-vocab-trainer/)

## Wasm版の起動方法

このアプリは `Pyodide` を使って Python を WebAssembly 上で実行します。静的ファイルとして配信できるので、ローカル確認時は簡易HTTPサーバーで起動してください。

```bash
python -m http.server 8000
```

起動後、ブラウザで以下を開きます。

```text
http://localhost:8000
```

同じネットワーク上の iPhone から確認する場合は、Mac のIPアドレスを使って `http://<your-mac-ip>:8000` を開いてください。

## 画面フロー

起動後は次の流れで進み、最後にまた 1. に戻ります。

1. rootフォルダにあるCSVファイルの選択
2. 出題モードの選択
3. 第1問から第10問まで出題、回答、正誤判定、解説表示
4. 結果表示
5. 正解ログを消去するか確認

## ログの扱い

- 正解ログはブラウザの `localStorage` に CSVごとに保存されます。
- 「正解ログを消去」を選ぶと、そのCSVの正解済み履歴だけを削除します。
- 誤答履歴も次回の出題バランス調整に利用されます。
- GitHub Pages のような静的配信でもCSV候補を表示できるよう、`csv-manifest.json` に学習用CSV一覧を持たせています。

## 既存のコンソール版

従来のコンソール版も残しています。

```bash
python console_app.py
```
