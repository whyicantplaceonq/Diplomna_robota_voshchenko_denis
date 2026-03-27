# Генерація документації — Tycoon Simulator (UEFN)

## Огляд

Документація генерується кастомним скриптом `verse_doc.py` що читає
doc-коментарі (`## ... ##`) з `.verse` файлів і створює HTML-сайт.

---

## Інструменти

| Інструмент | Призначення |
|---|---|
| `scripts/verse_doc.py` | Генератор HTML-документації з Verse коду |
| `docs/generated/` | Вихідна директорія з HTML |
| UEFN Build Verse Code | Вбудована перевірка типів (аналог typedoc) |

> **Чому не Doxygen/JSDoc?** Для мови Verse не існує офіційних парсерів.
> `verse_doc.py` реалізує власний формат doc-коментарів, натхненний JSDoc.

---

## Формат doc-коментарів

```verse
##
# @class MyClass
# @brief Короткий опис (одне речення).
#
# Детальний опис. Може займати
# кілька рядків.
#
# @field FieldName  Опис поля
##
MyClass := class(creative_device):

    ##
    # @func MyFunction
    # @brief Що робить функція.
    #
    # @param AgentArg  Опис параметра
    # @returns         Що повертає
    # @suspends        Якщо async
    # @algorithm       Опис алгоритму
    # @business-logic  Бізнес-правила
    # @error-handling  Обробка помилок
    ##
    MyFunction(AgentArg : agent) : void = ...
```

### Підтримувані теги

| Тег | Призначення |
|---|---|
| `@class` | Назва класу |
| `@func` | Назва функції |
| `@brief` | Короткий опис (перший рядок автоматично) |
| `@param Name Опис` | Параметр функції |
| `@returns Опис` | Тип/значення що повертається |
| `@suspends` | Позначення async функції |
| `@algorithm` | Опис алгоритму |
| `@business-logic` | Бізнес-правила та обмеження |
| `@architecture` | Архітектурні рішення |
| `@flow` | Потік виконання |
| `@error-handling` | Обробка помилок |
| `@see` | Посилання на пов'язані елементи |

---

## Запуск генерації

### Базовий запуск

```bash
python scripts/verse_doc.py Verse/ -o docs/generated/
```

### З кастомним заголовком

```bash
python scripts/verse_doc.py Verse/ -o docs/generated/ --title "Tycoon Simulator v2.0"
```

### Результат

```
=======================================================
  verse_doc.py — Verse Documentation Generator
=======================================================
  ✓ unlockables_device.verse → 9 documented entries

  Файлів оброблено  : 1
  Задокументовано   : 9 елементів
  Вихідна директорія: docs/generated/
  Відкрийте        : docs/generated/index.html
=======================================================
```

Відкрийте `docs/generated/index.html` у браузері.

---

## Вимоги

- Python 3.8+ (лише стандартна бібліотека, pip не потрібен)

---

## Правила для розробників

1. **Кожен новий клас** → обов'язково `## @class ... ##` перед декларацією
2. **Кожна публічна функція** → обов'язково `## @func ... ## `
3. **`@brief`** — одне речення, відповідь на питання "що це робить?"
4. **`@param`** — для кожного параметра функції
5. **`@business-logic`** — для функцій з нетривіальними правилами
6. **Оновлюйте документацію** при кожній зміні сигнатури або логіки
7. **Автогенеровані файли** (`*.digest.verse`) — не документувати

---

## Інтеграція з Git

Додайте до pre-commit хука автоматичну регенерацію:

```bash
# .githooks/pre-commit (додати після аналізатора)
echo "Regenerating documentation..."
python scripts/verse_doc.py Verse/ -o docs/generated/
git add docs/generated/
```
