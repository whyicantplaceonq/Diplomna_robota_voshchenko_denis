# docs/performance.md — Профілювання та оптимізація продуктивності

## 1. Контекст та методологія

### Специфіка платформи UEFN

Мова Verse виконується на серверах Epic Games і не надає стандартних зовнішніх
профайлерів. Тому застосовано два підходи:

| Підхід | Інструмент | Що вимірює |
|---|---|---|
| Вбудований | UEFN Output Log | Runtime помилки, час завантаження |
| Кастомний | Python cProfile + timeit | Алгоритмічна складність логіки |

Кастомний профайлер (`scripts/profiler.py`) запускає Python-еквівалент
`unlockables_device.verse` з ідентичною бізнес-логікою.

### Тестові набори даних

| Набір | Покупок | Props/покупку | Опис сценарію |
|---|---|---|---|
| small | 5 | 4 | Типова конфігурація малого острова |
| medium | 20 | 4 | Стандартний тайкун-острів |
| large | 50 | 4 | Великий острів з багатьма будівлями |

Кожен сценарій: `OnBegin → N покупок → OnPlayerLeft`. Повторень: 300.

---

## 2. Ключові метрики продуктивності

| Метрика | Чому важлива для тайкуну |
|---|---|
| Час виконання `on_claimer_triggered` | Гравець відчуває затримку при натисканні тригера |
| Алокації пам'яті в `_move_props` | При 50 будівлях × 4 props = 200 об'єктів на скидання |
| Час форматування рядків UI | Billboard оновлюється при кожній покупці |
| Час скидання стану `on_player_left` | При виході гравця — скидання всіх куплених об'єктів |

---

## 3. Результати базового профілювання (оригінальна версія)

### Час виконання по наборах даних

| Набір | Час (мс/сценарій) |
|---|---|
| small (5 покупок) | 0.1087 мс |
| medium (20 покупок) | 0.3034 мс |
| large (50 покупок) | 0.7193 мс |

### cProfile — топ функцій (medium dataset, 50 ітерацій)

```
ncalls  tottime  cumtime  filename:lineno(function)
  2950    0.009    0.020   tycoon_sim.py:100(_move_props)
    50    0.001    0.017   tycoon_sim.py:312(make_purchases)
  1000    0.003    0.013   tycoon_sim.py:53(PurchaseData.__init__)
  1000    0.002    0.011   tycoon_sim.py:156(on_claimer_triggered)
  4000    0.004    0.009   tycoon_sim.py:34(CreativeProp.__init__)
 11800    0.003    0.008   tycoon_sim.py:42(get_transform)
```

---

## 4. Виявлені гарячі точки

### Hotspot #1 — `_text_for_ui()` — O(n²) рядкова конкатенація

```python
# ПРОБЛЕМА: побуквенна конкатенація — O(n²) через іммутабельні рядки Python
def _text_for_ui(self, text: str) -> str:
    result = ""
    for char in text:
        result += char   # ← створює новий рядок при кожній ітерації
    return result
```

Еквівалент у Verse: `TextForUI<localizes>` викликається при кожному
`MoveClaimerToPurchase` — тобто при `OnBegin` + кожна покупка + скидання.

### Hotspot #2 — `on_claimer_triggered()` — O(n) лінійний пошук

```python
# ПРОБЛЕМА: шукаємо елемент за індексом лінійно замість прямого доступу
current_purchase = None
for i, pd in enumerate(self.purchase_datas):
    if i == self.current_purchase_index:   # ← O(n) замість O(1)
        current_purchase = pd
        break
```

Verse-еквівалент: `PurchaseDatas[CurrentPurchaseIndex]` — компілятор Verse
оптимізує це, але в Python-симуляції видно алгоритмічну проблему.

### Hotspot #3 — `_move_props()` — зайві алокації об'єктів

```python
# ПРОБЛЕМА: 3 алокації на кожен prop
transform = prop.get_transform()           # ← новий dict
location = transform["translation"]        # ← копія Vector3
new_location = Vector3(location.x,
    location.y, location.z + signed_move)  # ← новий Vector3
```

При 50 будівлях × 4 props = 200 props → 600 зайвих алокацій за скидання.

### Hotspot #4 — `on_player_left()` — range + lookup замість зрізу

```python
# ПРОБЛЕМА: Python range + повторний доступ до масиву
for i in range(0, self.current_purchase_index - 1):
    purchase_data = self.purchase_datas[i]  # ← O(1) але зайвий виклик
```

### Hotspot #5 — `_move_claimer_to_purchase()` — повторне форматування

Рядок білборда формується заново при кожному виклику, хоча він не змінюється
між сесіями гравців.

---

## 5. Застосовані оптимізації

| # | Функція | До | Після | Тип оптимізації |
|---|---|---|---|---|
| 1 | `_text_for_ui` | O(n²) concat | O(1) direct return | Алгоритм |
| 2 | `on_claimer_triggered` | O(n) linear search | O(1) direct index | Структура даних |
| 3 | `_move_props` | 3 aloc/prop | 0 aloc (in-place) | Пам'ять |
| 4 | `on_player_left` | range+lookup | Python slice | Алгоритм |
| 5 | `_move_claimer_to_purchase` | no cache | dict cache | Кешування |
| 6 | `__init__` | len() per call | cached count | Пам'ять |
| 7 | Billboard string | str concat | f-string | Алгоритм |

---

## 6. Результати після оптимізацій

| Набір | Оригінал (мс) | Оптимізовано (мс) | Покращення |
|---|---|---|---|
| small (5) | 0.1087 | 0.0403 | **+62.9%** (2.70x) |
| medium (20) | 0.3034 | 0.1569 | **+48.3%** (1.93x) |
| large (50) | 0.7193 | 0.3388 | **+52.9%** (2.12x) |
| **Середнє** | — | — | **+54.7%** |

Нових гарячих точок після оптимізацій не виявлено.

---

## 7. Відповідність оптимізацій Verse-коду

Кожна оптимізація має прямий еквівалент у реальному Verse-коді:

```verse
# ОПТИМІЗАЦІЯ 2 — прямий доступ за індексом (вже є у Verse)
if (CurrentPurchaseData := PurchaseDatas[CurrentPurchaseIndex]):
    # O(1) — Verse array access

# ОПТИМІЗАЦІЯ 3 — пряма мутація локації (MoveProps)
# Замість copy → modify → teleport можна mutate напряму через:
set Location.Z += SignedMoveOnZ

# ОПТИМІЗАЦІЯ 5 — кешування TextForUI
# У Verse: зберігати відформатований рядок у var поле класу
# і оновлювати лише коли Price або Name змінюється
```

---

## 8. Запуск профайлера

```bash
python scripts/profiler.py
```

Звіт зберігається у `reports/profiler_output.txt`.

---

*Автор: Вощенко Денис · 2025*
