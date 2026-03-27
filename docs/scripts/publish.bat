@echo off
:: publish.bat — Підготовка до публікації острова (Windows)
:: Використання: docs\scripts\publish.bat [version]
:: Приклад:      docs\scripts\publish.bat 1.1.0

setlocal
set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

echo ================================================
echo   Tycoon Simulator — Pre-Publish Checklist
echo   Version: v%VERSION%
echo ================================================
echo.

set ERRORS=0

echo [1/5] Перевірка чистоти Git...
git diff --quiet
if errorlevel 1 (
    echo       [FAIL] Є незакомічені зміни!
    git status --short
    set /a ERRORS+=1
) else (
    echo       [OK]
)

echo [2/5] Статичний аналіз Verse...
python scripts\verse_lint.py Verse\
if errorlevel 1 (
    echo       [FAIL] Лінтер знайшов помилки!
    set /a ERRORS+=1
) else (
    echo       [OK]
)

echo [3/5] Оновлення документації...
python scripts\verse_doc.py Verse\ -o docs\generated\ >nul
git add docs\generated\
echo       [OK] docs\generated\ оновлено

echo [4/5] Створення Git тегу v%VERSION%...
git tag -a "v%VERSION%" -m "Release v%VERSION%"
if errorlevel 1 (
    echo       [WARN] Тег вже існує або помилка
) else (
    echo       [OK] Тег v%VERSION% створено
)

echo [5/5] Push на GitHub...
git push origin main
git push origin "v%VERSION%"
echo       [OK]

echo.
if %ERRORS% GTR 0 (
    echo ================================================
    echo   [FAIL] Знайдено %ERRORS% проблем. Виправте перед публікацією!
    echo ================================================
) else (
    echo ================================================
    echo   [OK] Всі перевірки пройдено!
    echo.
    echo   Наступні кроки в UEFN:
    echo   1. Verse ^> Build Verse Code ^(Ctrl+Shift+B^)
    echo   2. Island ^> Publish to Fortnite
    echo ================================================
)
echo.
pause
endlocal
