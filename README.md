# English Vocabulary Trainer

英検準2級単語を学習するための4択クイズアプリ

## 使い方

python console_app.py

Quick setup — if you’ve done this kind of thing before
https://github.com/hirojie5310/english-vocab-trainer.git
Get started by creating a new file or uploading an existing file. We recommend every repository include a README, LICENSE, and .gitignore.

…or create a new repository on the command line
echo "# english-vocab-trainer" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/hirojie5310/english-vocab-trainer.git

git push -u origin main
…or push an existing repository from the command line
git remote add origin https://github.com/hirojie5310/english-vocab-trainer.git
git branch -M main
git push -u origin main

## .exe作成

仮想環境を用意（任意）

依存をインストール
requirements.txt は PySide6 のみなので、PyInstallerは別途入れます。.

specを使ってビルド

pip install -r requirements.txt
pip install pyinstaller
pyinstaller console_app.spec --clean

出力先
dist/console_app.exe（one-folder構成の場合は dist/console_app/ 配下になることもあります）

このリポジトリでも dist/ 配下に実行物が置かれる前提の構成になっています。.