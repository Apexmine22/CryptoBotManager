"""
Унифицированная система логирования v2.0
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import threading


class SingletonMeta(type):
    """Метакласс для создания singleton классов"""
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветами для консоли"""

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'SUCCESS': '\033[92m',  # Bright Green
        'RESET': '\033[0m'  # Reset
    }

    def format(self, record):
        log_message = super().format(record)
        if sys.stdout.isatty() and hasattr(record, 'color'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            return f"{color}{log_message}{self.COLORS['RESET']}"
        return log_message


class BotLogger(metaclass=SingletonMeta):
    """Унифицированный логгер для ботов"""

    def __init__(self):
        self._initialized = False
        self._log_dir = Path("logs")
        self._setup_logging()

    def _setup_logging(self):
        """Настройка системы логирования"""
        if self._initialized:
            return

        # Создание директории для логов
        self._log_dir.mkdir(exist_ok=True)

        # Настройка корневого логгера
        self.logger = logging.getLogger("CryptoBotManager")
        self.logger.setLevel(logging.INFO)

        # Очистка существующих обработчиков
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Форматтеры
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # Файловый обработчик
        file_handler = logging.FileHandler(
            self._log_dir / "application.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)

        # Консольный обработчик
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)

        # Добавление обработчиков
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self._initialized = True

    def info(self, message: str):
        """Информационное сообщение"""
        self.logger.info(message)

    def error(self, message: str):
        """Сообщение об ошибке"""
        self.logger.error(message)

    def warning(self, message: str):
        """Предупреждение"""
        self.logger.warning(message)

    def debug(self, message: str):
        """Отладочное сообщение"""
        self.logger.debug(message)

    def success(self, message: str):
        """Сообщение об успехе"""
        extra = {'color': 'SUCCESS'}
        self.logger.info(f"✅ {message}", extra=extra)

    def critical(self, message: str):
        """Критическое сообщение"""
        self.logger.critical(message)


# Глобальный экземпляр логгера
logger = BotLogger()


def setup_logging():
    """
    Инициализировать систему логирования.
    Фактически создаётся (или возвращается) единственный объект BotLogger.
    """
    # Экземпляр создаётся единожды благодаря SingletonMeta
    BotLogger()


def get_logger(name: str) -> logging.Logger:
    """Получение именованного логгера"""
    return logging.getLogger(name)
