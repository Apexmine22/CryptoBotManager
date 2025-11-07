# [file name]: main.py
"""
Главный модуль приложения Crypto Bot Manager v2.0
Консольная версия без GUI
"""
import asyncio
import signal
import sys
from pathlib import Path

from core.config_manager import ConfigManager
from core.bot_manager import BotManager
from utils.logger import logger, setup_logging


class Application:
    """Главное приложение"""

    def __init__(self):
        self.config_manager = None
        self.bot_manager = None
        self.running = False

    async def initialize(self):
        """Инициализация приложения"""
        try:
            logger.info("Инициализация приложения...")

            # Настройка логирования
            setup_logging()

            # Инициализация менеджеров
            self.config_manager = ConfigManager()
            self.bot_manager = BotManager(self.config_manager)

            # Создание необходимых директорий
            Path("data/cookies").mkdir(parents=True, exist_ok=True)
            Path("data/screenshots").mkdir(parents=True, exist_ok=True)

            logger.success("Приложение инициализировано")
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации приложения: {e}")
            return False

    async def run(self):
        """Запуск приложения"""
        if not await self.initialize():
            return

        self.running = True

        # Настройка обработчиков сигналов
        self._setup_signal_handlers()

        try:
            logger.info("Запуск ботов...")
            await self.bot_manager.start_all()

            # Основной цикл приложения
            await self._main_loop()

        except Exception as e:
            logger.error(f"Критическая ошибка в приложении: {e}")
        finally:
            await self.shutdown()

    async def _main_loop(self):
        """Главный цикл приложения"""
        logger.info("Приложение запущено. Нажмите Ctrl+C для остановки.")

        try:
            while self.running:
                # Проверяем статус ботов каждые 10 секунд
                await asyncio.sleep(10)

                # Выводим статус работающих ботов
                running_bots = self.bot_manager.get_running_bot_count()
                if running_bots > 0:
                    logger.info(f"Работает ботов: {running_bots}")

        except asyncio.CancelledError:
            logger.info("Получен запрос на остановку")

    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""

        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, завершение работы...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def shutdown(self):
        """Корректное завершение работы"""
        logger.info("Завершение работы приложения...")

        if self.bot_manager:
            await self.bot_manager.shutdown()

        logger.success("Приложение завершило работу")


async def main():
    """Главная функция"""
    app = Application()
    await app.run()


def print_banner():
    """Вывод баннера приложения"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   CRYPTO BOT MANAGER v2.0                   ║
║                 Консольная версия без GUI                   ║
║                                                              ║
║         Автоматизация работы с faucet-сайтами               ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


if __name__ == "__main__":
    print_banner()

    try:
        # Запуск асинхронного приложения
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        sys.exit(1)
