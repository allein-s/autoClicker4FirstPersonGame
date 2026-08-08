# Auto Clicker

カーソル位置を左クリックする Windows 向け自動クリックツールです。クリックと待機（インターバル）を並べたスケジュールをループ実行し、グローバルホットキー（既定は F8）で開始/停止できます。ゲーム（Minecraft など）でも動作するよう、低レベル入力（`SendInput`）を使用しています。

## 主な機能

- **カーソル位置をクリック**（座標指定ではなく現在のマウス位置を左クリック）
- **スケジュールのループ実行**（例: クリック → 200ms → クリック → 3000ms を繰り返し）
- **グローバルホットキー**で開始/停止（既定 F8、設定で変更可能。バックグラウンド・ゲーム中でも有効）
- **選択位置の直下に挿入**（一覧で項目を選んでクリック/インターバルを追加）
- **右クリックメニュー**（一覧上でクリック追加/インターバル追加/削除）
- **スケジュールの保存・読み込み**（JSON。プルダウンから前方一致で選択して読み込み）
- **実行中インジケーター**を画面右下（タスクバー上部）に表示（表示可否は設定で切替）
- **設定画面**: ホットキー変更・保存先フォルダ・クリック押下時間・最小化/最前面・自動読み込み・スタートアップ登録
- **多言語対応**（日本語 / English、既定は日本語。起動時に設定を読み込み）
- ゲーム対応: `SendInput` + 前面ウィンドウへのスレッドアタッチ、管理者権限で起動

## 動作環境

- Windows 10 / 11
- Python 3.12 以降（ソースから実行/ビルドする場合）
- サードパーティのランタイム依存はありません（すべて標準ライブラリ）。`pyinstaller` は exe ビルド専用です。

## 使い方（exe）

1. `dist\autoClicker.exe` を起動します（管理者権限の確認が表示されます）。
2. 左パネルで「クリック」「インターバル」を追加してスケジュールを作成します。
3. クリックしたい位置にマウスカーソルを置きます。
4. **F8** で開始/停止します（開始時に最小化、停止時に再表示）。

> ゲーム内で動作させる場合、ゲームを管理者として実行しているときは本アプリも管理者権限で起動してください（権限が異なると入力がブロックされます）。

## ソースから実行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python main.py
```

## exe のビルド

```powershell
# 依存の導入と PyInstaller によるビルドをまとめて実行
powershell -ExecutionPolicy Bypass -File .\build.ps1
# 生成物: dist\autoClicker.exe
```

または直接:

```powershell
pip install -r requirements.txt
pyinstaller --onefile --windowed --uac-admin --name autoClicker --clean main.py
```

## 開発 / テスト

```powershell
pip install -r requirements-dev.txt
pytest
```

CI（GitHub Actions, `.github/workflows/ci.yml`）は次のように動作します。

- **push / PR（`main`・`development`）**: 全モジュールのバイトコンパイルと `pytest`
- **`main` への PR**: 流入元が `development` かをチェック（それ以外はブロック）
- **`main` への push（＝マージ）時のみ**: PyInstaller で exe をビルドし、`pyproject.toml` の `version` を用いて `vX.Y.Z` の GitHub Release を自動作成・配布（同一バージョンが既に存在する場合はスキップ）

### ブランチ運用

- `development`: 通常の開発ブランチ（レビュー承認でマージ）
- `main`: リリース用。`development` からのみ、かつ管理者のみマージ可能
- リリースは **`main` にマージされたときのみ** 行われます。新バージョンを出す際は `pyproject.toml` の `version` を上げてください。

## 設定ファイル

- 設定は exe と同じディレクトリの `settings.json` に保存されます。
- スケジュールの保存先は既定で exe からの相対パス `schedule/` です（設定画面で変更可能）。
- これらはユーザー/環境依存のため `.gitignore` で除外しています。

## プロジェクト構成

```
main.py                          # エントリポイント
build.ps1                        # ビルドスクリプト
requirements.txt                 # ビルド依存 (pyinstaller)
requirements-dev.txt             # 開発/CI 依存 (pytest)
pyproject.toml                   # プロジェクト設定 + pytest 設定
autoclicker/
  app.py                         # メインアプリ / コントローラ
  settings.py                    # 設定データ + JSON 永続化
  settings_window.py             # 設定ダイアログ
  hotkey.py                      # グローバルホットキー (RegisterHotKey)
  overlay.py                     # 実行中インジケーター
  input_backend.py               # SendInput によるクリック
  startup_registry.py            # Windows スタートアップ登録
  vk_map.py                      # キー <-> 仮想キーコード
  paths.py                       # exe 相対パス解決
  scheduling/                    # スケジュールのモデル / 保存・読込
  widgets/                       # 前方一致オートコンプリート等
  i18n/                          # 文言辞書 (ja / en) と切替
tests/                           # pytest テスト
```

## 注意

- ゲームやツールの利用規約・各種法令に従ってご利用ください。
- OS の制限により、一部の保護されたアプリではクリックやホットキーが効かない場合があります。
