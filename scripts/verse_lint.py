#!/usr/bin/env python3
"""
verse_lint.py — Кастомний статичний аналізатор для мови Verse (UEFN)

Використання:
    python scripts/verse_lint.py Verse/
    python scripts/verse_lint.py Verse/ --verbose
    python scripts/verse_lint.py Verse/ --strict
"""

import os
import re
import sys
import argparse
from dataclasses import dataclass
from typing import List

# ── Конфігурація ──────────────────────────────────────────────────────────────

CONFIG = {
    "max_line_length": 100,
    "magic_number_ignore": {0, 1, -1, 5.0, 0.0, 1.0, 2, 3, 4, 10, 100},
    "ignore_patterns": [
        r".*\.digest\.verse$",
        r".*vproject.*",
    ]
}

# ── Типи даних ────────────────────────────────────────────────────────────────

@dataclass
class LintIssue:
    file: str
    line: int
    severity: str   # ERROR | WARNING | INFO
    rule: str
    message: str

    def __str__(self):
        icon = {"ERROR": "✗", "WARNING": "⚠", "INFO": "ℹ"}.get(self.severity, "?")
        return f"  {icon} [{self.severity}] {self.file}:{self.line} — {self.rule}: {self.message}"

# ── Правила аналізу ───────────────────────────────────────────────────────────

def check_line_length(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка довжини рядків (макс. 100 символів)"""
    issues = []
    for i, line in enumerate(lines, 1):
        if len(line.rstrip()) > CONFIG["max_line_length"]:
            issues.append(LintIssue(
                file=filepath, line=i,
                severity="WARNING", rule="line-length",
                message=f"Рядок містить {len(line.rstrip())} символів (макс. {CONFIG['max_line_length']})"
            ))
    return issues


def check_infinite_loop(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка loop без Sleep() — потенційне зависання"""
    issues = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r'^loop\s*:', line) or line == 'loop:':
            # Перевіряємо наступні 10 рядків на наявність Sleep
            block = "\n".join(lines[i:i+15])
            if "Sleep(" not in block and "break" not in block:
                issues.append(LintIssue(
                    file=filepath, line=i+1,
                    severity="ERROR", rule="no-infinite-loop-without-sleep",
                    message="loop без Sleep() або умови виходу може зависнути виконання острова"
                ))
        i += 1
    return issues


def check_magic_numbers(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка числових літералів без іменованих констант"""
    issues = []
    # Ігноруємо рядки з оголошенням констант та коментарями
    pattern = re.compile(r'(?<![A-Za-z_\.])\b(\d+\.?\d*)\b(?!\s*:)')
    editable_mode = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == '@editable':
            editable_mode = True
            continue
        if editable_mode:
            if stripped.startswith('#') or stripped == '':
                continue  # коментар між @editable та полем
            editable_mode = False
            continue  # саме поле @editable
        if stripped.startswith('#') or ':=' in stripped[:20]:
            continue
        matches = pattern.findall(stripped)
        for m in matches:
            val = float(m)
            if val not in CONFIG["magic_number_ignore"] and val > 1:
                issues.append(LintIssue(
                    file=filepath, line=i,
                    severity="WARNING", rule="no-magic-numbers",
                    message=f"Числовий літерал {m} — виведіть у іменовану константу"
                ))
                break  # одне попередження на рядок
    return issues


def check_missing_return_type(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка наявності типу повернення у функціях"""
    issues = []
    # Шукаємо оголошення функцій без типу повернення
    func_pattern = re.compile(r'^\s+(\w+)\s*\([^)]*\)\s*(?:<[^>]*>)?\s*=\s*$')
    for i, line in enumerate(lines, 1):
        if func_pattern.match(line):
            issues.append(LintIssue(
                file=filepath, line=i,
                severity="INFO", rule="explicit-return-type",
                message="Функція без явного типу повернення — рекомендовано вказати : void або тип"
            ))
    return issues


def check_unused_using(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка невикористаних імпортів (using)"""
    issues = []
    using_lines = []
    all_text = "\n".join(lines)

    for i, line in enumerate(lines, 1):
        m = re.match(r'^\s*using\s*\{([^}]+)\}', line)
        if m:
            module = m.group(1).strip()
            # Беремо останню частину шляху
            short_name = module.split("/")[-1]
            using_lines.append((i, line.strip(), short_name))

    for lineno, using_stmt, short_name in using_lines:
        # Перевіряємо чи використовується щось з модуля у коді
        rest_of_file = all_text.replace(using_stmt, "")
        always_used = ["Verse", "Simulation", "Devices", "SpatialMath", "Diagnostics", "Fortnite"]
        if short_name not in rest_of_file and short_name not in always_used:
            issues.append(LintIssue(
                file=filepath, line=lineno,
                severity="WARNING", rule="no-unused-imports",
                message=f"Імпорт '{short_name}' може бути невикористаним"
            ))
    return issues


def check_naming_convention(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка угоди про іменування (класи — snake_case в Verse це норма)"""
    issues = []
    class_pattern = re.compile(r'^\s*(\w+)\s*:=\s*class\s*\(')
    for i, line in enumerate(lines, 1):
        m = class_pattern.match(line)
        if m:
            name = m.group(1)
            # У Verse класи традиційно snake_case, але перевіримо на camelCase
            if re.search(r'[a-z][A-Z]', name):
                issues.append(LintIssue(
                    file=filepath, line=i,
                    severity="INFO", rule="naming-convention",
                    message=f"Клас '{name}' містить camelCase — у Verse рекомендовано snake_case"
                ))
    return issues


def check_comment_density(lines: List[str], filepath: str) -> List[LintIssue]:
    """Перевірка наявності коментарів у файлі"""
    issues = []
    total = len([l for l in lines if l.strip()])
    comments = len([l for l in lines if l.strip().startswith('#')])
    if total > 20 and comments == 0:
        issues.append(LintIssue(
            file=filepath, line=1,
            severity="INFO", rule="require-comments",
            message=f"Файл містить {total} рядків коду без жодного коментаря — додайте пояснення"
        ))
    return issues

# ── Аналізатор ────────────────────────────────────────────────────────────────

def should_ignore(filepath: str) -> bool:
    for pattern in CONFIG["ignore_patterns"]:
        if re.match(pattern, filepath):
            return True
    return False


def analyze_file(filepath: str) -> List[LintIssue]:
    issues = []
    if should_ignore(filepath):
        return issues
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return [LintIssue(filepath, 0, "ERROR", "file-read", str(e))]

    lines_stripped = [l.rstrip('\n') for l in lines]

    issues += check_line_length(lines_stripped, filepath)
    issues += check_infinite_loop(lines_stripped, filepath)
    issues += check_magic_numbers(lines_stripped, filepath)
    issues += check_missing_return_type(lines_stripped, filepath)
    issues += check_unused_using(lines_stripped, filepath)
    issues += check_naming_convention(lines_stripped, filepath)
    issues += check_comment_density(lines_stripped, filepath)

    return issues


def collect_verse_files(path: str) -> List[str]:
    verse_files = []
    if os.path.isfile(path) and path.endswith('.verse'):
        return [path]
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith('.verse'):
                full = os.path.join(root, f)
                if not should_ignore(full):
                    verse_files.append(full)
    return verse_files

# ── Головна функція ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Verse Static Analyzer — кастомний лінтер для UEFN Verse коду'
    )
    parser.add_argument('path', help='Шлях до файлу або директорії з .verse файлами')
    parser.add_argument('--verbose', action='store_true', help='Детальний вивід')
    parser.add_argument('--strict', action='store_true', help='INFO вважається помилкою')
    args = parser.parse_args()

    files = collect_verse_files(args.path)

    if not files:
        print(f"⚠ Verse файли не знайдено у: {args.path}")
        print("  Перевірте шлях або переконайтесь що файли мають розширення .verse")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  Verse Static Analyzer v1.0")
    print(f"  Перевірка: {args.path}")
    print(f"{'='*60}\n")

    all_issues: List[LintIssue] = []

    for filepath in sorted(files):
        issues = analyze_file(filepath)
        if issues or args.verbose:
            rel = os.path.relpath(filepath)
            print(f"📄 {rel}")
            if issues:
                for issue in issues:
                    print(str(issue))
            else:
                print("  ✓ Проблем не знайдено")
            print()
        all_issues += issues

    # Підсумок
    errors   = [i for i in all_issues if i.severity == "ERROR"]
    warnings = [i for i in all_issues if i.severity == "WARNING"]
    infos    = [i for i in all_issues if i.severity == "INFO"]

    print(f"{'='*60}")
    print(f"  ПІДСУМОК")
    print(f"{'='*60}")
    print(f"  Файлів перевірено : {len(files)}")
    print(f"  Помилок (ERROR)   : {len(errors)}")
    print(f"  Попереджень (WARN): {len(warnings)}")
    print(f"  Інформація (INFO) : {len(infos)}")
    print(f"  Всього проблем    : {len(all_issues)}")
    print(f"{'='*60}\n")

    if errors:
        print("✗ Аналіз завершено з ПОМИЛКАМИ\n")
        sys.exit(1)
    elif args.strict and (warnings or infos):
        print("✗ Аналіз завершено з попередженнями (--strict режим)\n")
        sys.exit(1)
    else:
        print("✓ Аналіз завершено успішно\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
