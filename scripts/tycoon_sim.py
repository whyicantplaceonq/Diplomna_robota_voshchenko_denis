"""
tycoon_sim.py — Python-еквівалент логіки unlockables_device (Verse/UEFN)

Моделює ту саму бізнес-логіку що виконується на острові:
- Масив покупок (purchase_data)
- Перевірка власника сесії
- Перевірка балансу золота
- Переміщення об'єктів (симульоване)
- Скидання стану при виході гравця

Використовується для профілювання та вимірювання продуктивності.
"""

import time
import random
import string


# ── Моделі даних (еквівалент Verse класів) ────────────────────────────────────

class Vector3:
    """Еквівалент vector3 у Verse."""
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Vector3(self.x, self.y, self.z)


class CreativeProp:
    """Еквівалент creative_prop — 3D об'єкт на острові."""
    def __init__(self, prop_id: str):
        self.prop_id = prop_id
        self.location = Vector3(
            random.uniform(-5000, 5000),
            random.uniform(-5000, 5000),
            random.uniform(0, 1000)
        )

    def get_transform(self):
        return {"translation": self.location.copy(), "rotation": (0.0, 0.0, 0.0)}

    def teleport_to(self, location: Vector3, rotation: tuple) -> bool:
        """Симулює TeleportTo[] — завжди успішно."""
        self.location = location
        return True


class PurchaseData:
    """Еквівалент purchase_data у Verse."""
    def __init__(self, name: str, price: int, props_count: int = 3):
        self.name = name
        self.price = price
        self.claimer_location = Vector3(
            random.uniform(-2000, 2000),
            random.uniform(-2000, 2000),
            100.0
        )
        self.creative_props = [
            CreativeProp(f"prop_{name}_{i}") for i in range(props_count)
        ]


class Player:
    """Еквівалент agent у Verse."""
    def __init__(self, player_id: str, gold: int = 0):
        self.player_id = player_id
        self.gold = gold

    def __eq__(self, other):
        return isinstance(other, Player) and self.player_id == other.player_id


# ── ВЕРСІЯ БЕЗ ОПТИМІЗАЦІЙ (оригінальна логіка) ──────────────────────────────

class UnlockablesDeviceOriginal:
    """
    Точний Python-еквівалент оригінального Verse-коду unlockables_device.
    Навмисно зберігає всі неоптимальні патерни для профілювання.
    """

    def __init__(self, purchase_datas: list, move_distance: float = 1500.0):
        self.purchase_datas = purchase_datas
        self.default_move_distance = move_distance
        self.maybe_owner_agent = None
        self.current_purchase_index = 0
        self.block_trigger_interaction = False
        self.billboard_text = ""

    def _text_for_ui(self, text: str) -> str:
        """Еквівалент TextForUI<localizes> — форматування рядка."""
        # НЕОПТИМАЛЬНО: конкатенація рядків у циклі (string interpolation кожен раз)
        result = ""
        for char in text:
            result += char
        return result

    def _move_props(self, purchase_data: PurchaseData, move_up: bool) -> None:
        """Еквівалент MoveProps — переміщення всіх props покупки."""
        signed_move = self.default_move_distance if move_up else -self.default_move_distance

        # НЕОПТИМАЛЬНО: повторний пошук в масиві, зайві копії об'єктів
        for prop in purchase_data.creative_props:
            transform = prop.get_transform()
            location = transform["translation"]
            # Зайве копіювання через словник
            new_location = Vector3(location.x, location.y, location.z + signed_move)
            prop.teleport_to(new_location, transform["rotation"])

    def _move_claimer_to_purchase(self, purchase_data: PurchaseData) -> None:
        """Еквівалент MoveClaimerToPurchase — оновлення тригера та білборда."""
        # Симулюємо TeleportTo тригера
        trigger_location = purchase_data.claimer_location

        # НЕОПТИМАЛЬНО: рядкова конкатенація замість форматування
        if purchase_data.price == 0:
            price_string = "FREE"
        else:
            price_string = str(purchase_data.price)

        # НЕОПТИМАЛЬНО: _text_for_ui обходить рядок побуквенно кожен раз
        billboard_string = purchase_data.name + "\n" + price_string
        self.billboard_text = self._text_for_ui(billboard_string)

    def on_begin(self) -> None:
        """Еквівалент OnBegin — ініціалізація."""
        # Переміщуємо всі об'єкти вниз
        for purchase_data in self.purchase_datas:
            self._move_props(purchase_data, False)

        # Переходимо до першої покупки
        if self.purchase_datas:
            self._move_claimer_to_purchase(self.purchase_datas[0])

    def on_player_left(self, agent: Player) -> None:
        """Еквівалент OnPlayerLeft — скидання стану."""
        if self.maybe_owner_agent is None:
            return
        if self.maybe_owner_agent != agent:
            return

        self.maybe_owner_agent = None

        # НЕОПТИМАЛЬНО: range(0, index-1) + звернення до масиву за індексом
        # замість прямого зрізу
        for i in range(0, self.current_purchase_index - 1):
            purchase_data = self.purchase_datas[i]
            self._move_props(purchase_data, False)

        self.current_purchase_index = 0
        if self.purchase_datas:
            self._move_claimer_to_purchase(self.purchase_datas[0])

    def on_claimer_triggered(self, maybe_agent) -> str:
        """Еквівалент OnClaimerTriggered — обробка натискання тригера."""
        if maybe_agent is None:
            return "no_agent"
        if self.block_trigger_interaction:
            return "blocked"

        agent = maybe_agent

        if self.maybe_owner_agent is not None:
            # НЕОПТИМАЛЬНО: порівняння об'єктів без кешування
            if self.maybe_owner_agent != agent:
                return "wrong_owner"
        else:
            self.maybe_owner_agent = agent

        # НЕОПТИМАЛЬНО: лінійний пошук в масиві по індексу кожен раз
        if self.current_purchase_index >= len(self.purchase_datas):
            return "all_purchased"

        current_purchase = None
        for i, pd in enumerate(self.purchase_datas):
            if i == self.current_purchase_index:
                current_purchase = pd
                break

        if current_purchase is None:
            return "no_purchase"

        owner_gold = agent.gold
        if owner_gold < current_purchase.price:
            return "not_enough_gold"

        # Виконуємо покупку
        self.block_trigger_interaction = True
        self._move_props(current_purchase, True)
        agent.gold -= current_purchase.price
        self.current_purchase_index += 1

        if self.current_purchase_index >= len(self.purchase_datas):
            return "all_done"

        self._move_claimer_to_purchase(
            self.purchase_datas[self.current_purchase_index]
        )
        self.block_trigger_interaction = False
        return "purchased"


# ── ВЕРСІЯ З ОПТИМІЗАЦІЯМИ ────────────────────────────────────────────────────

class UnlockablesDeviceOptimized:
    """
    Оптимізована версія з виправленими гарячими точками.
    """

    def __init__(self, purchase_datas: list, move_distance: float = 1500.0):
        self.purchase_datas = purchase_datas
        self.default_move_distance = move_distance
        self.maybe_owner_agent = None
        self.current_purchase_index = 0
        self.block_trigger_interaction = False
        self.billboard_text = ""
        # ОПТИМІЗАЦІЯ 1: кешуємо довжину масиву
        self._purchases_count = len(purchase_datas)
        # ОПТИМІЗАЦІЯ 2: кешуємо відформатовані рядки білборда
        self._billboard_cache: dict = {}

    def _text_for_ui(self, text: str) -> str:
        """ОПТИМІЗАЦІЯ 3: пряме повернення без побуквенного обходу."""
        return text

    def _move_props(self, purchase_data: PurchaseData, move_up: bool) -> None:
        """ОПТИМІЗАЦІЯ 4: мінімізація створення об'єктів, пряма мутація."""
        signed_move = self.default_move_distance if move_up else -self.default_move_distance

        for prop in purchase_data.creative_props:
            # Пряма мутація Z без створення копії Transform та нового Vector3
            prop.location.z += signed_move

    def _move_claimer_to_purchase(self, purchase_data: PurchaseData) -> None:
        """ОПТИМІЗАЦІЯ 5: кешування рядків білборда."""
        name = purchase_data.name

        # Перевіряємо кеш
        if name in self._billboard_cache:
            self.billboard_text = self._billboard_cache[name]
            return

        price_string = "FREE" if purchase_data.price == 0 else str(purchase_data.price)
        billboard_string = f"{name}\n{price_string}"
        self._billboard_cache[name] = billboard_string
        self.billboard_text = billboard_string

    def on_begin(self) -> None:
        for purchase_data in self.purchase_datas:
            self._move_props(purchase_data, False)
        if self.purchase_datas:
            self._move_claimer_to_purchase(self.purchase_datas[0])

    def on_player_left(self, agent: Player) -> None:
        if self.maybe_owner_agent is None:
            return
        if self.maybe_owner_agent != agent:
            return

        self.maybe_owner_agent = None

        # ОПТИМІЗАЦІЯ 6: зріз масиву замість range + пошуку
        for purchase_data in self.purchase_datas[:self.current_purchase_index]:
            self._move_props(purchase_data, False)

        self.current_purchase_index = 0
        if self.purchase_datas:
            self._move_claimer_to_purchase(self.purchase_datas[0])

    def on_claimer_triggered(self, maybe_agent) -> str:
        if maybe_agent is None:
            return "no_agent"
        if self.block_trigger_interaction:
            return "blocked"

        agent = maybe_agent

        if self.maybe_owner_agent is not None:
            if self.maybe_owner_agent != agent:
                return "wrong_owner"
        else:
            self.maybe_owner_agent = agent

        # ОПТИМІЗАЦІЯ 7: прямий доступ за індексом замість лінійного пошуку
        if self.current_purchase_index >= self._purchases_count:
            return "all_purchased"

        current_purchase = self.purchase_datas[self.current_purchase_index]

        if agent.gold < current_purchase.price:
            return "not_enough_gold"

        self.block_trigger_interaction = True
        self._move_props(current_purchase, True)
        agent.gold -= current_purchase.price
        self.current_purchase_index += 1

        if self.current_purchase_index >= self._purchases_count:
            return "all_done"

        self._move_claimer_to_purchase(
            self.purchase_datas[self.current_purchase_index]
        )
        self.block_trigger_interaction = False
        return "purchased"


# ── Фабрика тестових даних ────────────────────────────────────────────────────

def make_purchases(count: int, props_per_purchase: int = 3) -> list:
    """Генерує тестовий масив покупок."""
    purchases = []
    for i in range(count):
        name = f"Building_{i:04d}"
        price = random.randint(0, 500)
        purchases.append(PurchaseData(name, price, props_per_purchase))
    return purchases


def make_player(gold: int = 999999) -> Player:
    pid = "player_" + "".join(random.choices(string.ascii_lowercase, k=6))
    return Player(pid, gold)
