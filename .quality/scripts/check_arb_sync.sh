#!/usr/bin/env bash
#
# check_arb_sync.sh - ARB 多言語キーの同期確認
#
# Exit Codes:
#   0 - すべてのキーが同期済み
#   1 - 欠落キーを検出
#

cd "$(dirname "$0")/../.."

python3 << 'PYEOF'
import json
import sys
from pathlib import Path

l10n_dir = Path("lib/l10n")
template_file = l10n_dir / "app_ja.arb"

if not template_file.exists():
    print("⚠️ Template file not found")
    sys.exit(0)

# テンプレートキーを抽出（@ プレフィックスを除外）
with open(template_file, encoding='utf-8') as f:
    template_data = json.load(f)

template_keys = {k for k in template_data.keys() if not k.startswith('@')}

missing_total = 0

for arb_file in sorted(l10n_dir.glob("app_*.arb")):
    if arb_file == template_file:
        continue

    lang = arb_file.stem.replace("app_", "")

    with open(arb_file, encoding='utf-8') as f:
        lang_data = json.load(f)

    lang_keys = {k for k in lang_data.keys() if not k.startswith('@')}
    missing = template_keys - lang_keys

    if missing:
        print(f"⚠️ {lang}: {len(missing)} keys missing")
        missing_total += len(missing)

if missing_total > 0:
    print()
    print(f"Total: {missing_total} keys missing across all languages")
    print("Run: /arb-sync to fix")
    sys.exit(1)

print("✅ All ARB keys are synchronized")
sys.exit(0)
PYEOF
