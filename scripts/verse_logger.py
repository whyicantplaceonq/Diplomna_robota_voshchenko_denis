"""
verse_logger.py — Система логування для Tycoon Simulator (UEFN/Verse)

Рівень логування визначається БЕЗ перекомпіляції через:
  1. Змінну оточення:  LOG_LEVEL=DEBUG python scripts/verse_logger.py
  2. Ключ при запуску: python scripts/verse_logger.py --log-level DEBUG
  3. Файл конфігурації: config/logging.cfg

Використання:
    from verse_logger import get_logger, log_error, log_purchase
    logger = get_logger("unlockables_device")
    logger.info("OnBegin started")
"""

import logging
import logging.handlers
import os
import sys
import uuid
import json
import argparse
import configparser
from datetime import datetime
from pathlib import Path

# ── Константи ─────────────────────────────────────────────────────────────────

LOG_DIR    = Path(__file__).parent.parent / "logs"
LOG_FILE   = LOG_DIR / "tycoon.log"
ERROR_FILE = LOG_DIR / "tycoon_errors.log"
CONFIG_FILE = Path(__file__).parent.parent / "config" / "logging.cfg"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Рівні для різних модулів
MODULE_LEVELS = {
    "unlockables_device": logging.DEBUG,
    "economy":            logging.INFO,
    "player_session":     logging.INFO,
    "ui":                 logging.WARNING,
}


# ── Визначення рівня без перекомпіляції ───────────────────────────────────────

def resolve_log_level() -> int:
    """
    Визначає рівень логування у порядку пріоритету:
    1. Аргумент командного рядка --log-level
    2. Змінна оточення LOG_LEVEL
    3. Файл конфігурації config/logging.cfg
    4. Значення за замовчуванням: INFO
    """
    # 1. Аргумент командного рядка
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--log-level", default=None)
    args, _ = parser.parse_known_args()
    if args.log_level:
        level = getattr(logging, args.log_level.upper(), None)
        if level:
            return level

    # 2. Змінна оточення
    env_level = os.environ.get("LOG_LEVEL", "").upper()
    if env_level:
        level = getattr(logging, env_level, None)
        if level:
            return level

    # 3. Файл конфігурації
    if CONFIG_FILE.exists():
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_FILE)
        cfg_level = cfg.get("logging", "level", fallback="").upper()
        if cfg_level:
            level = getattr(logging, cfg_level, None)
            if level:
                return level

    # 4. За замовчуванням
    return logging.INFO


# ── Форматер з контекстом ─────────────────────────────────────────────────────

class ContextFormatter(logging.Formatter):
    """Форматер що додає контекстну інформацію до кожного запису."""

    def format(self, record: logging.LogRecord) -> str:
        # Додаємо error_id якщо є
        if not hasattr(record, "error_id"):
            record.error_id = ""
        if not hasattr(record, "player_id"):
            record.player_id = ""
        if not hasattr(record, "session_id"):
            record.session_id = ""
        return super().format(record)


# ── Ініціалізація системи логування ──────────────────────────────────────────

def setup_logging(level: int = None) -> None:
    """Налаштовує глобальну систему логування з усіма обробниками."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if level is None:
        level = resolve_log_level()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Коренений — DEBUG, фільтрується обробниками

    # Очищаємо існуючі обробники
    root_logger.handlers.clear()

    formatter = ContextFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # Обробник 1: Консоль (рівень з конфігурації)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Обробник 2: Файл з ротацією за розміром (5 МБ, 3 резервні копії)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # Файл пише все
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Обробник 3: Окремий файл тільки для помилок
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_FILE,
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    logging.getLogger("root").info(
        f"Logging initialized | level={logging.getLevelName(level)} | "
        f"file={LOG_FILE}"
    )


def get_logger(module_name: str) -> logging.Logger:
    """Повертає логер для конкретного модуля."""
    logger = logging.getLogger(module_name)
    # Встановлюємо специфічний рівень для модуля якщо задано
    if module_name in MODULE_LEVELS:
        logger.setLevel(MODULE_LEVELS[module_name])
    return logger


# ── Унікальні ідентифікатори помилок ─────────────────────────────────────────

def make_error_id() -> str:
    """Генерує унікальний ID помилки для відстеження."""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex[:6].upper()
    return f"ERR-{ts}-{uid}"


def make_session_id() -> str:
    """Генерує ID сесії гравця."""
    return f"SESSION-{uuid.uuid4().hex[:8].upper()}"


# ── Спеціалізовані функції логування ─────────────────────────────────────────

class TycoonLogger:
    """
    Обгортка над стандартним логером з контекстом гравця та сесії.
    Забезпечує структуровані логи з унікальними ID помилок.
    """

    def __init__(self, module_name: str, session_id: str = None):
        self._logger = get_logger(module_name)
        self.session_id = session_id or make_session_id()
        self.player_id = None

    def set_player(self, player_id: str) -> None:
        self.player_id = player_id

    def _extra(self, error_id: str = "") -> dict:
        return {
            "error_id": error_id,
            "player_id": self.player_id or "",
            "session_id": self.session_id,
        }

    def debug(self, msg: str) -> None:
        self._logger.debug(f"[{self.session_id}] {msg}")

    def info(self, msg: str) -> None:
        self._logger.info(f"[{self.session_id}] {msg}")

    def warning(self, msg: str) -> None:
        self._logger.warning(f"[{self.session_id}] {msg}")

    def error(self, msg: str, exc_info: bool = False) -> str:
        error_id = make_error_id()
        self._logger.error(
            f"[{self.session_id}] [{error_id}] {msg}",
            exc_info=exc_info,
        )
        return error_id

    def critical(self, msg: str, exc_info: bool = False) -> str:
        error_id = make_error_id()
        self._logger.critical(
            f"[{self.session_id}] [{error_id}] {msg}",
            exc_info=exc_info,
        )
        return error_id


# ── Функції логування ігрових подій ───────────────────────────────────────────

def log_purchase_attempt(logger: TycoonLogger, player_id: str,
                          purchase_name: str, price: int, gold: int) -> None:
    """Логування спроби покупки будівлі."""
    logger.debug(
        f"PURCHASE_ATTEMPT | player={player_id} | item={purchase_name} "
        f"| price={price} | gold={gold} | can_afford={gold >= price}"
    )


def log_purchase_success(logger: TycoonLogger, player_id: str,
                          purchase_name: str, price: int,
                          remaining_gold: int, index: int) -> None:
    """Логування успішної покупки."""
    logger.info(
        f"PURCHASE_SUCCESS | player={player_id} | item={purchase_name} "
        f"| price={price} | remaining_gold={remaining_gold} | index={index}"
    )


def log_purchase_failed(logger: TycoonLogger, player_id: str,
                         purchase_name: str, price: int, gold: int) -> str:
    """Логування невдалої покупки (недостатньо золота)."""
    return logger.error(
        f"PURCHASE_FAILED | player={player_id} | item={purchase_name} "
        f"| required={price} | available={gold} | deficit={price - gold}"
    )


def log_player_joined(logger: TycoonLogger, player_id: str) -> None:
    logger.info(f"PLAYER_JOINED | player={player_id}")


def log_player_left(logger: TycoonLogger, player_id: str,
                     purchases_made: int) -> None:
    logger.info(
        f"PLAYER_LEFT | player={player_id} | purchases_made={purchases_made} "
        f"| state=reset"
    )


def log_wrong_owner(logger: TycoonLogger, requesting_player: str,
                     owner_player: str) -> str:
    """Логування спроби покупки чужим гравцем."""
    return logger.error(
        f"WRONG_OWNER | requester={requesting_player} | owner={owner_player} "
        f"| action=blocked"
    )


def log_device_init(logger: TycoonLogger, purchases_count: int,
                     move_distance: float) -> None:
    logger.info(
        f"DEVICE_INIT | purchases_count={purchases_count} "
        f"| move_distance={move_distance} | status=OK"
    )


def log_all_purchased(logger: TycoonLogger, player_id: str,
                       total: int) -> None:
    logger.info(
        f"ALL_PURCHASED | player={player_id} | total_buildings={total} "
        f"| island=complete"
    )


# ── Демонстрація роботи ───────────────────────────────────────────────────────

def demo() -> None:
    """Демонстрація всіх рівнів логування та сценаріїв."""
    setup_logging()
    logger = TycoonLogger("unlockables_device")

    print(f"\n{'='*60}")
    print("  Tycoon Simulator — Logger Demo")
    print(f"  Рівень: {logging.getLevelName(resolve_log_level())}")
    print(f"  Файл логів: {LOG_FILE}")
    print(f"{'='*60}\n")

    # OnBegin
    log_device_init(logger, purchases_count=5, move_distance=1500.0)

    # Гравець приєднується
    logger.set_player("player_ABC123")
    log_player_joined(logger, "player_ABC123")

    # Успішна покупка
    log_purchase_attempt(logger, "player_ABC123", "Workshop", 100, 500)
    log_purchase_success(logger, "player_ABC123", "Workshop", 100, 400, 0)

    # Невдала покупка
    log_purchase_attempt(logger, "player_ABC123", "Factory", 600, 400)
    err_id = log_purchase_failed(logger, "player_ABC123", "Factory", 600, 400)
    print(f"\n  Помилка зафіксована з ID: {err_id}")
    print(f"  Повідомлення гравцю: 'Недостатньо золота! Потрібно 600, є 400.'")

    # Чужий гравець
    err_id2 = log_wrong_owner(logger, "player_XYZ999", "player_ABC123")
    print(f"  Помилка власника з ID: {err_id2}")

    # WARNING рівень
    logger.warning("TRIGGER_BLOCKED | reason=cooldown | duration=1.0s")

    # Гравець виходить
    log_player_left(logger, "player_ABC123", purchases_made=1)

    # Критична помилка (симуляція)
    try:
        raise RuntimeError("purchase_datas array is empty — island misconfigured")
    except RuntimeError:
        crit_id = logger.critical("ISLAND_CONFIG_ERROR | purchases=0", exc_info=True)
        print(f"  Критична помилка з ID: {crit_id}")

    print(f"\n  Логи збережено у: {LOG_FILE}")
    print(f"  Помилки збережено у: {ERROR_FILE}\n")


if __name__ == "__main__":
    demo()
