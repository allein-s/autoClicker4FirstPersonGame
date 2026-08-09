#!/usr/bin/env bash
# macOS 向けに autoClicker.app をビルドする（プロジェクトルートから実行）。
# 注意: PyInstaller はクロスビルド不可のため、必ず macOS 実機で実行すること。
set -euo pipefail
cd "$(dirname "$0")"

# 仮想環境を用意（無ければ作成）。
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# macOS ビルド: Windows 専用の --onefile / --uac-admin は付けない。
# pynput は動的 import のため --collect-submodules で同梱する。
pyinstaller --windowed --name autoClicker --collect-submodules pynput --clean main.py

# 配布用 zip に固める（.app バンドル構造を保持）。
ditto -c -k --sequesterRsrc --keepParent "dist/autoClicker.app" "dist/autoClicker-macos.zip"

echo ""
echo "Output: dist/autoClicker.app  (zip: dist/autoClicker-macos.zip)"
