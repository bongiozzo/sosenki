#!/usr/bin/env python3
"""
Translation completeness validation script for SOSenki.

Validates that translations.json contains all required translation keys used in:
1. Bot handlers - t("bot.key") pattern in Python files
2. Mini App - t("key") pattern in JavaScript files

Single source of truth: src/static/mini_app/translations.json

Provides warnings for:
- Missing keys in ru.json
- Unused keys in ru.json (defined but not used in code)

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


def extract_bot_keys_from_python(code: str) -> set:
    """Extract translation keys from Python code using t("bot.key") pattern."""
    # Pattern: t("bot.key_name" with optional format args
    # Handles both single-line t("bot.key") and multi-line t(\n  "bot.key",\n  ...
    pattern = r't\(\s*["\']bot\.([a-z_]+)["\']'
    matches = re.findall(pattern, code)
    return {f"bot.{key}" for key in matches}


def extract_mini_app_keys_from_js(code: str) -> set:
    """Extract translation keys from JavaScript code using t('key') pattern."""
    # Pattern: t("key_name" or t('key_name' with optional params
    # Must match valid translation keys (lowercase letters and underscores only)
    # Exclude HTML element names by requiring underscore in most keys
    pattern = r"t\(['\"]([a-z][a-z_]*[a-z])['\"]"
    matches = re.findall(pattern, code)
    # Filter out HTML element names that might be caught
    html_elements = {
        "a",
        "div",
        "label",
        "option",
        "select",
        "span",
        "p",
        "h1",
        "h2",
        "pre",
        "button",
    }
    return {f"mini_app.{key}" for key in matches if key not in html_elements}


def extract_mini_app_keys_from_html(code: str) -> set:
    """Extract translation keys from HTML using data-i18n attributes."""
    # Pattern: data-i18n="key_name" or data-i18n-html="key_name"
    pattern = r'data-i18n(?:-html)?=["\']([a-z_]+)["\']'
    matches = re.findall(pattern, code)
    return {f"mini_app.{key}" for key in matches}


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

    # Python files that use t() for bot translations
    python_files = [
        project_root / "src" / "bot" / "handlers.py",
        project_root / "src" / "services" / "notification_service.py",
    ]

    # JavaScript files that use t() for mini_app translations
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
    print("=" * 60)

    # Extract keys from Python files (bot namespace)
    bot_keys = set()
    for py_file in python_files:
        if py_file.exists():
            with open(py_file, encoding="utf-8") as f:
                code = f.read()
                bot_keys.update(extract_bot_keys_from_python(code))

    # Extract keys from JavaScript files (mini_app namespace)
    mini_app_keys = set()
    for js_file in js_files:
        if js_file.exists():
            with open(js_file, encoding="utf-8") as f:
                code = f.read()
                mini_app_keys.update(extract_mini_app_keys_from_js(code))

    # Extract keys from HTML files (mini_app namespace via data-i18n attributes)
    for html_file in html_files:
        if html_file.exists():
            with open(html_file, encoding="utf-8") as f:
                code = f.read()
                mini_app_keys.update(extract_mini_app_keys_from_html(code))

    # Combine all used keys
    used_keys = bot_keys | mini_app_keys

    print(f"\n📋 Found {len(bot_keys)} bot keys used in Python handlers")
    print(f"📋 Found {len(mini_app_keys)} mini_app keys used in JavaScript")
    print(f"📚 Found {len(available_keys)} total keys defined in ru.json\n")

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
