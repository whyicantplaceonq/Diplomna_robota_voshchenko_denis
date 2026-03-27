# 🏗️ Tycoon Simulator — UEFN Project

> Бакалаврська кваліфікаційна робота  
> Розроблено в Unreal Editor for Fortnite (UEFN) з використанням мови Verse

## 📖 Опис проекту

**Tycoon Simulator** — ігровий острів для Fortnite Creative 2.0. Гравець розвиває бізнес: розблоковує будівлі, витрачає внутрішню валюту та розширює свою економічну імперію.

---

## 🚀 Швидкий старт для розробника

> Передбачається свіжа ОС (Windows 10/11). Усі кроки — з нуля.

### Крок 1 — Встановлення Epic Games Launcher

1. Перейдіть на [epicgames.com/store](https://store.epicgames.com)
2. Завантажте та встановіть **Epic Games Launcher**
3. Створіть або увійдіть в Epic Games акаунт
4. У Launcher → вкладка **Fortnite** → встановіть Fortnite

### Крок 2 — Встановлення UEFN

1. У Epic Games Launcher → вкладка **Unreal Editor for Fortnite**
2. Натисніть **Install** (розмір ~20 GB)
3. Дочекайтесь завершення встановлення

### Крок 3 — Встановлення Git

```bash
# Завантажте з https://git-scm.com
# Або через winget:
winget install Git.Git
```

### Крок 4 — Клонування репозиторію

```bash
git clone https://github.com/whyicantplaceonq/Diplomna_robota_voshchenko_denis.git
cd Diplomna_robota_voshchenko_denis
```

### Крок 5 — Відкриття проекту в UEFN

1. Запустіть **Unreal Editor for Fortnite**
2. У вікні запуску натисніть **Open Existing Project**
3. Оберіть папку склонованого репозиторію
4. Дочекайтесь завантаження проекту та компіляції Verse

### Крок 6 — Запуск у режимі розробки

```
UEFN Menu → Launch Session (або Ctrl+F8)
```

Fortnite запуститься з вашим островом у режимі тестування.

### Крок 7 — Перевірка Verse коду

```
UEFN Menu → Verse → Build Verse Code (Ctrl+Shift+B)
```

Якщо компіляція успішна — проект готовий до роботи.

---

## 🗂️ Структура репозиторію

```
/
├── Verse/
│   └── unlockables_device.verse   # Логіка розблокування будівель
├── Content/
│   └── Maps/                      # Мапи острова
├── scripts/
│   ├── verse_lint.py              # Статичний аналізатор коду
│   └── verse_doc.py               # Генератор документації
├── docs/
│   ├── deployment.md              # Інструкція публікації острова
│   ├── update.md                  # Інструкція оновлення
│   ├── generate_docs.md           # Генерація документації
│   ├── linting.md                 # Документація лінтера
│   └── generated/                 # Згенерована HTML-документація
├── .githooks/
│   └── pre-commit                 # Git хук для статичного аналізу
├── .gitignore
├── README.md
└── LICENSE
```

---

## 🛠️ Базові команди

| Дія | Команда / Дія в UEFN |
|---|---|
| Запуск тестування | UEFN → Launch Session (Ctrl+F8) |
| Компіляція Verse | UEFN → Verse → Build Verse Code (Ctrl+Shift+B) |
| Статичний аналіз | `python scripts/verse_lint.py Verse/` |
| Генерація документації | `python scripts/verse_doc.py Verse/ -o docs/generated/` |
| Публікація острова | UEFN → Island → Publish to Fortnite |

---

## 📝 Документування коду

Використовуємо формат **Verse Doc Comments** (`## ... ##`):

```verse
##
# @func MyFunction
# @brief Що робить функція.
# @param AgentArg  Опис параметра
##
MyFunction(AgentArg : agent) : void = ...
```

Детальніше → [docs/generate_docs.md](docs/generate_docs.md)

---

## 🔍 Статичний аналіз (лінтинг)

```bash
# Активація pre-commit хука
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Ручний запуск
python scripts/verse_lint.py Verse/
```

Детальніше → [docs/linting.md](docs/linting.md)

---

## 👤 Автор

**Вощенко Денис** · [GitHub](https://github.com/whyicantplaceonq)

## 📄 Ліцензія

MIT License — детальніше у файлі [LICENSE](LICENSE)
