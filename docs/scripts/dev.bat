@echo off
:: dev.bat — Запуск середовища розробки Tycoon Simulator (Windows)
:: Використання: docs\scripts\dev.bat

echo ================================================
echo   Tycoon Simulator — Dev Environment
echo ================================================
echo.

:: Перевірка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не знайдено. Встановіть Python 3.8+
    echo         https://python.org
    pause
    exit /b 1
)

:: Перевірка Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git не знайдено. Встановіть Git
    echo         https://git-scm.com
    pause
    exit /b 1
)

echo [1/4] Активація pre-commit хука...
if exist ".githooks\pre-commit" (
    copy /Y ".githooks\pre-commit" ".git\hooks\pre-commit" >nul
    echo       OK — хук активовано
) else (
    echo       WARN — .githooks\pre-commit не знайдено
)

echo [2/4] Статичний аналіз коду...
python scripts\verse_lint.py Verse\
if errorlevel 1 (
    echo [ERROR] Лінтер знайшов помилки. Виправте перед роботою.
    pause
    exit /b 1
)

echo [3/4] Генерація документації...
python scripts\verse_doc.py Verse\ -o docs\generated\
echo       OK — docs\generated\index.html

echo [4/4] Перевірка статусу Git...
git status

echo.
echo ================================================
echo   Середовище готове до розробки!
echo   Наступний крок: відкрийте проект у UEFN
echo ================================================
echo.
pause
