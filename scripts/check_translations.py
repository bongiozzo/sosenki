#!/usr/bin/env python3
"""
Translation completeness validation script for SOSenki.

Validates that translations.json contains all required translation keys used in:
1. Bot handlers - t("category.key") pattern in Python files
2. Mini App - t("category.key") pattern in JavaScript files
3. HTML - data-i18n="category.key" attributes

Single source of truth: src/static/mini_app/translations.json
Flat namespace: buttons, labels, status, errors, requests, admin, electricity, ui

Provides warnings for:
- Missing keys in translations.json
- Unused keys in translations.json (defined but not used in code)

Usage:
    uv run python scripts/check_translations.py
    make check-i18n
"""

import json
import re
import sys
from pathlib import Path


def load_translations(file_path: Path) -> dict:
    """Load translation JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading {file_path}: {e}")
        sys.exit(1)


def extract_keys_from_code(code: str) -> set:
    """Extract translation keys from Python/JavaScript code using t("category.key") pattern."""
    # Pattern: t("category.key_name" or t('category.key_name' with optional format args
    pattern = r't\(\s*["\']([a-z_]+\.[a-z_]+)["\']'
    matches = re.findall(pattern, code)
    return set(matches)


def extract_keys_from_html(code: str) -> set:
    """Extract translation keys from HTML using data-i18n attributes."""
    # Pattern: data-i18n="category.key_name" or data-i18n-html="category.key_name"
    pattern = r'data-i18n(?:-html)?=["\']([a-z_]+\.[a-z_]+)["\']'
    matches = re.findall(pattern, code)
    return set(matches)


def flatten_keys(translations: dict, prefix: str = "") -> set:
    """Flatten nested translation dict to dot-notation keys."""
    keys = set()
    for key, value in translations.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


def check_translations():  # noqa: C901
    """Main validation function."""
    project_root = Path(__file__).parent.parent

    # Single source of truth
    ru_json_path = project_root / "src" / "static" / "mini_app" / "translations.json"

    # Python files that use t("category.key")
    python_files = [
        project_root / "src" / "bot" / "handlers.py",
        project_root / "src" / "services" / "notification_service.py",
    ]

    # JavaScript files that use t("category.key")
    js_files = [
        project_root / "src" / "static" / "mini_app" / "app.js",
    ]

    # HTML files that use data-i18n attributes
    html_files = [
        project_root / "src" / "static" / "mini_app" / "index.html",
    ]

    # Load translations from single backend file
    translations = load_translations(ru_json_path)
    available_keys = flatten_keys(translations)

    print("\n🔍 Translation Validation Report\n")
    print("=" * 60)
    print(f"📍 Single source of truth: {ru_json_path.relative_to(project_root)}")
    print(
        "📚 Semantic categories: buttons, labels, status, errors, requests, admin, electricity, ui"
    )
    print("=" * 60)

    # Extract keys from all Python files
    python_keys = set()
    for py_file in python_files:
        if py_file.exists():
            with open(py_file, encoding="utf-8") as f:
                code = f.read()
                python_keys.update(extract_keys_from_code(code))

    # Extract keys from JavaScript files
    js_keys = set()
    for js_file in js_files:
        if js_file.exists():
            with open(js_file, encoding="utf-8") as f:
                code = f.read()
                js_keys.update(extract_keys_from_code(code))

    # Extract keys from HTML files
    html_keys = set()
    for html_file in html_files:
        if html_file.exists():
            with open(html_file, encoding="utf-8") as f:
                code = f.read()
                html_keys.update(extract_keys_from_html(code))

    # Combine all used keys
    used_keys = python_keys | js_keys | html_keys

    print(f"\n📋 Found {len(python_keys)} keys used in Python handlers")
    print(f"📋 Found {len(js_keys)} keys used in JavaScript")
    print(f"📋 Found {len(html_keys)} keys used in HTML")
    print(f"📚 Found {len(available_keys)} total keys defined in translations.json\n")

    # Check for missing keys
    missing_keys = used_keys - available_keys
    if missing_keys:
        print(f"⚠️  Missing translations ({len(missing_keys)}):")
        for key in sorted(missing_keys):
            print(f"   - {key}")
        print()

    # Check for unused keys
    unused_keys = available_keys - used_keys
    if unused_keys:
        print(f"ℹ️  Unused translations ({len(unused_keys)}) defined but not used:")
        for key in sorted(unused_keys):
            print(f"   - {key}")
        print()

    # Summary
    print("=" * 60)
    if not missing_keys:
        print("✅ All translation keys are properly defined!\n")
        return 0
    else:
        print(f"❌ {len(missing_keys)} missing translation key(s)\n")
        return 1


if __name__ == "__main__":
    sys.exit(check_translations())
